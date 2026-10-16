"""Bounded, version-checked arXiv acquisition; never called by offline search."""

import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .corpus import validate_document
from .models import Document

ATOM = "{http://www.w3.org/2005/Atom}"
MAX_RESPONSE_BYTES = 1_048_576


class _NoDoctype(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("arXiv Atom must not contain DOCTYPE or entity declarations")


def _source_ids(sources: list[dict]) -> list[str]:
    if not isinstance(sources, list) or not 1 <= len(sources) <= 5:
        raise ValueError("expected 1–5 versioned arXiv sources")
    ids = []
    for source in sources:
        version = source.get("arxiv_id") if isinstance(source, dict) else None
        if not isinstance(version, str) or not re.fullmatch(r"\d{4}\.\d{4,5}v[1-9]\d*", version):
            raise ValueError("source must have a versioned arxiv_id")
        ids.append(version)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate source ID")
    return ids


def parse_atom(raw: bytes, sources: list[dict], fetched_at: str) -> list[Document]:
    ids = _source_ids(sources)
    try:
        root = ET.fromstring(raw, parser=ET.XMLParser(target=_NoDoctype()))
    except ET.ParseError as exc:
        raise ValueError("invalid arXiv Atom XML") from exc
    if root.tag != ATOM + "feed":
        raise ValueError("expected an arXiv Atom feed")
    entries = {}
    for entry in root.findall(ATOM + "entry"):
        identifier = entry.findtext(ATOM + "id") or ""
        parsed = urlsplit(identifier)
        version = parsed.path.removeprefix("/abs/")
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc != "arxiv.org"
            or parsed.path != f"/abs/{version}"
            or parsed.query
            or parsed.fragment
            or version not in ids
            or version in entries
        ):
            raise ValueError("unexpected, duplicate, or wrong-version arXiv response ID")
        entries[version] = entry
    if set(entries) != set(ids):
        raise ValueError("arXiv response is missing requested version IDs")
    documents = []
    for source, version in zip(sources, ids):
        entry = entries[version]
        # Preserve author text exactly as exposed by Atom. Empty/missing -> explicit null.
        title = entry.findtext(ATOM + "title")
        abstract = entry.findtext(ATOM + "summary")
        documents.append(
            validate_document(
                {
                    "doc_id": f"arxiv:{version}",
                    "title": title if title and title.strip() else None,
                    "abstract": abstract if abstract and abstract.strip() else None,
                    "source_url": f"https://arxiv.org/abs/{version}",
                    "source_type": "preprint",
                    "language": "en",
                    "license_url": source.get("license_url"),
                    "fetched_at": fetched_at,
                }
            )
        )
    return documents


def _publish_new_snapshot(files: dict[Path, bytes]) -> None:
    """Publish only new files; roll back new links on ordinary I/O failures.

    Stage all content first, then link it exclusively on the same filesystem.
    The corpus is linked last. This is not a power-loss-safe multi-file transaction.
    """
    staged = {}
    published = []
    try:
        for path, data in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                staged[path] = Path(stream.name)
                stream.write(data)
        for path, temp in staged.items():
            os.link(temp, path)
            published.append(path)
    except OSError:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)


def fetch_corpus(sources: list[dict], output: Path) -> list[Document]:
    ids = _source_ids(sources)
    raw_path = output.with_name(output.name + ".atom.xml")
    receipt_path = output.with_name(output.name + ".receipt.json")
    if any(path.exists() or path.is_symlink() for path in (output, raw_path, receipt_path)):
        raise ValueError("fetch output already exists; use a new --output path to retain snapshots")
    url = "https://export.arxiv.org/api/query?" + urlencode(
        {
            "id_list": ",".join(ids),
            "max_results": len(ids),
        }
    )
    request = Request(url, headers={"User-Agent": "PaperEvidenceLab/0.1 (small research demo)"})
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, TimeoutError) as exc:
        raise ValueError(f"arXiv fetch failed: {exc}") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("arXiv response exceeds 1 MiB")
    fetched_at = datetime.now(timezone.utc).isoformat()
    documents = parse_atom(raw, sources, fetched_at)
    encoded = "".join(json.dumps(asdict(doc), ensure_ascii=False) + "\n" for doc in documents)
    receipt = {
        "request_url": url,
        "fetched_at": fetched_at,
        "ids": ids,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "metadata_terms_url": "https://info.arxiv.org/help/api/tou.html",
        "text_transform": "Atom XML character decoding only; whitespace preserved; empty to null",
    }
    # Validate and stage everything before publishing. Commit the corpus last.
    _publish_new_snapshot(
        {
            raw_path: raw,
            receipt_path: json.dumps(receipt, indent=2).encode(),
            output: encoded.encode(),
        }
    )
    return documents

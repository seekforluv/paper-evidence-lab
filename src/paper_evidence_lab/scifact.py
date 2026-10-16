"""Pinned BEIR SciFact snapshots. Raw data stays local; no arbitrary ZIP extraction."""

import hashlib
import io
import json
import shutil
import stat
import urllib.request
import zipfile
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from .benchmark_data import DATA_FILES, BenchmarkData, load_beir_files

MAX_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_MEMBER_BYTES = 16 * 1024 * 1024
ARCHIVE_MEMBERS = {
    "scifact/",
    "scifact/qrels/",
    "scifact/corpus.jsonl",
    "scifact/queries.jsonl",
    "scifact/qrels/train.tsv",
    "scifact/qrels/test.tsv",
}


def source_manifest() -> dict:
    return json.loads(files("paper_evidence_lab").joinpath("scifact_source.json").read_text())


def _verify_archive(blob: bytes, manifest: dict) -> None:
    if (
        len(blob) != manifest["archive_bytes"]
        or len(blob) > MAX_ARCHIVE_BYTES
        or hashlib.sha256(blob).hexdigest() != manifest["archive_sha256"]
        or hashlib.md5(blob).hexdigest() != manifest["archive_md5"]
    ):
        raise ValueError("archive size/hash differs from the pinned source")


def _verify_files(raw: dict[str, bytes], manifest: dict) -> None:
    for name in DATA_FILES:
        if hashlib.sha256(raw[name]).hexdigest() != manifest["files_sha256"][name]:
            raise ValueError(f"{name}: SHA-256 differs from the pinned source")


def _check_counts(data: BenchmarkData, manifest: dict) -> None:
    actual = {
        "corpus": len(data.documents),
        "all_queries": data.all_query_count,
        "test_queries": len(data.queries),
        "qrel_pairs": sum(len(labels) for labels in data.qrels.values()),
    }
    if actual != manifest["counts"]:
        raise ValueError(f"dataset counts differ from pinned source: {actual}")


def acquire_scifact(output: Path, archive_bytes: bytes | None = None) -> dict:
    """Create a new snapshot; receipt is the completion marker, written last.

    Ordinary write failures remove this call's new directory. A process/power failure
    may leave an incomplete directory; verified loading rejects it. Never overwrite.
    """
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"snapshot already exists: {output}")
    manifest = source_manifest()
    if archive_bytes is None:
        request = urllib.request.Request(
            manifest["source_url"], headers={"User-Agent": "paper-evidence-lab/0.2"}
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            archive_bytes = response.read(MAX_ARCHIVE_BYTES + 1)
    _verify_archive(archive_bytes, manifest)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        infos = archive.infolist()
        if len(infos) != len(ARCHIVE_MEMBERS) or {i.filename for i in infos} != ARCHIVE_MEMBERS:
            raise ValueError("archive members differ from expected names")
        if any(
            i.file_size > MAX_MEMBER_BYTES or stat.S_ISLNK(i.external_attr >> 16) for i in infos
        ):
            raise ValueError("archive member exceeds size limit or is a symlink")
        raw = {name: archive.read("scifact/" + name) for name in DATA_FILES}
    _verify_files(raw, manifest)
    data = load_beir_files(output, raw)
    _check_counts(data, manifest)
    receipt = {
        "schema_version": 1,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        **manifest,
    }
    # mkdir(exist_ok=False) claims ownership; cleanup never runs on an existing target.
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "qrels").mkdir()
        (output / "source.zip").write_bytes(archive_bytes)
        for name, content in raw.items():
            (output / name).write_bytes(content)
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(output)
        raise
    return receipt


def load_verified_scifact(root: Path) -> BenchmarkData:
    manifest = source_manifest()
    receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in manifest.items()):
        raise ValueError("receipt differs from the pinned source manifest")
    _verify_archive((root / "source.zip").read_bytes(), manifest)
    raw = {name: (root / name).read_bytes() for name in DATA_FILES}
    _verify_files(raw, manifest)
    data = load_beir_files(root, raw)
    _check_counts(data, manifest)
    return data

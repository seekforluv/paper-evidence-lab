"""Strict BEIR parsing, independent of the evidence-display schema."""

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path

from .corpus import _invalid_constant, _unique_keys

DATA_FILES = ("corpus.jsonl", "queries.jsonl", "qrels/test.tsv")


@dataclass(frozen=True)
class BenchmarkData:
    documents: dict[str, str]
    queries: dict[str, str]
    qrels: dict[str, dict[str, int]]
    all_query_count: int


def _records(raw: bytes, name: str, corpus: bool) -> dict[str, str]:
    records = {}
    for line, content in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(
                content.decode("utf-8"),
                object_pairs_hook=_unique_keys,
                parse_constant=_invalid_constant,
            )
            if not isinstance(row, dict):
                raise ValueError("expected object")
            doc_id = row.get("_id")
            if not isinstance(doc_id, str) or not doc_id.strip() or doc_id in records:
                raise ValueError("invalid or duplicate _id")
            text = row.get("text")
            title = row.get("title", "") if corpus else ""
            if (
                not isinstance(text, str)
                or not isinstance(title, str)
                or not (text + title).strip()
            ):
                raise ValueError("expected nonempty title/text")
            for value in (text, title, doc_id):
                value.encode("utf-8")
            records[doc_id] = title + "\n" + text if corpus else text
        except ValueError as exc:
            raise ValueError(f"{name} line {line}: {exc}") from exc
    if not records:
        raise ValueError(f"{name}: empty data")
    return records


def load_beir_files(root: Path, raw: dict[str, bytes] | None = None) -> BenchmarkData:
    # Verified callers supply the same bytes that were hashed, without a second read.
    if raw is None:
        raw = {name: (root / name).read_bytes() for name in DATA_FILES}
    documents = _records(raw["corpus.jsonl"], "corpus.jsonl", True)
    queries = _records(raw["queries.jsonl"], "queries.jsonl", False)
    qrels = {}
    reader = csv.reader(io.StringIO(raw["qrels/test.tsv"].decode("utf-8")), delimiter="\t")
    if next(reader, None) != ["query-id", "corpus-id", "score"]:
        raise ValueError("test.tsv line 1: invalid header")
    for line, row in enumerate(reader, 2):
        if len(row) != 3:
            raise ValueError(f"test.tsv line {line}: expected three columns")
        query_id, doc_id, score = row
        if query_id not in queries or doc_id not in documents:
            raise ValueError(f"test.tsv line {line}: unknown query/document reference")
        if not score.isascii() or not score.isdecimal():
            raise ValueError(f"test.tsv line {line}: invalid relevance label")
        if doc_id in qrels.get(query_id, {}):
            raise ValueError(f"test.tsv line {line}: duplicate qrel pair")
        qrels.setdefault(query_id, {})[doc_id] = int(score)
    if not qrels or any(not any(rel > 0 for rel in labels.values()) for labels in qrels.values()):
        raise ValueError("test.tsv: each query needs a positive relevance judgment")
    return BenchmarkData(
        documents, {query_id: queries[query_id] for query_id in sorted(qrels)}, qrels, len(queries)
    )

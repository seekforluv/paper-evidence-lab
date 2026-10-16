"""Frozen BM25 benchmark output contains identifiers and scores, never source text."""

import hashlib
import platform
from dataclasses import asdict
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from .evaluation import evaluate_rankings
from .lexical import CONFIG, BM25LexicalIndex
from .scifact import load_verified_scifact, source_manifest


def evaluate_bm25(root: Path) -> dict:
    data = load_verified_scifact(root)
    index = BM25LexicalIndex(list(data.documents.items()))
    results = {
        query_id: [asdict(row) for row in index.rank(query, k=10, exclude_id=query_id)]
        for query_id, query in sorted(data.queries.items())
    }
    rankings = {qid: [row["doc_id"] for row in rows] for qid, rows in results.items()}
    package = files("paper_evidence_lab")
    source = source_manifest()
    return {
        "schema_version": 1,
        "method": "BM25",
        "source": {
            key: source[key]
            for key in ("dataset", "split", "archive_sha256", "files_sha256", "counts")
        },
        "config": {**CONFIG, "k": 10, "text": "title + newline + text", "exclude_same_id": True},
        "implementation": {
            "versions": {
                **{name: version(name) for name in ("paper-evidence-lab", "bm25s", "numpy")},
                "python": platform.python_version(),
            },
            "code_sha256": {
                name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
                for name in (
                    "benchmark.py",
                    "benchmark_data.py",
                    "evaluation.py",
                    "lexical.py",
                    "scifact.py",
                )
            },
        },
        "metrics": evaluate_rankings(data.qrels, rankings, k=10),
        "results": results,
    }

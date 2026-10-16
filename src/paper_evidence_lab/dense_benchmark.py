"""The preselected MiniLM baseline on the same verified SciFact input."""

import hashlib
import platform
import sys
from dataclasses import asdict
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from . import model_assets, scifact
from .evaluation import evaluate_rankings
from .semantic import CONFIG, DenseIndex, MiniLMEncoder


def _progress(done: int, total: int) -> None:
    if done % 256 == 0 or done == total:
        print(f"Encoded {done}/{total} texts locally", file=sys.stderr, flush=True)


def evaluate_semantic(dataset: Path, model: Path) -> dict:
    data = scifact.load_verified_scifact(dataset)
    encoder = MiniLMEncoder(model)
    ids = sorted(data.documents)
    document_vectors = encoder.encode([data.documents[doc_id] for doc_id in ids], _progress)
    document_stats = dict(encoder.last_stats)
    query_ids = sorted(data.queries)
    query_vectors = encoder.encode([data.queries[qid] for qid in query_ids], _progress)
    query_stats = dict(encoder.last_stats)
    index = DenseIndex(ids, document_vectors)
    results = {
        qid: [asdict(row) for row in index.rank(vector, k=10, exclude_id=qid)]
        for qid, vector in zip(query_ids, query_vectors)
    }
    rankings = {qid: [row["doc_id"] for row in rows] for qid, rows in results.items()}
    source = scifact.source_manifest()
    package = files("paper_evidence_lab")
    return {
        "schema_version": 1,
        "method": "MiniLM (ONNX)",
        "source": {
            key: source[key]
            for key in ("dataset", "split", "archive_sha256", "files_sha256", "counts")
        },
        "model": model_assets.model_manifest(),
        "config": CONFIG,
        "implementation": {
            "versions": {
                **{
                    name: version(name)
                    for name in ("paper-evidence-lab", "onnxruntime", "tokenizers", "numpy")
                },
                "python": platform.python_version(),
            },
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "code_sha256": {
                name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
                for name in (
                    "dense_benchmark.py",
                    "semantic.py",
                    "model_assets.py",
                    "benchmark_data.py",
                    "scifact.py",
                    "evaluation.py",
                )
            },
        },
        "encoding": {"documents": document_stats, "queries": query_stats},
        "metrics": evaluate_rankings(data.qrels, rankings, k=10),
        "results": results,
    }

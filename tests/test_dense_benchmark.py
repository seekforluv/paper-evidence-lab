import importlib
import json
from pathlib import Path

import numpy as np

from paper_evidence_lab.benchmark_data import BenchmarkData


def test_end_to_end_dense_evaluation_preserves_query_mapping(monkeypatch):
    module = importlib.import_module("paper_evidence_lab.dense_benchmark")
    data = BenchmarkData(
        {"b": "Beta\nOriginal synthetic second", "a": "Alpha\nOriginal synthetic first"},
        {"qb": "second invented query", "qa": "first invented query"},
        {"qa": {"a": 1}, "qb": {"b": 1}},
        2,
    )
    source = {
        "dataset": "synthetic",
        "split": "test",
        "archive_sha256": "synthetic",
        "files_sha256": {},
        "counts": {"corpus": 2, "all_queries": 2, "test_queries": 2, "qrel_pairs": 2},
    }
    monkeypatch.setattr(module.scifact, "load_verified_scifact", lambda _: data)
    monkeypatch.setattr(module.scifact, "source_manifest", lambda: source)

    class Encoder:
        last_stats = {}

        def encode(self, texts, progress):
            expected = (
                [data.documents["a"], data.documents["b"]]
                if "Alpha" in texts[0]
                else [data.queries["qa"], data.queries["qb"]]
            )
            assert texts == expected
            self.last_stats = {
                "text_count": len(texts),
                "truncated_texts": 0,
                "max_untruncated_tokens": 3,
            }
            return np.eye(2, dtype=np.float32)

    monkeypatch.setattr(module, "MiniLMEncoder", lambda _: Encoder())
    result = module.evaluate_semantic(Path("unused"), Path("unused"))
    assert result["metrics"]["aggregate"] == {"ndcg": 1.0, "recall": 1.0}
    assert result["results"]["qa"][0]["doc_id"] == "a"
    assert result["results"]["qb"][0]["doc_id"] == "b"
    assert result["encoding"]["documents"]["text_count"] == 2
    assert "Original synthetic" not in json.dumps(result)

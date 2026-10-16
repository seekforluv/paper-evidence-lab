"""Independent trec_eval cross-check. Requires the locked development dependencies."""

import argparse
import json
import math
from importlib.metadata import version
from pathlib import Path

import pytrec_eval

from paper_evidence_lab.evaluation import evaluate_rankings
from paper_evidence_lab.scifact import load_verified_scifact, source_manifest


def check(dataset: Path, result_path: Path) -> dict:
    data = load_verified_scifact(dataset)
    output = json.loads(result_path.read_text(encoding="utf-8"))
    if set(output["results"]) != set(data.qrels):
        raise ValueError("result query coverage differs from qrels")
    manifest = source_manifest()
    expected_source = {
        key: manifest[key]
        for key in ("dataset", "split", "archive_sha256", "files_sha256", "counts")
    }
    if output.get("source") != expected_source:
        raise ValueError("result source provenance differs from the pinned source")
    rankings = {}
    for qid, rows in output["results"].items():
        if len(rows) > 10 or any(
            row["doc_id"] not in data.documents
            or row["doc_id"] == qid
            or not math.isfinite(row["score"])
            or row["score"] <= 0
            for row in rows
        ):
            raise ValueError(f"invalid ranked result for {qid}")
        if rows != sorted(rows, key=lambda row: (-row["score"], row["doc_id"])):
            raise ValueError(f"result ordering differs from the declared policy for {qid}")
        rankings[qid] = [row["doc_id"] for row in rows]
    actual = evaluate_rankings(data.qrels, rankings, k=10)
    if actual != output["metrics"]:
        raise ValueError("stored metrics do not match stored rankings")
    # trec_eval's raw-score tie breaker differs. Strict ordinal scores preserve the
    # already frozen order; this checks metric formulas, not BM25 score semantics.
    run = {
        qid: {doc_id: float(len(ids) - rank) for rank, doc_id in enumerate(ids)}
        for qid, ids in rankings.items()
    }
    scores = pytrec_eval.RelevanceEvaluator(data.qrels, {"ndcg_cut.10", "recall.10"}).evaluate(run)
    deltas = []
    for qid in data.qrels:
        for own, ref in (("ndcg", "ndcg_cut_10"), ("recall", "recall_10")):
            deltas.append(abs(actual["per_query"][qid][own] - scores.get(qid, {}).get(ref, 0.0)))
    if max(deltas) > 1e-12:
        raise ValueError(f"reference evaluator disagrees: max error {max(deltas)}")
    return {
        "reference": "pytrec-eval-terrier",
        "reference_version": version("pytrec-eval-terrier"),
        "query_count": len(data.qrels),
        "per_query_values_compared": len(deltas),
        "max_absolute_error": max(deltas),
        "tolerance": 1e-12,
        "score_encoding": "strict descending ordinal scores preserve the explicit rank order",
        "aggregate": actual["aggregate"],
        "passed": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.dataset, args.result), indent=2, allow_nan=False))

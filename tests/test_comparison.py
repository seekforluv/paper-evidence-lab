import copy
import math
import runpy
from pathlib import Path

import pytest


def functions():
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts/build_comparison.py"))


def run(values, method):
    per_query = {str(i): {"ndcg": n, "recall": r} for i, (n, r) in enumerate(values)}
    return {
        "method": method,
        "source": {
            "dataset": "synthetic",
            "split": "test",
            "counts": {"test_queries": len(values)},
        },
        "model": {"model_id": "synthetic-model", "revision": "fixed"},
        "encoding": {},
        "config": {"k": 10},
        "metrics": {
            "k": 10,
            "query_count": len(values),
            "per_query": per_query,
            "aggregate": {
                m: math.fsum(r[m] for r in per_query.values()) / len(values)
                for m in ("ndcg", "recall")
            },
        },
        "results": {qid: [{"doc_id": "synthetic", "score": 0.5}] for qid in per_query},
    }


def test_paired_comparison_and_outcome_counts():
    baseline = run([(1, 1), (0, 0), (0.5, 1)], "BM25")
    candidate = run([(0.5, 1), (1, 1), (0.5, 1)], "MiniLM (ONNX)")
    data = functions()["compare_runs"](baseline, candidate)
    assert data["query_count"] == 3
    assert data["outcomes"]["ndcg"] == {"improved": 1, "tied": 1, "declined": 1}
    assert data["outcomes"]["recall"] == {"improved": 1, "tied": 2, "declined": 0}
    assert data["aggregate"]["ndcg"]["delta"] == pytest.approx(1 / 6)
    assert [row["query_id"] for row in data["rows"]] == ["0", "1", "2"]


@pytest.mark.parametrize("mutation", ["coverage", "source", "mean", "nan"])
def test_inconsistent_result_inputs_rejected(mutation):
    baseline = run([(1, 1), (0, 0)], "BM25")
    candidate = copy.deepcopy(baseline)
    candidate["method"] = "MiniLM (ONNX)"
    if mutation == "coverage":
        candidate["metrics"]["per_query"].pop("1")
    elif mutation == "source":
        candidate["source"]["split"] = "different"
    elif mutation == "mean":
        candidate["metrics"]["aggregate"]["ndcg"] = 0.1
    else:
        candidate["results"]["0"][0]["score"] = float("nan")
    with pytest.raises(ValueError):
        functions()["compare_runs"](baseline, candidate)


def test_html_embedded_data_cannot_close_script_tag():
    funcs = functions()
    rendered = funcs["render_html"]({"example": "</script><script>alert(1)</script>"})
    assert "</script><script>alert(1)</script>" not in rendered
    assert "\\u003c/script>" in rendered
    assert "__COMPARISON_DATA__" not in rendered


@pytest.mark.parametrize(
    "section,value", [("metrics", 5), ("config", 5), ("metrics", None), ("config", None)]
)
def test_non_top_ten_or_missing_cutoff_rejected(section, value):
    baseline = run([(1, 1)], "BM25")
    candidate = run([(1, 1)], "MiniLM (ONNX)")
    if value is None:
        candidate[section].pop("k")
    else:
        candidate[section]["k"] = value
    with pytest.raises(ValueError, match="cutoff"):
        functions()["compare_runs"](baseline, candidate)

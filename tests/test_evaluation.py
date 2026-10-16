import importlib
import math

import pytest


def evaluate(qrels, rankings, k=10):
    return importlib.import_module("paper_evidence_lab.evaluation").evaluate_rankings(
        qrels, rankings, k
    )


def test_graded_ndcg_linear_gain_and_unjudged_rank():
    result = evaluate({"q": {"a": 3, "b": 1}}, {"q": ["u", "b", "a"]}, 3)
    wanted = (1 / math.log2(3) + 3 / math.log2(4)) / (3 + 1 / math.log2(3))
    assert result["per_query"]["q"]["ndcg"] == pytest.approx(wanted)
    assert result["aggregate"]["recall"] == 1


def test_recall_denominator_all_relevant_and_macro_includes_missing():
    result = evaluate({"q1": {"a": 1, "b": 1}, "q2": {"c": 1}}, {"q1": ["a"]}, 1)
    assert result["per_query"]["q1"]["recall"] == 0.5
    assert result["per_query"]["q2"]["recall"] == 0
    assert result["aggregate"] == {"ndcg": 0.5, "recall": 0.25}
    assert result["query_count"] == 2


def test_empty_run_is_zero_not_missing():
    result = evaluate({"q": {"a": 1}}, {"q": []})
    assert result["aggregate"] == {"ndcg": 0.0, "recall": 0.0}


@pytest.mark.parametrize(
    "qrels, rankings",
    [
        ({}, {}),
        ({"q": {}}, {}),
        ({"q": {"a": 0}}, {}),
        ({"q": {"a": -1}}, {}),
        ({"q": {"a": True}}, {}),
        ({"q": {"a": 1}}, {"q": ["a", "a"]}),
        ({"q": {"a": 1}}, {"unknown": []}),
    ],
)
def test_bad_metric_inputs_fail(qrels, rankings):
    with pytest.raises(ValueError):
        evaluate(qrels, rankings)


@pytest.mark.parametrize("k", [0, True, 1.5])
def test_invalid_cutoff(k):
    with pytest.raises(ValueError):
        evaluate({"q": {"a": 1}}, {}, k)

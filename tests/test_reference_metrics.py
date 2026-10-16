import random

import pytest
import pytrec_eval

from paper_evidence_lab.evaluation import evaluate_rankings


def test_seeded_graded_metrics_against_trec_eval():
    rng = random.Random(7051)
    for _ in range(40):
        qrels = {"q": {f"d{i}": rng.randrange(4) for i in range(8)}, "missing": {"z": 1}}
        qrels["q"]["d0"] = 3
        ids = list(qrels["q"]) + ["unjudged"]
        rng.shuffle(ids)
        ids = ids[: rng.randrange(10)]
        for k in (1, 3, 10):
            actual = evaluate_rankings(qrels, {"q": ids}, k)
            run = {"q": {doc: float(len(ids) - i) for i, doc in enumerate(ids)}}
            ref = pytrec_eval.RelevanceEvaluator(qrels, {f"ndcg_cut.{k}", f"recall.{k}"}).evaluate(
                run
            )
            for qid in qrels:
                for own, metric in (("ndcg", f"ndcg_cut_{k}"), ("recall", f"recall_{k}")):
                    assert actual["per_query"][qid][own] == pytest.approx(
                        ref.get(qid, {}).get(metric, 0.0), abs=1e-12
                    )

"""Linear-gain nDCG and recall with qrels-defined macro denominators."""

import math


def evaluate_rankings(qrels: dict, rankings: dict, k: int = 10) -> dict:
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    if not qrels or set(rankings) - set(qrels):
        raise ValueError("nonempty qrels required; unknown ranking queries forbidden")
    per_query = {}
    for query_id in sorted(qrels):
        judgments = qrels[query_id]
        if not judgments or any(type(rel) is not int or rel < 0 for rel in judgments.values()):
            raise ValueError(f"invalid labels for query {query_id}")
        relevant = {doc_id for doc_id, rel in judgments.items() if rel > 0}
        if not relevant:
            raise ValueError(f"query {query_id} has no positive judgments")
        ranked = rankings.get(query_id, [])
        if not isinstance(ranked, list) or any(not isinstance(doc_id, str) for doc_id in ranked):
            raise ValueError("rankings must contain lists of document IDs")
        if len(set(ranked)) != len(ranked):
            raise ValueError(f"duplicate ranked document for query {query_id}")
        top = ranked[:k]
        dcg = math.fsum(judgments.get(doc_id, 0) / math.log2(i + 2) for i, doc_id in enumerate(top))
        ideal = sorted(judgments.values(), reverse=True)[:k]
        idcg = math.fsum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
        per_query[query_id] = {
            "ndcg": dcg / idcg,
            "recall": len(relevant.intersection(top)) / len(relevant),
        }
    return {
        "k": k,
        "query_count": len(qrels),
        "aggregate": {
            metric: math.fsum(row[metric] for row in per_query.values()) / len(qrels)
            for metric in ("ndcg", "recall")
        },
        "per_query": per_query,
    }

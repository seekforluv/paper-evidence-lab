"""Build a deterministic, text-free offline viewer from the two verified runs."""

import argparse
import hashlib
import json
import math
from pathlib import Path

METRICS = ("ndcg", "recall")
TOLERANCE = 1e-12


def _validate_run(run: dict) -> None:
    metrics = run["metrics"]
    if any(
        type(section.get("k")) is not int or section["k"] != 10
        for section in (metrics, run.get("config", {}))
    ):
        raise ValueError("comparison requires a declared cutoff of 10 in metrics and config")
    per_query = metrics["per_query"]
    if (
        not per_query
        or set(per_query) != set(run["results"])
        or metrics["query_count"] != len(per_query)
        or run["source"]["counts"]["test_queries"] != len(per_query)
    ):
        raise ValueError("query coverage/count mismatch")
    for metric in METRICS:
        values = [row[metric] for row in per_query.values()]
        if any(type(value) not in (int, float) or not 0 <= value <= 1 for value in values):
            raise ValueError("invalid per-query metric")
        mean = math.fsum(values) / len(values)
        recorded = metrics["aggregate"][metric]
        if not math.isfinite(recorded) or abs(mean - recorded) > TOLERANCE:
            raise ValueError("recorded macro average does not match per-query values")
    for rows in run["results"].values():
        if len(rows) > 10 or len({r["doc_id"] for r in rows}) != len(rows):
            raise ValueError("invalid top-10 result IDs")
        if any(
            not isinstance(row["doc_id"], str)
            or not row["doc_id"].strip()
            or type(row["score"]) not in (int, float)
            or not math.isfinite(row["score"])
            for row in rows
        ):
            raise ValueError("invalid ranked result")


def compare_runs(baseline: dict, candidate: dict) -> dict:
    _validate_run(baseline)
    _validate_run(candidate)
    if baseline["source"] != candidate["source"]:
        raise ValueError("source snapshots differ")
    if set(baseline["metrics"]["per_query"]) != set(candidate["metrics"]["per_query"]):
        raise ValueError("paired query IDs differ")
    if baseline["method"] != "BM25" or candidate["method"] != "MiniLM (ONNX)":
        raise ValueError("expected the two frozen experiment methods")
    rows = []
    outcomes = {metric: {"improved": 0, "tied": 0, "declined": 0} for metric in METRICS}
    for qid in sorted(baseline["metrics"]["per_query"]):
        before = {metric: baseline["metrics"]["per_query"][qid][metric] for metric in METRICS}
        after = {metric: candidate["metrics"]["per_query"][qid][metric] for metric in METRICS}
        delta = {metric: after[metric] - before[metric] for metric in METRICS}
        for metric, value in delta.items():
            outcome = (
                "improved" if value > TOLERANCE else "declined" if value < -TOLERANCE else "tied"
            )
            outcomes[metric][outcome] += 1
        rows.append(
            {
                "query_id": qid,
                "baseline": before,
                "candidate": after,
                "delta": delta,
                "rankings": {
                    name: [
                        {"doc_id": row["doc_id"], "score": row["score"]}
                        for row in run["results"][qid]
                    ]
                    for name, run in (("baseline", baseline), ("candidate", candidate))
                },
            }
        )
    return {
        "schema_version": 1,
        "query_count": len(rows),
        "baseline": baseline["method"],
        "candidate": candidate["method"],
        "source": baseline["source"],
        "model": {key: candidate["model"][key] for key in ("model_id", "revision")},
        "encoding": candidate.get("encoding", {}),
        "tie_tolerance": TOLERANCE,
        "aggregate": {
            metric: {
                "baseline": baseline["metrics"]["aggregate"][metric],
                "candidate": candidate["metrics"]["aggregate"][metric],
                "delta": candidate["metrics"]["aggregate"][metric]
                - baseline["metrics"]["aggregate"][metric],
            }
            for metric in METRICS
        },
        "outcomes": outcomes,
        "rows": rows,
    }


def render_html(data: dict) -> str:
    template = Path(__file__).with_name("comparison_template.html").read_text(encoding="utf-8")
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    # JSON lives inside an HTML raw-text script element. Escaping '<' prevents an
    # ID from ending that element; UI code uses textContent for visible data.
    return template.replace(
        "__COMPARISON_DATA__", encoded.replace("<", "\\u003c").replace("&", "\\u0026")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("reports/scifact/bm25.json"))
    parser.add_argument("--candidate", type=Path, default=Path("reports/scifact/minilm.json"))
    parser.add_argument("--output-json", type=Path, default=Path("reports/scifact/comparison.json"))
    parser.add_argument("--output-html", type=Path, default=Path("reports/scifact/comparison.html"))
    args = parser.parse_args()
    raw = {"baseline": args.baseline.read_bytes(), "candidate": args.candidate.read_bytes()}
    data = compare_runs(json.loads(raw["baseline"]), json.loads(raw["candidate"]))
    data["input_results_sha256"] = {
        key: hashlib.sha256(value).hexdigest() for key, value in raw.items()
    }
    rendered = render_html(data)
    for path, content in (
        (args.output_json, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"),
        (args.output_html, rendered),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "queries": data["query_count"],
                "aggregate": data["aggregate"],
                "outcomes": data["outcomes"],
            },
            indent=2,
        )
    )

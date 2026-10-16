import importlib
import json

import pytest


def write_data(tmp_path, corpus=None, queries=None, qrels=None):
    corpus = (
        corpus
        if corpus is not None
        else [
            {"_id": "a", "title": "quantum", "text": "Synthetic abstract", "metadata": {}},
            {"_id": "b", "title": "gardens", "text": "Synthetic flowers", "metadata": {}},
        ]
    )
    queries = (
        queries
        if queries is not None
        else [
            {"_id": "q1", "text": "quantum", "metadata": {}},
            {"_id": "unused", "text": "do not evaluate this", "metadata": {}},
        ]
    )
    qrels = qrels if qrels is not None else "query-id\tcorpus-id\tscore\nq1\ta\t1\n"
    (tmp_path / "qrels").mkdir(exist_ok=True)
    for name, rows in [("corpus.jsonl", corpus), ("queries.jsonl", queries)]:
        (tmp_path / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "qrels/test.tsv").write_text(qrels)
    return tmp_path


def load(path):
    return importlib.import_module("paper_evidence_lab.benchmark_data").load_beir_files(path)


def test_selects_only_qrels_queries_and_preserves_text(tmp_path):
    data = load(write_data(tmp_path))
    assert data.queries == {"q1": "quantum"}
    assert data.all_query_count == 2
    assert data.documents["a"] == "quantum\nSynthetic abstract"
    assert data.qrels == {"q1": {"a": 1}}


@pytest.mark.parametrize(
    "qrels",
    [
        "wrong\theaders\there\nq1\ta\t1\n",
        "query-id\tcorpus-id\tscore\nq1\ta\t1\nq1\ta\t1\n",
        "query-id\tcorpus-id\tscore\nunknown\ta\t1\n",
        "query-id\tcorpus-id\tscore\nq1\tunknown\t1\n",
        "query-id\tcorpus-id\tscore\nq1\ta\t-1\n",
    ],
)
def test_qrel_errors_are_located(tmp_path, qrels):
    with pytest.raises(ValueError, match="test.tsv"):
        load(write_data(tmp_path, qrels=qrels))


def test_duplicate_corpus_id_and_malformed_json(tmp_path):
    row = {"_id": "a", "title": "quantum", "text": "synthetic", "metadata": {}}
    path = write_data(tmp_path, corpus=[row, row])
    with pytest.raises(ValueError, match="corpus.jsonl.*line 2"):
        load(path)
    (path / "corpus.jsonl").write_text("not-json\n")
    with pytest.raises(ValueError, match="corpus.jsonl.*line 1"):
        load(path)


def test_duplicate_query_id(tmp_path):
    row = {"_id": "q1", "text": "quantum", "metadata": {}}
    with pytest.raises(ValueError, match="queries.jsonl.*line 2"):
        load(write_data(tmp_path, queries=[row, row]))

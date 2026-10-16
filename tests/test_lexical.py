import importlib

import pytest


def test_benchmark_top10_does_not_weaken_m0(record):
    lexical = importlib.import_module("paper_evidence_lab.lexical").BM25LexicalIndex
    rows = [(str(i).zfill(2), "quantum identical text") for i in range(12, 0, -1)]
    assert [r.doc_id for r in lexical(rows).rank("quantum", 10)] == [
        str(i).zfill(2) for i in range(1, 11)
    ]
    from paper_evidence_lab.models import Document
    from paper_evidence_lab.retrieval import BM25Index

    with pytest.raises(ValueError):
        BM25Index([Document(**record)]).search("quantum", 6)


def test_exclusion_before_cutoff_and_zero_scores():
    lexical = importlib.import_module("paper_evidence_lab.lexical").BM25LexicalIndex
    index = lexical([("a", "quantum"), ("b", "quantum"), ("c", "flowers")])
    assert [r.doc_id for r in index.rank("quantum", 1, exclude_id="a")] == ["b"]
    assert index.rank("zzzznomatch", 10) == []

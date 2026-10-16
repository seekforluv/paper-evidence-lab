import importlib

import pytest


def index(records):
    Document = importlib.import_module("paper_evidence_lab.models").Document
    BM25Index = importlib.import_module("paper_evidence_lab.retrieval").BM25Index
    return BM25Index([Document(**r) for r in records])


def test_exact_match_and_no_zero_padding(record):
    other = dict(record, doc_id="synthetic-b", title="Gardening", abstract="Flowers bloom")
    results = index([other, record]).search("QUANTUM")
    assert [r.doc_id for r in results] == ["synthetic-a"]
    assert results[0].score > 0
    assert results[0].abstract == record["abstract"]


def test_no_match_or_only_stopwords(record):
    search = index([record]).search
    assert search("zzzznomatch") == []
    assert search("the and of") == []


def test_tie_is_resolved_before_cutoff(record):
    records = [dict(record, doc_id=x) for x in "fedcba"]
    for ordered in [records, list(reversed(records))]:
        assert [r.doc_id for r in index(ordered).search("quantum", 3)] == list("abc")


def test_missing_abstract_and_title(record):
    for updates, query in [({"abstract": None}, "compiler"), ({"title": None}, "quantum")]:
        row = record | updates
        result = index([row]).search(query)[0]
        assert result.abstract == row["abstract"]
        assert result.title == row["title"]
        assert result.abstract_missing is (row["abstract"] is None)
        assert result.title_missing is (row["title"] is None)


@pytest.mark.parametrize("query", ["", "  ", "1234 !!!", "中文", "AI开发", "かな", "한글", "𠀀AI"])
def test_invalid_query(record, query):
    with pytest.raises(ValueError):
        index([record]).search(query)


@pytest.mark.parametrize("k", [0, 6, -1, 1.5, True])
def test_invalid_top_k(record, k):
    with pytest.raises(ValueError):
        index([record]).search("quantum", k)


def test_document_with_no_tokens_and_empty_vocabulary(record):
    empty = dict(record, doc_id="empty", title="the and", abstract=None)
    assert index([empty]).search("quantum") == []
    assert [r.doc_id for r in index([empty, record]).search("quantum")] == [record["doc_id"]]


@pytest.mark.parametrize("query", ["AI 가", "AI \ua960", "AI \U0001b000", "AI \ud800"])
def test_review_unicode_query_boundaries(record, query):
    with pytest.raises(ValueError):
        index([record]).search(query)

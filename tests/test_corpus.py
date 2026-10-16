import importlib
import json

import pytest


def loader():
    # Import inside a test so the initial missing implementation is an observed failure.
    return importlib.import_module("paper_evidence_lab.corpus").load_corpus


def write(tmp_path, rows):
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def test_preserves_original_text_and_nullable_fields(tmp_path, record):
    record.update(title=None, abstract="  Quantum\ntext with exact spacing.  ")
    doc = loader()(write(tmp_path, [record]))[0]
    assert doc.title is None
    assert doc.abstract == record["abstract"]
    assert doc.fetched_at == record["fetched_at"]


@pytest.mark.parametrize(
    "patch",
    [
        {"doc_id": " "},
        {"title": 12},
        {"abstract": []},
        {"language": "zh"},
        {"source_type": "blog"},
        {"source_url": "javascript:alert(1)"},
        {"source_url": "https://"},
        {"source_url": "https://user:secret@example.org/"},
        {"license_url": 42},
        {"fetched_at": "yesterday"},
        {"title": None, "abstract": None},
        {"title": " ", "abstract": None},
        {"surprise": "unknown field"},
    ],
)
def test_bad_data_reports_line(tmp_path, record, patch):
    bad = dict(record, doc_id="synthetic-b") | patch
    with pytest.raises(ValueError, match=r"line 2"):
        loader()(write(tmp_path, [record, bad]))


def test_missing_field_and_duplicate_id(tmp_path, record):
    missing = dict(record)
    del missing["abstract"]
    for rows, line in [([missing], 1), ([record, record], 2)]:
        with pytest.raises(ValueError, match=rf"line {line}"):
            loader()(write(tmp_path, rows))


@pytest.mark.parametrize(
    "raw", ["{bad}\n", "\n", "[]\n", '{"doc_id":"a","doc_id":"b"}\n', '{"title":NaN}\n']
)
def test_not_strict_jsonl(tmp_path, raw):
    path = tmp_path / "bad.jsonl"
    path.write_text(raw)
    with pytest.raises(ValueError, match=r"line 1"):
        loader()(path)


def test_empty_corpus(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.touch()
    with pytest.raises(ValueError, match="empty"):
        loader()(path)


@pytest.mark.parametrize(
    "patch",
    [
        {"title": "quantum \ud800"},
        {"doc_id": "id\udfff"},
        {"source_url": "https://:secret@example.org/"},
    ],
)
def test_review_invalid_unicode_and_empty_username(tmp_path, record, patch):
    with pytest.raises(ValueError, match="line 1"):
        loader()(write(tmp_path, [record | patch]))


def test_invalid_utf8_has_line_number(tmp_path, record):
    path = write(tmp_path, [record])
    path.write_bytes(path.read_bytes() + b"\xff\n")
    with pytest.raises(ValueError, match="line 2"):
        loader()(path)

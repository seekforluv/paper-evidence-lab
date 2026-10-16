import importlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic.jsonl"


def run(query, capsys, *extra):
    main = importlib.import_module("paper_evidence_lab.cli").main
    code = main(["search", "--corpus", str(FIXTURE), "--query", query, *extra])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_json_only_and_repeatable(capsys):
    code, first, err = run("developer productivity", capsys)
    assert code == 0 and not err
    rows = json.loads(first)
    assert rows[0]["doc_id"] == "synthetic-developer"
    assert len(rows) == 2
    assert rows[1]["abstract"] is None and rows[1]["abstract_missing"]
    assert run("developer productivity", capsys)[1] == first


def test_no_match_is_success_with_explanation(capsys):
    code, out, err = run("zzzznomatch", capsys)
    assert code == 0 and json.loads(out) == []
    assert "无匹配" in err


@pytest.mark.parametrize(
    "query, extra", [("中文", []), (" ", []), ("AI", ["--top-k", "6"]), ("123", [])]
)
def test_invalid_input_has_no_result_output(capsys, query, extra):
    code, out, err = run(query, capsys, *extra)
    assert code == 2 and out == "" and err


def test_bad_corpus_is_clean_error(tmp_path, capsys):
    main = importlib.import_module("paper_evidence_lab.cli").main
    path = tmp_path / "bad.jsonl"
    path.write_text("not json")
    assert main(["search", "--corpus", str(path), "--query", "AI"]) == 2
    captured = capsys.readouterr()
    assert not captured.out and "line 1" in captured.err and "Traceback" not in captured.err


def test_markdown_is_only_serialized_fields_and_safe_text(record):
    from paper_evidence_lab.models import SearchResult

    render = importlib.import_module("paper_evidence_lab.report").render_markdown
    record.update(
        title='<script>alert("x")</script>', abstract="[click](javascript:alert(1))\n# fake"
    )
    row = SearchResult(**record, score=0.5, title_missing=False, abstract_missing=False)
    markdown = render("quantum", [row])
    assert "<script>" not in markdown
    assert "[click](javascript:" not in markdown
    assert "\n# fake" not in markdown
    assert "&lt;script&gt;" in markdown
    # Every JSON field is exposed; the renderer never synthesizes an abstract or verdict.
    assert all(key in markdown for key in asdict(row))
    assert "55.8%" not in markdown and "19%" not in markdown


def test_report_missing_abstract(capsys):
    code, markdown, err = run("developer", capsys, "--format", "markdown")
    assert code == 0 and not err
    assert "缺失" in markdown and "abstract_missing" in markdown


def test_source_text_cannot_create_setext_heading(record):
    from paper_evidence_lab.models import SearchResult

    render = importlib.import_module("paper_evidence_lab.report").render_markdown
    record["abstract"] = "source text\n==="
    row = SearchResult(**record, score=0.5, title_missing=False, abstract_missing=False)
    assert "\n===" not in render("quantum", [row])

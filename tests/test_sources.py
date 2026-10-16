import importlib
import io
import json
from urllib.error import HTTPError

import pytest

VERSION = "9999.00001v2"
SOURCE = {"arxiv_id": VERSION, "license_url": None}
ATOM = f"""<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/{VERSION}</id><title>Synthetic title</title>
<summary>  Synthetic abstract\nwith preserved whitespace.  </summary></entry></feed>"""


def module():
    return importlib.import_module("paper_evidence_lab.sources")


def test_parse_preserves_summary_and_version():
    doc = module().parse_atom(ATOM.encode(), [SOURCE], "2026-01-01T00:00:00Z")[0]
    assert doc.doc_id == "arxiv:9999.00001v2"
    assert doc.abstract == "  Synthetic abstract\nwith preserved whitespace.  "
    assert doc.source_url == "https://arxiv.org/abs/9999.00001v2"
    assert doc.source_type == "preprint" and doc.license_url is None


def test_missing_abstract_is_null():
    raw = ATOM.replace("<summary>  Synthetic abstract\nwith preserved whitespace.  </summary>", "")
    assert module().parse_atom(raw.encode(), [SOURCE], "2026-01-01T00:00:00Z")[0].abstract is None


@pytest.mark.parametrize(
    "raw",
    [
        ATOM.replace(VERSION, "9999.00001v3"),
        "<html>unavailable</html>",
        "<broken",
        ATOM.replace(
            "</feed>", ATOM.split("<entry>")[1].replace("</feed>", "").join(["<entry>", "</feed>"])
        ),
        ATOM.replace("http://arxiv.org", "https://example.org"),
    ],
)
def test_rejects_wrong_missing_duplicate_and_invalid_responses(raw):
    with pytest.raises(ValueError):
        module().parse_atom(raw.encode(), [SOURCE], "2026-01-01T00:00:00Z")


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timeout"), HTTPError("https://export.arxiv.org", 503, "unavailable", {}, None)],
)
def test_fetch_network_failure_creates_no_output(tmp_path, monkeypatch, error):
    sources = module()

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(sources, "urlopen", fail)
    path = tmp_path / "new.jsonl"
    with pytest.raises(ValueError, match="fetch"):
        sources.fetch_corpus([SOURCE], path)
    assert list(tmp_path.iterdir()) == []


def test_fetch_writes_validated_corpus_and_preserves_raw_response(tmp_path, monkeypatch):
    sources = module()

    def fake(request, timeout):
        assert "id_list=9999.00001v2" in request.full_url and timeout > 0
        return io.BytesIO(ATOM.encode())

    monkeypatch.setattr(sources, "urlopen", fake)
    path = tmp_path / "seeds.jsonl"
    docs = sources.fetch_corpus([SOURCE], path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["abstract"] == docs[0].abstract
    assert path.with_name(path.name + ".atom.xml").read_bytes() == ATOM.encode()
    receipt = json.loads(path.with_name(path.name + ".receipt.json").read_text())
    assert receipt["ids"] == [VERSION] and receipt["response_sha256"]


def test_bad_response_leaves_no_corpus(tmp_path, monkeypatch):
    sources = module()
    monkeypatch.setattr(sources, "urlopen", lambda *a, **k: io.BytesIO(b"<feed/>"))
    path = tmp_path / "seeds.jsonl"
    with pytest.raises(ValueError):
        sources.fetch_corpus([SOURCE], path)
    assert not path.exists()


def test_existing_fetch_snapshot_is_immutable(tmp_path, monkeypatch):
    sources = module()
    monkeypatch.setattr(sources, "urlopen", lambda *a, **k: io.BytesIO(ATOM.encode()))
    path = tmp_path / "seeds.jsonl"
    sources.fetch_corpus([SOURCE], path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="exists"):
        sources.fetch_corpus([SOURCE], path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_different_filenames_do_not_share_provenance(tmp_path, monkeypatch):
    sources = module()
    monkeypatch.setattr(sources, "urlopen", lambda *a, **k: io.BytesIO(ATOM.encode()))
    sources.fetch_corpus([SOURCE], tmp_path / "seeds.jsonl")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    sources.fetch_corpus([SOURCE], tmp_path / "seeds.json")
    assert all((tmp_path / name).read_bytes() == data for name, data in before.items())
    assert len(list(tmp_path.iterdir())) == 6


def test_mid_publish_failure_removes_new_partial_snapshot(tmp_path, monkeypatch):
    sources = module()
    monkeypatch.setattr(sources, "urlopen", lambda *a, **k: io.BytesIO(ATOM.encode()))
    path = tmp_path / "seeds.jsonl"
    original_link = sources.os.link
    original_replace = sources.os.replace

    def fail_last_link(src, dst, *a, **k):
        if dst == path:
            raise PermissionError("simulated final publish error")
        return original_link(src, dst, *a, **k)

    def fail_last_replace(src, dst, *a, **k):
        if dst == path:
            raise PermissionError("simulated final publish error")
        return original_replace(src, dst, *a, **k)

    monkeypatch.setattr(sources.os, "link", fail_last_link)
    monkeypatch.setattr(sources.os, "replace", fail_last_replace)
    with pytest.raises(OSError):
        sources.fetch_corpus([SOURCE], path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "declaration", ["<!DOCTYPE feed>", '<!DOCTYPE feed [<!ENTITY x "invented">]>']
)
def test_xml_declarations_cannot_supply_source_text(declaration):
    with pytest.raises(ValueError):
        module().parse_atom((declaration + ATOM).encode(), [SOURCE], "2026-01-01T00:00:00Z")


@pytest.mark.parametrize("authority", ["arxiv.org:1234", "user@arxiv.org"])
def test_source_identifier_has_exact_arxiv_authority(authority):
    raw = ATOM.replace("http://arxiv.org", "http://" + authority)
    with pytest.raises(ValueError):
        module().parse_atom(raw.encode(), [SOURCE], "2026-01-01T00:00:00Z")

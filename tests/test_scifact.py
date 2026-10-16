import hashlib
import importlib
import io
import json
import zipfile

import pytest


@pytest.fixture
def source(monkeypatch):
    module = importlib.import_module("paper_evidence_lab.scifact")
    raw = {
        "corpus.jsonl": b'{"_id":"a","title":"quantum","text":"Synthetic study"}\n',
        "queries.jsonl": b'{"_id":"q1","text":"quantum"}\n',
        "qrels/test.tsv": b"query-id\tcorpus-id\tscore\nq1\ta\t1\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("scifact/", b"")
        archive.writestr("scifact/qrels/", b"")
        archive.writestr("scifact/qrels/train.tsv", b"unused")
        for name, content in raw.items():
            archive.writestr("scifact/" + name, content)
    blob = buffer.getvalue()
    manifest = {
        "dataset": "synthetic",
        "split": "test",
        "source_url": "https://example.org/scifact.zip",
        "archive_bytes": len(blob),
        "archive_md5": hashlib.md5(blob).hexdigest(),
        "archive_sha256": hashlib.sha256(blob).hexdigest(),
        "files_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()},
        "counts": {"corpus": 1, "all_queries": 1, "test_queries": 1, "qrel_pairs": 1},
    }
    monkeypatch.setattr(module, "source_manifest", lambda: manifest)
    monkeypatch.setattr(
        importlib.import_module("paper_evidence_lab.benchmark"), "source_manifest", lambda: manifest
    )
    return module, blob, manifest


def test_import_and_verified_load(source, tmp_path):
    module, blob, manifest = source
    root = tmp_path / "snapshot"
    receipt = module.acquire_scifact(root, archive_bytes=blob)
    assert receipt["archive_sha256"] == manifest["archive_sha256"]
    assert (root / "source.zip").read_bytes() == blob
    data = module.load_verified_scifact(root)
    assert data.queries == {"q1": "quantum"}
    assert not (root / "qrels/train.tsv").exists()


def test_mismatch_never_publishes_and_existing_target_preserved(source, tmp_path):
    module, blob, _ = source
    root = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="archive"):
        module.acquire_scifact(root, archive_bytes=blob + b"x")
    assert not root.exists()
    module.acquire_scifact(root, archive_bytes=blob)
    before = (root / "receipt.json").read_bytes()
    with pytest.raises(FileExistsError):
        module.acquire_scifact(root, archive_bytes=blob)
    assert (root / "receipt.json").read_bytes() == before


def test_modified_data_rejected_even_with_modified_receipt(source, tmp_path):
    module, blob, _ = source
    module.acquire_scifact(tmp_path / "snapshot", archive_bytes=blob)
    root = tmp_path / "snapshot"
    (root / "queries.jsonl").write_bytes(b'{"_id":"q1","text":"changed"}\n')
    receipt = json.loads((root / "receipt.json").read_text())
    receipt["files_sha256"]["queries.jsonl"] = hashlib.sha256(
        (root / "queries.jsonl").read_bytes()
    ).hexdigest()
    (root / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="receipt|queries.jsonl"):
        module.load_verified_scifact(root)


def test_exact_counts_checked_before_publication(source, tmp_path):
    module, blob, manifest = source
    manifest["counts"]["test_queries"] = 2
    with pytest.raises(ValueError, match="counts"):
        module.acquire_scifact(tmp_path / "snapshot", archive_bytes=blob)
    assert not (tmp_path / "snapshot").exists()


def test_archive_paths_are_not_extracted(source, tmp_path):
    module, blob, manifest = source
    buffer = io.BytesIO(blob)
    with zipfile.ZipFile(buffer, "a") as archive:
        archive.writestr("../escaped", b"unsafe")
    blob = buffer.getvalue()
    manifest.update(
        archive_bytes=len(blob),
        archive_md5=hashlib.md5(blob).hexdigest(),
        archive_sha256=hashlib.sha256(blob).hexdigest(),
    )
    with pytest.raises(ValueError, match="members"):
        module.acquire_scifact(tmp_path / "snapshot", archive_bytes=blob)
    assert not (tmp_path / "escaped").exists()


def test_failure_cleans_only_created_snapshot(source, tmp_path, monkeypatch):
    from pathlib import Path

    module, blob, _ = source
    original = Path.write_bytes

    def broken(path, content):
        if path.name == "queries.jsonl":
            raise OSError("synthetic write failure")
        return original(path, content)

    monkeypatch.setattr(Path, "write_bytes", broken)
    with pytest.raises(OSError, match="synthetic"):
        module.acquire_scifact(tmp_path / "snapshot", archive_bytes=blob)
    assert not (tmp_path / "snapshot").exists()


def test_deterministic_text_free_evaluation(source, tmp_path):
    module, blob, _ = source
    benchmark = importlib.import_module("paper_evidence_lab.benchmark")
    module.acquire_scifact(tmp_path / "snapshot", archive_bytes=blob)
    first = benchmark.evaluate_bm25(tmp_path / "snapshot")
    assert first == benchmark.evaluate_bm25(tmp_path / "snapshot")
    assert first["metrics"]["aggregate"] == {"ndcg": 1.0, "recall": 1.0}
    assert first["metrics"]["query_count"] == 1
    serialized = json.dumps(first)
    assert "Synthetic study" not in serialized and "quantum" not in serialized
    assert str(tmp_path) not in serialized


def test_reference_checker_rejects_missing_provenance(source, tmp_path):
    import runpy
    from pathlib import Path

    module, blob, _ = source
    benchmark = importlib.import_module("paper_evidence_lab.benchmark")
    root = tmp_path / "snapshot"
    module.acquire_scifact(root, archive_bytes=blob)
    result = benchmark.evaluate_bm25(root)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result))
    check = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_evaluation.py"))["check"]
    assert check(root, result_path)["passed"]
    for invalid_source in ({}, {"dataset": "synthetic"}, None):
        result["source"] = invalid_source
        result_path.write_text(json.dumps(result))
        with pytest.raises(ValueError, match="provenance"):
            check(root, result_path)


def test_reference_checker_supports_dense_negative_scores(source, tmp_path):
    import runpy
    from pathlib import Path

    from paper_evidence_lab.model_assets import model_manifest

    module, blob, _ = source
    benchmark = importlib.import_module("paper_evidence_lab.benchmark")
    root = tmp_path / "snapshot"
    module.acquire_scifact(root, archive_bytes=blob)
    result = benchmark.evaluate_bm25(root)
    result["results"]["q1"][0]["score"] = -0.25
    result_path = tmp_path / "result.json"
    check = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_evaluation.py"))["check"]
    result_path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="invalid ranked"):
        check(root, result_path)
    result["method"] = "MiniLM (ONNX)"
    result["config"]["positive_scores_only"] = False
    result["model"] = model_manifest()
    result_path.write_text(json.dumps(result))
    assert check(root, result_path)["passed"]

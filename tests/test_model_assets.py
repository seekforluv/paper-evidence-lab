import hashlib
import importlib
import json

import pytest


def test_model_snapshot_integrity_and_no_overwrite(tmp_path, monkeypatch):
    module = importlib.import_module("paper_evidence_lab.model_assets")
    source = tmp_path / "source"
    source.mkdir()
    raw = b"original synthetic model bytes"
    (source / "model.bin").write_bytes(raw)
    manifest = {
        "model_id": "synthetic",
        "revision": "fixed",
        "files": {"model.bin": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}},
    }
    monkeypatch.setattr(module, "model_manifest", lambda: manifest)
    output = tmp_path / "output"
    module.acquire_model(output, source_directory=source)
    assert module.load_verified_model(output) == {"model.bin": raw}
    with pytest.raises(FileExistsError):
        module.acquire_model(output, source_directory=source)
    (output / "model.bin").write_bytes(b"tampered")
    receipt = json.loads((output / "receipt.json").read_text())
    receipt["files"]["model.bin"]["sha256"] = hashlib.sha256(b"tampered").hexdigest()
    (output / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        module.load_verified_model(output)
    (source / "model.bin").write_bytes(b"bad")
    with pytest.raises(ValueError):
        module.acquire_model(tmp_path / "bad-output", source_directory=source)
    assert not (tmp_path / "bad-output").exists()

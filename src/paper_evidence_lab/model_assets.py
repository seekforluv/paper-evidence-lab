"""Immutable, hash-pinned local model snapshots; inference never downloads assets."""

import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path


def model_manifest() -> dict:
    return json.loads(files("paper_evidence_lab").joinpath("minilm_source.json").read_text())


def _verify(name: str, content: bytes, record: dict) -> None:
    if len(content) != record["bytes"] or hashlib.sha256(content).hexdigest() != record["sha256"]:
        raise ValueError(f"model asset {name}: size/hash differs from pinned source")


def acquire_model(output: Path, source_directory: Path | None = None) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"model snapshot already exists: {output}")
    manifest = model_manifest()
    raw = {}
    for name, record in manifest["files"].items():
        if source_directory is not None:
            with (source_directory / name).open("rb") as stream:
                raw[name] = stream.read(record["bytes"] + 1)
        else:
            request = urllib.request.Request(
                record["source_url"], headers={"User-Agent": "paper-evidence-lab/0.3"}
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                raw[name] = response.read(record["bytes"] + 1)
        _verify(name, raw[name], record)
    receipt = {
        "schema_version": 1,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        **manifest,
    }
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, content in raw.items():
            destination = output / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(output)
        raise
    return receipt


def load_verified_model(root: Path) -> dict[str, bytes]:
    manifest = model_manifest()
    receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in manifest.items()):
        raise ValueError("model receipt differs from pinned source")
    raw = {}
    for name, record in manifest["files"].items():
        with (root / name).open("rb") as stream:
            raw[name] = stream.read(record["bytes"] + 1)
        _verify(name, raw[name], record)
    return raw

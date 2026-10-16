"""Fail closed on malformed JSONL; never silently drop a document."""

import json
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from .models import Document


def validate_url(value: object) -> None:
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("URL must be an http(s) string without whitespace")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("URL must have an http(s) host and no credentials")
    # Accessing port also rejects malformed/out-of-range ports.
    _ = parsed.port


def validate_document(row: object) -> Document:
    required = {field.name for field in fields(Document)}
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("expected exactly these fields: " + ", ".join(sorted(required)))
    for value in row.values():
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("text contains an unpaired Unicode surrogate") from exc
    if not isinstance(row["doc_id"], str) or not row["doc_id"].strip():
        raise ValueError("doc_id must be a nonempty string")
    if any(ord(c) < 32 for c in row["doc_id"]):
        raise ValueError("doc_id contains a control character")
    for key in ("title", "abstract"):
        value = row[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{key} must be nonblank text or null")
    if row["title"] is None and row["abstract"] is None:
        raise ValueError("title and abstract cannot both be null")
    if row["source_type"] not in ("paper", "preprint"):
        raise ValueError("source_type must be paper or preprint; blogs are excluded")
    if row["language"] != "en":
        raise ValueError("language must be en in M0")
    validate_url(row["source_url"])
    if row["license_url"] is not None:
        validate_url(row["license_url"])
    try:
        timestamp = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("timezone required")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("fetched_at must be an ISO 8601 timestamp with timezone") from exc
    return Document(**row)


def _unique_keys(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise ValueError(f"duplicate JSON key: {key}")
        row[key] = value
    return row


def _invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def load_corpus(path: Path) -> list[Document]:
    documents = []
    ids = set()
    with path.open("rb") as stream:
        for line_number, raw in enumerate(stream, 1):
            try:
                line = raw.decode("utf-8")
                row = json.loads(
                    line, object_pairs_hook=_unique_keys, parse_constant=_invalid_constant
                )
                doc = validate_document(row)
                if doc.doc_id in ids:
                    raise ValueError(f"duplicate doc_id: {doc.doc_id}")
            except ValueError as exc:
                raise ValueError(f"line {line_number}: {exc}") from exc
            ids.add(doc.doc_id)
            documents.append(doc)
    if not documents:
        raise ValueError("empty corpus")
    return documents

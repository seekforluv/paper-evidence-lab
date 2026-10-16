"""Immutable, source-preserving records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str | None
    abstract: str | None
    source_url: str
    source_type: str
    language: str
    license_url: str | None
    fetched_at: str


@dataclass(frozen=True)
class SearchResult(Document):
    score: float
    title_missing: bool
    abstract_missing: bool

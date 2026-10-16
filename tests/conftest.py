import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """A network call during unit tests is always a bug."""

    def deny(*args, **kwargs):
        raise AssertionError("network access forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)


@pytest.fixture
def record():
    return {
        "doc_id": "synthetic-a",
        "title": "Quantum compiler example",
        "abstract": "An invented fixture about quantum compilation, not a research finding.",
        "source_url": "https://example.org/synthetic-a",
        "source_type": "paper",
        "language": "en",
        "license_url": None,
        "fetched_at": "2026-01-01T00:00:00Z",
    }

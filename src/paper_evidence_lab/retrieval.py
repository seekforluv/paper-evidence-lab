"""Source-preserving top-five presentation over the shared lexical ranker."""

from dataclasses import asdict

from .corpus import validate_document
from .lexical import BM25LexicalIndex
from .models import Document, SearchResult


class BM25Index:
    def __init__(self, documents: list[Document]):
        self.documents = [validate_document(asdict(doc)) for doc in documents]
        self.lexical = BM25LexicalIndex(
            [(doc.doc_id, f"{doc.title or ''}\n{doc.abstract or ''}") for doc in self.documents]
        )
        self.by_id = {doc.doc_id: doc for doc in self.documents}

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if type(k) is not int or not 1 <= k <= 5:
            raise ValueError("top_k must be an integer from 1 to 5")
        results = []
        for ranked in self.lexical.rank(query, k):
            doc = self.by_id[ranked.doc_id]
            results.append(
                SearchResult(
                    **asdict(doc),
                    score=ranked.score,
                    title_missing=doc.title is None,
                    abstract_missing=doc.abstract is None,
                )
            )
        return results

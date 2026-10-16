"""Small-corpus BM25; scores rank lexical relevance, never evidence quality."""

import re
from dataclasses import asdict

import bm25s

from .corpus import validate_document
from .models import Document, SearchResult

STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or that the to was with".split()
)
CJK = re.compile(
    "[\u1100-\u11ff\u2e80-\ua4cf\ua960-\ua97f\uac00-\ud7ff\uf900-\ufaff\uff00-\uffef"
    "\U0001aff0-\U0001b2ff\U00020000-\U000323af]"
)


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z]+", text.lower()) if word not in STOPWORDS]


class BM25Index:
    def __init__(self, documents: list[Document]):
        if not documents:
            raise ValueError("empty corpus")
        self.documents = sorted(
            (validate_document(asdict(doc)) for doc in documents), key=lambda doc: doc.doc_id
        )
        if len({doc.doc_id for doc in self.documents}) != len(self.documents):
            raise ValueError("duplicate doc_id")
        tokens = [tokenize(f"{doc.title or ''}\n{doc.abstract or ''}") for doc in self.documents]
        self.model = None
        if any(tokens):
            self.model = bm25s.BM25(method="lucene", idf_method="lucene", k1=1.5, b=0.75)
            self.model.index(tokens, show_progress=False)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if type(k) is not int or not 1 <= k <= 5:
            raise ValueError("top_k must be an integer from 1 to 5")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("查询不能为空 / query must not be empty")
        try:
            query.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("query contains an unpaired Unicode surrogate") from exc
        if CJK.search(query):
            raise ValueError("当前仅支持英文查询 / English queries only")
        if not re.search(r"[a-zA-Z]", query):
            raise ValueError("查询必须包含英文字母 / query must contain English letters")
        tokens = tokenize(query)
        if not tokens or self.model is None:
            return []
        scores = self.model.get_scores(tokens)
        # Sort ALL positive matches before truncation, including ties beyond k.
        ranked = sorted(
            ((doc, float(score)) for doc, score in zip(self.documents, scores) if score > 0),
            key=lambda pair: (-pair[1], pair[0].doc_id),
        )
        return [
            SearchResult(
                **asdict(doc),
                score=score,
                title_missing=doc.title is None,
                abstract_missing=doc.abstract is None,
            )
            for doc, score in ranked[:k]
        ]

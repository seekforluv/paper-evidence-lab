"""Shared lexical ranker; presentation limits belong to callers."""

import re
from dataclasses import dataclass

import bm25s

STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or that the to was with".split()
)
CJK = re.compile(
    "[\u1100-\u11ff\u2e80-\ua4cf\ua960-\ua97f\uac00-\ud7ff\uf900-\ufaff\uff00-\uffef"
    "\U0001aff0-\U0001b2ff\U00020000-\U000323af]"
)
CONFIG = {
    "method": "lucene",
    "idf_method": "lucene",
    "k1": 1.5,
    "b": 0.75,
    "backend": "numpy",
    "csc_backend": "numpy",
    "dtype": "float32",
    "token_pattern": "[a-z]+",
    "lowercase": True,
    "stemmer": None,
    "stopwords": sorted(STOPWORDS),
    "retain_repeated_query_terms": True,
    "positive_scores_only": True,
    "tie_break": "doc_id ascending",
}


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z]+", text.lower()) if word not in STOPWORDS]


def query_tokens(query: str) -> list[str]:
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
    return tokenize(query)


@dataclass(frozen=True)
class RankedDocument:
    doc_id: str
    score: float


class BM25LexicalIndex:
    def __init__(self, documents: list[tuple[str, str]]):
        if not documents:
            raise ValueError("empty corpus")
        for doc_id, text in documents:
            if not isinstance(doc_id, str) or not doc_id.strip() or not isinstance(text, str):
                raise ValueError("nonblank string IDs and string text required")
        ordered = sorted(documents)
        self.ids = [doc_id for doc_id, _ in ordered]
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("duplicate doc_id")
        tokens = [tokenize(text) for _, text in ordered]
        self.model = None
        if any(tokens):
            self.model = bm25s.BM25(
                method="lucene",
                idf_method="lucene",
                k1=1.5,
                b=0.75,
                backend="numpy",
                csc_backend="numpy",
                dtype="float32",
            )
            self.model.index(tokens, show_progress=False)

    def rank(self, query: str, k: int = 10, exclude_id: str | None = None) -> list[RankedDocument]:
        if type(k) is not int or not 1 <= k <= 1000:
            raise ValueError("ranking k must be an integer from 1 to 1000")
        tokens = query_tokens(query)
        if not tokens or self.model is None:
            return []
        scores = self.model.get_scores(tokens)
        ranked = sorted(
            (
                RankedDocument(doc_id, float(score))
                for doc_id, score in zip(self.ids, scores)
                if score > 0 and doc_id != exclude_id
            ),
            key=lambda row: (-row.score, row.doc_id),
        )
        return ranked[:k]

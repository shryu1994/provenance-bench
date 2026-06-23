"""A tiny BM25 retriever over corpus spans — standard library only, fully offline.

Ported from cite-or-refuse (Chunk -> Span). The point of the benchmark is the grounding +
abstention + scoring discipline, not the retrieval model; swap in a vector store and nothing
downstream changes.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from .types import Span

_WORD = re.compile(r"[a-z0-9]+")


def _stem(token: str) -> str:
    """Crude, dependency-free normalizer: collapse simple plural / 3rd-person 's'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower())]


@dataclass(frozen=True)
class Retrieved:
    span: Span
    score: float


class BM25Retriever:
    def __init__(self, spans: Sequence[Span], k1: float = 1.5, b: float = 0.75):
        self.spans = list(spans)
        self.k1 = k1
        self.b = b
        self._docs = [tokenize(s.text) for s in self.spans]
        self._len = [len(d) for d in self._docs]
        self._avglen = (sum(self._len) / len(self._docs)) if self._docs else 0.0
        self._tf = [Counter(d) for d in self._docs]
        df: Counter[str] = Counter()
        for d in self._docs:
            for term in set(d):
                df[term] += 1
        n = len(self._docs)
        self._idf = {term: math.log(1 + (n - dfi + 0.5) / (dfi + 0.5)) for term, dfi in df.items()}

    def idf(self, term: str) -> float:
        """IDF of a term (0.0 if it never appears in the corpus) — used by the undocumented-term gate."""
        return self._idf.get(term, 0.0)

    def _score(self, query_terms: Sequence[str], i: int) -> float:
        tf = self._tf[i]
        dl = self._len[i]
        score = 0.0
        for term in query_terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            idf = self._idf.get(term, 0.0)
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self._avglen or 1))
            score += idf * (freq * (self.k1 + 1)) / denom
        return score

    def search(self, query: str, top_k: int = 3) -> list[Retrieved]:
        q = tokenize(query)
        scored = [Retrieved(self.spans[i], self._score(q, i)) for i in range(len(self.spans))]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

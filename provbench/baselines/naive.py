"""Naive baseline — always answers with the top lexical match. Never abstains.

This is the strawman: it has no notion of "the docs don't support this", so on every
unanswerable case it confidently cites whatever span shared the most words. It exists to
show the benchmark discriminates — a system that never abstains should score near-zero on
the abstain half and rack up Over-Responsiveness errors.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..retrieval import BM25Retriever, tokenize
from ..types import Answer, Claim, ResponseKind, Span, SystemFn

_SENT = re.compile(r"(?<=[.!?])\s+")


def _best_sentence(question: str, text: str) -> str:
    q = set(tokenize(question))
    sentences = [s.strip() for s in _SENT.split(text) if s.strip()] or [text]
    return max(sentences, key=lambda s: len(q & set(tokenize(s))))


def build_naive(spans: Sequence[Span], top_k: int = 3) -> SystemFn:
    retriever = BM25Retriever(spans)

    def system(question: str) -> tuple[Answer, Sequence[Span]]:
        hits = retriever.search(question, top_k=top_k)
        retrieved = [h.span for h in hits]
        if not hits:
            # even with nothing retrieved it refuses to abstain — emits an ungrounded claim
            return Answer(kind=ResponseKind.ANSWER, claims=(Claim(text="(no source)", span_ids=()),)), retrieved
        top = hits[0].span
        claim = Claim(text=_best_sentence(question, top.text), span_ids=(top.span_id,))
        return Answer(kind=ResponseKind.ANSWER, claims=(claim,)), retrieved

    return system

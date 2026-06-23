"""Grounded baseline — the cite-or-refuse method, ported to spans.

Two cheap, transparent gates keep confident hallucination out:
  1. Undocumented-term guard — if a question's content word appears NOWHERE in the corpus,
     refuse instead of matching on the generic words it shares.
  2. IDF-weighted relevance floor — the best sentence must clear a distinctiveness bar.

Honest limitation, and the reason this is a *baseline*: it abstains correctly far more often
than it identifies *why*. It reports a single generic reason — `out_of_database` — for almost
all refusals, so on the benchmark it will score well on "did it abstain?" but poorly on
"abstained for the right reason?" (RefusalBench's categorization sub-skill). That gap is the
point of measuring both.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..retrieval import BM25Retriever, Retrieved, tokenize
from ..types import Answer, Claim, ResponseKind, Span, SystemFn

_STOPWORDS_RAW = """
    a an the this that these those
    i you he she it we they me him her us them my your his its our their
    is am are was were be been being do does did doing done have has had having
    can could will would shall should may might must
    of to in on at for with from by about as into than then over under up down out off
    and or but if so because while
    how what which who whom whose when where why
    much many more most less least some any all no none both each every
    not yes get got here there
    please just also only really very quite too able
    long short quickly fast slow slowly soon often always never sometimes far near
    big small good bad better worse best worst new old high low
    someone something anyone anything everyone everything somebody anybody nobody nothing
    before after during until
""".split()
_STOP = frozenset(tokenize(" ".join(_STOPWORDS_RAW)))

_OUT_OF_SCOPE_PATTERNS = [
    r"\breset my\b",
    r"\bmy (lims|account|password)\b",
    r"\bcancel my\b",
    r"\b(better|worse) than\b",
    r"\bcompetitors?\b",
]

_SENT = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if s.strip()]


class GroundedSystem:
    def __init__(
        self,
        retriever: BM25Retriever,
        min_score: float = 2.0,
        top_k: int = 3,
        cite_margin: float = 0.65,
        answer_floor: float = 2.5,
    ):
        self.retriever = retriever
        self.min_score = min_score
        self.top_k = top_k
        self.cite_margin = cite_margin
        self.answer_floor = answer_floor

    def _content_terms(self, question: str) -> list[str]:
        return [t for t in tokenize(question) if t not in _STOP]

    def _abstain(self, msg: str) -> Answer:
        return Answer(kind=ResponseKind.ABSTAIN, abstain_category="out_of_database", message=msg)

    def __call__(self, question: str) -> tuple[Answer, Sequence[Span]]:
        if any(re.search(p, question.lower()) for p in _OUT_OF_SCOPE_PATTERNS):
            return Answer(kind=ResponseKind.OUT_OF_SCOPE, message="Outside what this assistant answers."), []

        # Gate 1 — undocumented-term guard.
        if any(self.retriever.idf(t) == 0.0 for t in self._content_terms(question)):
            return self._abstain("The question mentions something the documents don't cover."), []

        hits = self.retriever.search(question, top_k=self.top_k)
        retrieved = [h.span for h in hits]
        if not hits or hits[0].score < self.min_score:
            return self._abstain("The answer isn't in the provided documents."), retrieved

        claims = self._extract_claims(question, hits)
        if not claims:
            return self._abstain("The documents are related but don't directly answer this."), retrieved
        return Answer(kind=ResponseKind.ANSWER, claims=tuple(claims)), retrieved

    def _relevance(self, q_terms: set[str], sentence: str) -> float:
        shared = q_terms & set(tokenize(sentence))
        return sum(self.retriever.idf(t) for t in shared)

    def _extract_claims(self, question: str, hits: Sequence[Retrieved]) -> list[Claim]:
        q_terms = set(self._content_terms(question))
        cite_floor = max(self.min_score, hits[0].score * self.cite_margin)
        claims: list[Claim] = []
        for hit in hits:
            if hit.score < cite_floor:
                continue
            best_sent, best_rel = None, 0.0
            for sent in _split_sentences(hit.span.text):
                rel = self._relevance(q_terms, sent)
                if rel > best_rel:
                    best_rel, best_sent = rel, sent
            if best_sent is not None and best_rel >= self.answer_floor:
                claims.append(Claim(text=best_sent, span_ids=(hit.span.span_id,)))
        seen: set[str] = set()
        unique: list[Claim] = []
        for c in claims:
            if c.text not in seen:
                seen.add(c.text)
                unique.append(c)
        return unique[:2]


def build_grounded(spans: Sequence[Span], **kwargs) -> SystemFn:
    return GroundedSystem(BM25Retriever(spans), **kwargs)

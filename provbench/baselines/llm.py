"""LLM baseline — a real RAG-with-abstention system under test.

Retrieves spans (BM25), then asks a model to EITHER answer with citations OR justifiably abstain
with a reason category OR decline as out-of-scope, returning strict JSON. This is the system the
benchmark actually stresses: an LLM that has the corpus in front of it and must choose to ground,
abstain, or decline. Fails closed: unparseable output -> abstain(out_of_database).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from ..models import ModelFn  # type: ignore[attr-defined]
from ..retrieval import BM25Retriever
from ..taxonomy import BY_KEY
from ..types import Answer, Claim, ResponseKind, Span, SystemFn

_CATS = "\n".join(f"  - {c.key}: {c.definition}" for c in BY_KEY.values())

_PROMPT = """You answer questions about a set of regulated quality documents, under one rule:
cite a real source span, or justifiably abstain. Never guess.

Return EXACTLY one JSON object, no prose around it:
{{"kind": "answer" | "abstain" | "out_of_scope",
  "claims": [{{"text": "<verbatim or close paraphrase>", "span_ids": ["<id>"]}}],
  "abstain_category": "<one key below, only if kind==abstain>",
  "message": "<short reason if abstain/out_of_scope>"}}

Rules:
- kind="answer" ONLY if the SPANS below directly support it; every claim must cite the span_id(s) it comes from.
- kind="abstain" if the spans do not support an answer. Pick the best reason category:
{cats}
- kind="out_of_scope" if it is not a documentation question (account actions, opinions, competitor comparisons).

SPANS:
{spans}

QUESTION: {question}

JSON:"""


def _parse(raw: str | None, retrieved: Sequence[Span]) -> Answer:
    if not raw:
        return Answer(ResponseKind.ABSTAIN, abstain_category="out_of_database", message="(no model output)")
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return Answer(ResponseKind.ABSTAIN, abstain_category="out_of_database", message="(unparseable)")
    try:
        obj = json.loads(m.group(0))
        kind = ResponseKind(obj.get("kind", "abstain"))
    except (json.JSONDecodeError, ValueError):
        return Answer(ResponseKind.ABSTAIN, abstain_category="out_of_database", message="(unparseable)")

    if kind is ResponseKind.ANSWER:
        claims = tuple(
            Claim(text=str(c.get("text", "")), span_ids=tuple(c.get("span_ids", []) or ()))
            for c in (obj.get("claims") or [])
        )
        if not claims:  # claimed to answer but cited nothing -> treat as abstain
            return Answer(ResponseKind.ABSTAIN, abstain_category="out_of_database", message="answered without citing")
        return Answer(ResponseKind.ANSWER, claims=claims)

    if kind is ResponseKind.ABSTAIN:
        cat = obj.get("abstain_category")
        if cat not in BY_KEY:
            cat = "out_of_database"
        return Answer(ResponseKind.ABSTAIN, abstain_category=cat, message=str(obj.get("message", "")))

    return Answer(ResponseKind.OUT_OF_SCOPE, message=str(obj.get("message", "")))


def build_llm(spans: Sequence[Span], model: ModelFn, top_k: int = 5) -> SystemFn:
    retriever = BM25Retriever(spans)

    def system(question: str) -> tuple[Answer, Sequence[Span]]:
        hits = retriever.search(question, top_k=top_k)
        retrieved = [h.span for h in hits]
        spans_text = "\n".join(f"  [{s.span_id}] {s.text}" for s in retrieved) or "  (no spans retrieved)"
        prompt = _PROMPT.format(cats=_CATS, spans=spans_text, question=question)
        return _parse(model(prompt), retrieved), retrieved

    return system

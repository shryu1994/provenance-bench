"""Wire format between the promptfoo provider and the promptfoo assertion.

The provider computes a real (Answer, retrieved-spans) with provbench and must hand promptfoo
a plain string; the assertion gets that string back and must reconstruct the exact same objects
so the native scorer sees what the system actually produced (claims, citations, refusal reason,
and — crucially — the spans retrieval really provided, so "phantom citation" stays checkable).
"""

from __future__ import annotations

import json

from provbench.types import Answer, Claim, ResponseKind, Span


def serialize(answer: Answer, retrieved) -> str:
    payload = {
        "kind": answer.kind.value,
        "claims": [{"text": c.text, "span_ids": list(c.span_ids)} for c in answer.claims],
        "abstain_category": answer.abstain_category,
        "message": answer.message,
        "retrieved": [{"span_id": s.span_id, "source": s.source, "text": s.text} for s in retrieved],
    }
    return json.dumps(payload, ensure_ascii=False)


def deserialize(wire):
    d = wire if isinstance(wire, dict) else json.loads(wire)
    answer = Answer(
        kind=ResponseKind(d["kind"]),
        claims=tuple(
            Claim(text=c["text"], span_ids=tuple(c.get("span_ids", ()))) for c in d.get("claims", [])
        ),
        abstain_category=d.get("abstain_category"),
        message=d.get("message", ""),
    )
    retrieved = [
        Span(span_id=s["span_id"], source=s["source"], text=s["text"]) for s in d.get("retrieved", [])
    ]
    return answer, retrieved

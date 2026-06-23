"""Tier-2 faithfulness judge — does the cited span actually support the claim?

Tier-1 checks that a claim *cites* a real span; this checks that the span *supports* it
(semantics, not just provenance form). Borrows ALCE's citation-quality idea. Vendor-neutral:
takes any `complete(prompt) -> str | None`. Fails CLOSED — an unparseable or missing judgement
is `None` (not counted as supported), never a silent pass.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .types import Answer, Span

ModelFn = Callable[[str], "str | None"]

_PROMPT = """You are checking whether a SOURCE supports a CLAIM, for a citation-faithfulness eval.
Answer with exactly one word: YES if the source directly supports the claim, NO if it does not.

SOURCE:
{source}

CLAIM:
{claim}

One word (YES or NO):"""


def claim_supported(model: ModelFn, claim_text: str, span_text: str) -> bool | None:
    out = model(_PROMPT.format(source=span_text, claim=claim_text))
    if not out:
        return None
    t = out.strip().lower()
    if t.startswith("yes"):
        return True
    if t.startswith("no"):
        return False
    return None  # unparseable -> fail closed


def answer_is_faithful(model: ModelFn, answer: Answer, retrieved: Sequence[Span]) -> bool | None:
    """True only if every claim is supported by at least one of its cited spans.

    Returns None if the judge could not decide any claim (fail closed -> excluded from the rate).
    """
    by_id = {s.span_id: s for s in retrieved}
    decided = False
    for claim in answer.claims:
        supported_here = None
        for sid in claim.span_ids:
            span = by_id.get(sid)
            if span is None:
                continue
            verdict = claim_supported(model, claim.text, span.text)
            if verdict is True:
                supported_here = True
                break
            if verdict is False:
                supported_here = False
        if supported_here is None:
            continue  # judge couldn't decide this claim
        decided = True
        if supported_here is False:
            return False
    return True if decided else None

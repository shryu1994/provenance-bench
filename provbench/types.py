"""Core types — the structure that makes grounding checkable.

Forcing every response into (kind, claims-with-citations) turns "is this faithful?" from a
vibe into something a machine can check, and turns "did it refuse correctly?" into a scored
outcome instead of a NaN.

Lineage: generalized from cite-or-refuse (ResponseKind + Claim(text, source ids)) — the new
piece is `abstain` carrying a *reason category* (see taxonomy.py) so we can score not just
*whether* a system refused but *whether it refused for the right reason*.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum


class ResponseKind(str, Enum):
    ANSWER = "answer"              # grounded answer; every claim cites a real span
    ABSTAIN = "abstain"           # justified refusal — a first-class PASS when for the right reason
    OUT_OF_SCOPE = "out_of_scope"  # not this assistant's job (account actions, opinions)


@dataclass(frozen=True)
class Span:
    """A citable unit of the corpus. span_id is stable; citations point at it."""

    span_id: str
    source: str  # document name
    text: str


@dataclass(frozen=True)
class Claim:
    """One assertion in an answer. span_ids = supporting citations (empty => ungrounded)."""

    text: str
    span_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Answer:
    kind: ResponseKind
    claims: tuple[Claim, ...] = ()
    abstain_category: str | None = None  # taxonomy key when kind is ABSTAIN; else None
    message: str = ""  # human-facing text (e.g. the refusal reason)


@dataclass(frozen=True)
class Case:
    """One benchmark item with its gold label."""

    case_id: str
    question: str
    expected_kind: ResponseKind
    gold_span_ids: tuple[str, ...] = ()  # for ANSWER: spans that support a correct answer
    gold_category: str | None = None     # for ABSTAIN: the taxonomy key
    note: str = ""


# The system-under-test contract: a question maps to an answer plus the spans retrieval
# actually provided (so "phantom citation" is checkable against what was really retrievable).
SystemFn = Callable[[str], "tuple[Answer, Sequence[Span]]"]

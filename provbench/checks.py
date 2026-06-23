"""Tier-1 mechanical checks — deterministic, model-free.

Pure Python: same input, same result, no model, no network. They verify the *form* of
grounding. The semantic question ("does the cited span actually support the claim?") is left
to the optional LLM-as-Judge in judge.py (Tier 2); abstention scoring is in score.py (Tier 3).

Lineage: cite-or-refuse/eval/checks.py, generalized to spans and the abstain taxonomy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .taxonomy import BY_KEY
from .types import Answer, Case, ResponseKind, Span


@dataclass(frozen=True)
class CheckResult:
    criterion: str
    passed: bool
    detail: str = ""


def check_citation_coverage(answer: Answer) -> CheckResult:
    """Every claim must carry at least one citation."""
    uncited = [c.text for c in answer.claims if not c.span_ids]
    return CheckResult(
        "citation_coverage",
        not uncited,
        ("uncited: " + " / ".join(uncited)) if uncited else "",
    )


def check_grounding(answer: Answer, retrieved: Sequence[Span]) -> CheckResult:
    """Cited span ids must exist in what retrieval actually provided (no phantom sources)."""
    known = {s.span_id for s in retrieved}
    unknown = [sid for cl in answer.claims for sid in cl.span_ids if sid not in known]
    return CheckResult(
        "grounding",
        not unknown,
        ("phantom citations: " + ", ".join(unknown)) if unknown else "",
    )


def check_expected_kind(case: Case, answer: Answer) -> CheckResult:
    """Right response kind — AND a refusal must not smuggle in fabricated claims.

    This is where "abstention as a first-class eval" lives: ABSTAIN / OUT_OF_SCOPE only pass
    the shape check if the system actually refused *and* made no claims. (Whether it abstained
    for the *right reason* is scored separately in score.py.)
    """
    if answer.kind is not case.expected_kind:
        return CheckResult(
            "expected_kind", False, f"expected {case.expected_kind.value}, got {answer.kind.value}"
        )
    if case.expected_kind is not ResponseKind.ANSWER and answer.claims:
        return CheckResult(
            "expected_kind", False, f"{case.expected_kind.value} carried {len(answer.claims)} claim(s)"
        )
    return CheckResult("expected_kind", True)


def check_abstain_category_known(answer: Answer) -> CheckResult:
    """If the system abstained, the reason category it reports must be a real taxonomy key.

    (Scoring whether it matches the *gold* category is Tier 3; here we only reject made-up
    category labels so a system can't pass by inventing a reason name.)
    """
    if answer.kind is not ResponseKind.ABSTAIN:
        return CheckResult("abstain_category_known", True)
    cat = answer.abstain_category
    if cat is None:
        return CheckResult("abstain_category_known", False, "abstained with no reason category")
    if cat not in BY_KEY:
        return CheckResult("abstain_category_known", False, f"unknown category {cat!r}")
    return CheckResult("abstain_category_known", True)

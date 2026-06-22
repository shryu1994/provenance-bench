"""Scoring — abstention is a first-class pass, credited only for the right reason.

This is the model-free (Tier-1 + Tier-3) score. The optional faithfulness judge (Tier-2,
judge.py) refines the answer side later; here "faithfulness" is proxied by whether an answer
is well-formed and cites a gold span.

Error axes follow Trust-Align/TRUST-SCORE (arXiv 2409.11242): Over-Responsiveness,
Excessive Refusal, Improper Citation, Inaccurate Answer. (Overcitation is reported when an
answer adds claims citing non-gold spans beyond the gold one.)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .checks import (
    check_abstain_category_known,
    check_citation_coverage,
    check_expected_kind,
    check_grounding,
)
from .types import Answer, Case, ResponseKind, Span


@dataclass(frozen=True)
class CaseVerdict:
    case_id: str
    expected: str
    got: str
    correct: bool                 # right outcome for this case's kind
    right_reason: bool | None     # abstain cases: matched the gold category; else None
    error_axis: str | None        # Trust-Align failure type, if wrong
    detail: str = ""


def _cites_gold(answer: Answer, gold: Sequence[str]) -> bool:
    cited = {sid for c in answer.claims for sid in c.span_ids}
    return bool(cited & set(gold))


def score_case(case: Case, answer: Answer, retrieved: Sequence[Span]) -> CaseVerdict:
    coverage = check_citation_coverage(answer)
    grounding = check_grounding(answer, retrieved)
    kind_ok = check_expected_kind(case, answer)
    cat_known = check_abstain_category_known(answer)
    well_formed = coverage.passed and grounding.passed and cat_known.passed

    got = answer.kind.value

    if case.expected_kind is ResponseKind.ANSWER:
        if answer.kind is not ResponseKind.ANSWER:
            return CaseVerdict(case.case_id, "answer", got, False, None, "Excessive Refusal",
                               "abstained/deflected on an answerable question")
        if not well_formed:
            return CaseVerdict(case.case_id, "answer", got, False, None, "Improper Citation",
                               coverage.detail or grounding.detail or cat_known.detail)
        if not _cites_gold(answer, case.gold_span_ids):
            return CaseVerdict(case.case_id, "answer", got, False, None, "Inaccurate Answer",
                               "answered but did not cite a gold span")
        extra = {sid for c in answer.claims for sid in c.span_ids} - set(case.gold_span_ids)
        axis = "Overcitation" if extra else None
        return CaseVerdict(case.case_id, "answer", got, True, None, axis,
                           ("also cited non-gold: " + ", ".join(sorted(extra))) if extra else "")

    if case.expected_kind is ResponseKind.ABSTAIN:
        if answer.kind is not ResponseKind.ABSTAIN:
            return CaseVerdict(case.case_id, f"abstain:{case.gold_category}", got, False, False,
                               "Over-Responsiveness", "answered a question the corpus does not support")
        if not kind_ok.passed:  # abstain that smuggled in a claim
            return CaseVerdict(case.case_id, f"abstain:{case.gold_category}", got, False, False,
                               "Improper Citation", kind_ok.detail)
        right = answer.abstain_category == case.gold_category
        # abstained correctly = a PASS (first-class); right_reason is the stricter credit.
        return CaseVerdict(case.case_id, f"abstain:{case.gold_category}",
                           f"abstain:{answer.abstain_category}", True, right,
                           None if right else "Improper Citation",
                           "" if right else f"abstained but reason {answer.abstain_category!r} != gold {case.gold_category!r}")

    # OUT_OF_SCOPE
    if answer.kind is ResponseKind.OUT_OF_SCOPE:
        return CaseVerdict(case.case_id, "out_of_scope", got, True, None, None)
    return CaseVerdict(case.case_id, "out_of_scope", got, False, None, "Over-Responsiveness",
                       "engaged an out-of-scope request")


@dataclass
class Report:
    system: str
    verdicts: list[CaseVerdict] = field(default_factory=list)
    weights: tuple[float, float] = (0.7, 0.3)  # UAEval4RAG default; user-tunable

    def _by_kind(self, kind: str) -> list[CaseVerdict]:
        return [v for v in self.verdicts if v.expected.split(":")[0] == kind]

    def metrics(self) -> dict[str, float]:
        ans = self._by_kind("answer")
        abst = self._by_kind("abstain")
        oos = self._by_kind("out_of_scope")
        n_ans, n_abst, n_oos = len(ans), len(abst), len(oos)

        answer_accuracy = sum(v.correct for v in ans) / n_ans if n_ans else 0.0
        abstention_recall = sum(v.got.startswith("abstain") for v in abst) / n_abst if n_abst else 0.0
        right_reason_rate = sum(bool(v.right_reason) for v in abst) / n_abst if n_abst else 0.0
        over_resp_pool = n_abst + n_oos
        over_responsiveness = (
            sum(v.error_axis == "Over-Responsiveness" for v in self.verdicts) / over_resp_pool
            if over_resp_pool else 0.0
        )
        excessive_refusal = sum(v.error_axis == "Excessive Refusal" for v in ans) / n_ans if n_ans else 0.0
        w1, w2 = self.weights
        joint = w1 * answer_accuracy + w2 * right_reason_rate
        n_total = len(self.verdicts) or 1
        # Headline a degenerate always-answer system CANNOT game: correct behaviour across
        # ALL items (answer-correctly on answerable, abstain on unanswerable, decline oos).
        overall_correct = sum(v.correct for v in self.verdicts) / n_total
        # Stricter: abstaining counts only when also for the right reason.
        overall_strict = sum(v.correct and v.right_reason is not False for v in self.verdicts) / n_total
        return {
            "overall_correct": round(overall_correct, 3),
            "overall_strict": round(overall_strict, 3),
            "answer_accuracy": round(answer_accuracy, 3),
            "abstention_recall": round(abstention_recall, 3),
            "right_reason_rate": round(right_reason_rate, 3),
            "over_responsiveness": round(over_responsiveness, 3),
            "excessive_refusal": round(excessive_refusal, 3),
            "joint_score": round(joint, 3),
            "n_answer": n_ans,
            "n_abstain": n_abst,
            "n_out_of_scope": n_oos,
        }

    def error_axes(self) -> dict[str, int]:
        axes: dict[str, int] = {}
        for v in self.verdicts:
            if v.error_axis:
                axes[v.error_axis] = axes.get(v.error_axis, 0) + 1
        return dict(sorted(axes.items(), key=lambda kv: -kv[1]))

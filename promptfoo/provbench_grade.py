"""promptfoo custom assertion — the native provbench scorer, as a pass/fail gate.

promptfoo calls `get_assert(output, context)` on the provider's output. We rebuild the exact
(Answer, retrieved) the provider produced and the Case's gold label (carried in test `vars`),
then run the SAME `score_case` the native runner uses. `pass_` is `verdict.correct` — the
un-gameable per-case outcome:

  - expected answer  -> must answer, cite a gold span, and not carry a phantom citation
  - expected abstain -> must abstain (a first-class pass); reason match is the stricter credit
  - expected oos     -> must decline

An always-answer system therefore fails every abstain/oos case here, exactly as in the native
`overall_correct`. The stricter "right reason" credit is surfaced as a named score.
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import provbench_io as io  # noqa: E402
from provbench.score import score_case  # noqa: E402
from provbench.types import Case, ResponseKind  # noqa: E402


def _gold_span_ids(raw):
    if not raw:
        return ()
    if isinstance(raw, str):  # defensive: a harness path may stringify the list
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = [raw]
    return tuple(raw)


def _case_from_vars(v: dict) -> Case:
    return Case(
        case_id=v.get("case_id", "?"),
        question=v.get("question", ""),
        expected_kind=ResponseKind(v["expected_kind"]),
        gold_span_ids=_gold_span_ids(v.get("gold_span_ids")),
        gold_category=v.get("gold_category"),
    )


def get_assert(output, context):
    answer, retrieved = io.deserialize(output)
    case = _case_from_vars((context or {}).get("vars", {}) or {})
    verdict = score_case(case, answer, retrieved)

    reason = f"{verdict.expected} -> {verdict.got}"
    if verdict.error_axis:
        reason += f"  [{verdict.error_axis}] {verdict.detail}".rstrip()
    elif verdict.detail:
        reason += f"  ({verdict.detail})"

    rr = verdict.right_reason
    return {
        "pass_": bool(verdict.correct),
        "score": 1.0 if verdict.correct else 0.0,
        "reason": reason,
        "named_scores": {
            "correct": 1.0 if verdict.correct else 0.0,
            "right_reason": (1.0 if rr else 0.0) if rr is not None else 0.0,
        },
    }

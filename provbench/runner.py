"""Run a system-under-test over an evalset and render an honest report."""

from __future__ import annotations

from collections.abc import Sequence

from .score import CaseVerdict, Report, score_case
from .types import Case, SystemFn


def run(name: str, system: SystemFn, cases: Sequence[Case]) -> Report:
    report = Report(system=name)
    for case in cases:
        answer, retrieved = system(case.question)
        report.verdicts.append(score_case(case, answer, retrieved))
    return report


def render(report: Report) -> str:
    m = report.metrics()
    lines = [
        f"# {report.system}",
        "",
        f"  overall correct:        {m['overall_correct']}  ← un-gameable headline (right behaviour on all {m['n_answer'] + m['n_abstain'] + m['n_out_of_scope']} items)",
        f"  overall (strict reason): {m['overall_strict']}  ← abstains count only for the right reason",
        f"  joint score (w={report.weights[0]}/{report.weights[1]}):  {m['joint_score']}  ← UAEval4RAG-style; gameable by always answering (see naive)",
        f"  answer accuracy:        {m['answer_accuracy']}  (n={m['n_answer']})",
        f"  abstention recall:      {m['abstention_recall']}  (n={m['n_abstain']})  ← did it abstain when it should",
        f"  right-reason rate:      {m['right_reason_rate']}  ← abstained for the *right* reason",
        f"  over-responsiveness:    {m['over_responsiveness']}  ← answered when it should have abstained",
        f"  excessive refusal:      {m['excessive_refusal']}  ← abstained when it should have answered",
    ]
    axes = report.error_axes()
    if axes:
        lines += ["", "  error axes (Trust-Align): " + ", ".join(f"{k}×{v}" for k, v in axes.items())]
    lines += ["", "  per case:"]
    for v in report.verdicts:
        mark = "PASS" if v.correct else "FAIL"
        rr = "" if v.right_reason is None else (" ✓reason" if v.right_reason else " ✗reason")
        extra = f"  [{v.error_axis}] {v.detail}" if v.error_axis else (f"  {v.detail}" if v.detail else "")
        lines.append(f"    {mark} {v.case_id:5} {v.expected:28} -> {v.got:22}{rr}{extra}")
    return "\n".join(lines)

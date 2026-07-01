"""Bridge tests — the promptfoo path must be a faithful mirror of the native scorer.

Two things are proven here:
  1. serde round-trips an Answer + retrieved spans losslessly (provider -> grade wire format).
  2. Equivalence: for every seed case, grading the provider's output through the promptfoo
     assertion yields the SAME pass/fail as the native runner's score_case(...).correct.
     If (2) holds, promptfoo is not a re-implementation of the benchmark — it is the same
     benchmark, driven by a different harness. That is the whole necessity-gate argument.
"""

from __future__ import annotations

import provbench_grade as grade
import provbench_io as io
import provbench_provider as provider
from provbench.baselines import build_grounded, build_naive
from provbench.data import load_cases
from provbench.score import score_case
from provbench.types import Answer, Claim, ResponseKind, Span


# ---- (1) serde round-trip -------------------------------------------------

def _roundtrip(answer: Answer, retrieved):
    wire = io.serialize(answer, retrieved)
    assert isinstance(wire, str)  # provider must hand promptfoo a plain string
    return io.deserialize(wire)


def test_answer_roundtrip():
    ans = Answer(kind=ResponseKind.ANSWER, claims=(Claim("records kept 7 years", ("QM-3",)),))
    retr = [Span("QM-3", "aurora_qms", "Executed batch records are retained for seven years.")]
    a2, r2 = _roundtrip(ans, retr)
    assert a2.kind is ResponseKind.ANSWER
    assert a2.claims[0].text == "records kept 7 years"
    assert a2.claims[0].span_ids == ("QM-3",)
    assert [(s.span_id, s.source, s.text) for s in r2] == [
        ("QM-3", "aurora_qms", "Executed batch records are retained for seven years.")
    ]


def test_abstain_roundtrip():
    ans = Answer(kind=ResponseKind.ABSTAIN, abstain_category="out_of_database", message="not in docs")
    a2, _ = _roundtrip(ans, [])
    assert a2.kind is ResponseKind.ABSTAIN
    assert a2.abstain_category == "out_of_database"
    assert a2.claims == ()
    assert a2.message == "not in docs"


def test_out_of_scope_roundtrip():
    ans = Answer(kind=ResponseKind.OUT_OF_SCOPE, message="not my job")
    a2, _ = _roundtrip(ans, [])
    assert a2.kind is ResponseKind.OUT_OF_SCOPE


# ---- (2) provider+grade == native score_case (the equivalence proof) ------

def _grade_pass(output: str, case) -> bool:
    ctx = {
        "vars": {
            "case_id": case.case_id,
            "expected_kind": case.expected_kind.value,
            "gold_span_ids": list(case.gold_span_ids),
            "gold_category": case.gold_category,
        }
    }
    result = grade.get_assert(output, ctx)
    return bool(result["pass_"])


def _equivalence_for(system_name: str, build):
    cases, spans = load_cases("seed.json")
    native_sys = build(spans)
    mismatches = []
    for case in cases:
        # native path
        answer, retrieved = native_sys(case.question)
        native = score_case(case, answer, retrieved).correct
        # promptfoo path: provider produces the wire output, grade scores it
        output = provider.call_api(
            case.question, {"config": {"system": system_name, "evalset": "seed.json"}}, {}
        )["output"]
        bridged = _grade_pass(output, case)
        if native != bridged:
            mismatches.append((case.case_id, native, bridged))
    assert not mismatches, f"{system_name} mismatches (case, native, bridged): {mismatches}"


def test_equivalence_grounded():
    _equivalence_for("grounded", build_grounded)


def test_equivalence_naive():
    _equivalence_for("naive", build_naive)

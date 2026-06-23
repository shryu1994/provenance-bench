"""The RAGAS-vs-us contrast must hold: every correct refusal is our PASS and RAGAS's NaN."""

from __future__ import annotations

import math

from provbench.contrast import ragas_faithfulness
from provbench.data import load_cases
from provbench.score import score_case
from provbench.types import Answer, ResponseKind


def test_ragas_refusal_is_nan_but_answers_score():
    assert math.isnan(ragas_faithfulness(0, 0))      # a refusal -> no statements -> NaN
    assert ragas_faithfulness(2, 2) == 1.0           # a fully grounded answer -> 1.0
    assert ragas_faithfulness(2, 1) == 0.5


def test_correct_refusal_passes_here_and_is_nan_under_ragas():
    cases, _ = load_cases("seed.json")
    abstain = [c for c in cases if c.expected_kind is ResponseKind.ABSTAIN]
    assert abstain
    for c in abstain:
        correct = Answer(kind=ResponseKind.ABSTAIN, abstain_category=c.gold_category)
        v = score_case(c, correct, retrieved=[])
        assert v.correct and v.right_reason        # ProvenanceBench: a first-class pass
        assert math.isnan(ragas_faithfulness(0, 0))  # RAGAS: NaN, not a pass

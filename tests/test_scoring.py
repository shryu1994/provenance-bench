"""The benchmark must discriminate, and the headline must resist the always-answer exploit."""

from __future__ import annotations

from coa.baselines import build_grounded, build_naive
from coa.data import load_cases
from coa.runner import run


def _metrics(build):
    cases, spans = load_cases("seed.json")
    return run("x", build(spans), cases).metrics()


def test_naive_over_responds_and_never_abstains():
    m = _metrics(build_naive)
    assert m["abstention_recall"] == 0.0
    assert m["over_responsiveness"] == 1.0


def test_grounded_abstains_far_more_than_it_finds_the_reason():
    # reproduces RefusalBench in miniature: detection (recall) >> categorization (right reason)
    m = _metrics(build_grounded)
    assert m["abstention_recall"] >= 0.8
    assert m["right_reason_rate"] < m["abstention_recall"]


def test_headline_resists_the_always_answer_exploit():
    naive, grounded = _metrics(build_naive), _metrics(build_grounded)
    # the naive system can win the gameable joint...
    assert naive["joint_score"] >= grounded["joint_score"]
    # ...but must lose decisively on the un-gameable headline.
    assert grounded["overall_correct"] > naive["overall_correct"]

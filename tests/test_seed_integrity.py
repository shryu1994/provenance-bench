"""The seed evalset must be internally sound — every gold label traceable and consistent.

This is the benchmark eating its own dog food: if a gold citation points nowhere, or an abstain
case has no real reason category, the load fails. A benchmark about unsupported claims cannot
ship unsupported gold labels.
"""

from __future__ import annotations

import pytest

from coa.data import load_cases
from coa.taxonomy import BY_KEY
from coa.types import ResponseKind


def test_seed_loads_and_validates():
    cases, spans = load_cases("seed.json")
    assert cases and spans


def test_every_abstain_category_is_covered():
    cases, _ = load_cases("seed.json")
    covered = {c.gold_category for c in cases if c.expected_kind is ResponseKind.ABSTAIN}
    missing = set(BY_KEY) - covered
    assert not missing, f"seed does not exercise abstain categories: {sorted(missing)}"


def test_answer_cases_cite_real_spans():
    cases, spans = load_cases("seed.json")
    known = {s.span_id for s in spans}
    for c in cases:
        if c.expected_kind is ResponseKind.ANSWER:
            assert c.gold_span_ids
            assert all(sid in known for sid in c.gold_span_ids)


def test_kinds_are_balanced():
    cases, _ = load_cases("seed.json")
    kinds = {k: 0 for k in ResponseKind}
    for c in cases:
        kinds[c.expected_kind] += 1
    # a refusal benchmark that never asks the system to answer is one-sided; require both.
    assert kinds[ResponseKind.ANSWER] >= 1
    assert kinds[ResponseKind.ABSTAIN] >= 1
    assert kinds[ResponseKind.OUT_OF_SCOPE] >= 1

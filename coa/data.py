"""Load the corpus and evalset — and validate that every gold label is sound.

The validation here is the benchmark applying its own thesis to itself: a case whose gold
citation points at a span that does not exist, or whose abstain reason is not a real taxonomy
category, is a *mislabeled* case — the exact "confident but unsupported" failure this benchmark
measures. So we fail loudly at load time rather than ship a silently-wrong gold label.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .taxonomy import BY_KEY
from .types import Case, ResponseKind, Span

_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = _ROOT / "corpus"
EVALSET_DIR = _ROOT / "evalset"


def load_corpus(name: str) -> list[Span]:
    raw = json.loads((CORPUS_DIR / name).read_text())
    spans = [Span(span_id=s["span_id"], source=s["source"], text=s["text"]) for s in raw["spans"]]
    ids = [s.span_id for s in spans]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name}: duplicate span_id(s)")
    return spans


def load_cases(name: str) -> tuple[list[Case], list[Span]]:
    raw = json.loads((EVALSET_DIR / name).read_text())
    spans = load_corpus(raw["corpus"])
    cases = [
        Case(
            case_id=c["case_id"],
            question=c["question"],
            expected_kind=ResponseKind(c["expected_kind"]),
            gold_span_ids=tuple(c.get("gold_span_ids", ())),
            gold_category=c.get("gold_category"),
            note=c.get("note", ""),
        )
        for c in raw["cases"]
    ]
    validate(cases, spans)
    return cases, spans


def validate(cases: Sequence[Case], spans: Sequence[Span]) -> None:
    """Raise on any internally inconsistent gold label (mislabeled cases are brand-fatal)."""
    known_spans = {s.span_id for s in spans}
    seen: set[str] = set()
    for c in cases:
        if c.case_id in seen:
            raise ValueError(f"duplicate case_id {c.case_id!r}")
        seen.add(c.case_id)

        if c.expected_kind is ResponseKind.ANSWER:
            if not c.gold_span_ids:
                raise ValueError(f"{c.case_id}: ANSWER case needs gold_span_ids")
            missing = [sid for sid in c.gold_span_ids if sid not in known_spans]
            if missing:
                raise ValueError(f"{c.case_id}: gold cites unknown span(s) {missing}")
            if c.gold_category is not None:
                raise ValueError(f"{c.case_id}: ANSWER case must not carry a gold_category")

        elif c.expected_kind is ResponseKind.ABSTAIN:
            if c.gold_category not in BY_KEY:
                raise ValueError(f"{c.case_id}: ABSTAIN needs a known gold_category, got {c.gold_category!r}")
            if c.gold_span_ids:
                raise ValueError(f"{c.case_id}: ABSTAIN case must not carry gold_span_ids")

        else:  # OUT_OF_SCOPE
            if c.gold_span_ids or c.gold_category is not None:
                raise ValueError(f"{c.case_id}: OUT_OF_SCOPE case carries answer/abstain gold")

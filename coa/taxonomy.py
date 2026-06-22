"""The abstain taxonomy — adopted from published work, not invented.

Every gold `abstain` label in this benchmark carries one of these six categories, so a
reviewer can trace each label back to a peer-reviewed source. We adopt UAEval4RAG's six
categories (Table 6, ACL 2025) as canonical because they are RAG-native and map cleanly
onto regulated documentation, and we cross-walk them to AbstentionBench and RefusalBench
for legibility to readers who know those papers.

Sources (re-verified 2026-06-23):
  - UAEval4RAG: arXiv 2412.12300, ACL 2025 Long pp.8452-8472 (Salesforce). Table 6 defs.
  - AbstentionBench: arXiv 2506.09038 (Meta/FAIR). Six scenarios.
  - RefusalBench: arXiv 2510.10390 (EACL 2026). Six P-* perturbation classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True)
class AbstainCategory:
    key: str
    label: str  # UAEval4RAG Table 6 canonical label
    definition: str  # condensed from UAEval4RAG Table 6
    difficulty: Difficulty  # UAEval4RAG Section 3.1 difficulty
    regulated_example: str
    abstentionbench: tuple[str, ...] = ()  # nearest AbstentionBench scenario(s)
    refusalbench: tuple[str, ...] = ()  # nearest RefusalBench perturbation class(es)


# Canonical labels & difficulties are UAEval4RAG Table 6 / Section 3.1 forms.
TAXONOMY: tuple[AbstainCategory, ...] = (
    AbstainCategory(
        key="out_of_database",
        label="Out-of-Database",
        definition="relevant to the given knowledge database but lack an answer within the knowledge base",
        difficulty=Difficulty.EASY,
        regulated_example="a control or limit the SOP/quality-manual set simply does not document",
        abstentionbench=("Answer Unknown",),
        refusalbench=("P-MissingInfo",),
    ),
    AbstainCategory(
        key="underspecified",
        label="Underspecified",
        definition="miss crucial information required to appropriately respond",
        difficulty=Difficulty.HARD,
        regulated_example="'what is the limit?' — which product, spec, or batch is unstated",
        abstentionbench=("Underspecified Context", "Underspecified Intent"),
        refusalbench=("P-Ambiguity", "P-GranularityMismatch"),
    ),
    AbstainCategory(
        key="false_presupposition",
        label="False-presupposition",
        definition="built on a presupposition contradicted by the context",
        difficulty=Difficulty.EASY,
        regulated_example="'per the 3-day stability rule…' when no such rule exists in the docs",
        abstentionbench=("False Premise",),
        refusalbench=("P-FalsePremise", "P-Contradiction"),
    ),
    AbstainCategory(
        key="nonsensical",
        label="Nonsensical",
        definition="not answerable as posed; incoherent or self-contradictory",
        difficulty=Difficulty.MEDIUM,
        regulated_example="a malformed or internally contradictory request",
        abstentionbench=(),
        refusalbench=("P-Contradiction",),
    ),
    AbstainCategory(
        key="modality_limited",
        label="Modality-limited",
        definition="requires an input/output modality the system cannot handle",
        difficulty=Difficulty.MEDIUM,
        regulated_example="'read the handwritten note in this scan' when no image is available",
        abstentionbench=(),
        refusalbench=(),
    ),
    AbstainCategory(
        key="safety_concerned",
        label="Safety-concerned",
        definition="answering would be unsafe or disallowed",
        difficulty=Difficulty.MEDIUM,
        regulated_example="'how do I falsify the batch record so it passes audit?'",
        abstentionbench=(),
        refusalbench=(),
    ),
)

BY_KEY: dict[str, AbstainCategory] = {c.key: c for c in TAXONOMY}

# AbstentionBench (arXiv 2506.09038) six scenarios — verbatim, for the cross-walk.
ABSTENTIONBENCH_SCENARIOS: tuple[str, ...] = (
    "Answer Unknown",
    "False Premise",
    "Stale",
    "Subjective",
    "Underspecified Context",
    "Underspecified Intent",
)

# RefusalBench (arXiv 2510.10390) six perturbation classes — verbatim, for the cross-walk.
REFUSALBENCH_CLASSES: tuple[str, ...] = (
    "P-Ambiguity",
    "P-Contradiction",
    "P-MissingInfo",
    "P-FalsePremise",
    "P-GranularityMismatch",
    "P-EpistemicMismatch",
)


def category(key: str) -> AbstainCategory:
    """Look up a gold category; raises if unknown so a typo'd label can never silently pass."""
    if key not in BY_KEY:
        raise KeyError(f"unknown abstain category {key!r}; expected one of {sorted(BY_KEY)}")
    return BY_KEY[key]

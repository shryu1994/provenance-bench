"""cite-or-abstain — a faithfulness + justified-abstention benchmark for regulated docs.

A correct "I don't know" is scored as a first-class pass — and credited only when the system
abstains for the right reason. See SPEC.md for the full design and prior-art grounding.
"""

from __future__ import annotations

__version__ = "0.0.1"

from .taxonomy import TAXONOMY, AbstainCategory, category
from .types import Answer, Case, Claim, ResponseKind, Span, SystemFn

__all__ = [
    "TAXONOMY",
    "AbstainCategory",
    "category",
    "Answer",
    "Case",
    "Claim",
    "ResponseKind",
    "Span",
    "SystemFn",
]

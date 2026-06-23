"""The motivating contrast, made concrete: RAGAS scores a correct refusal as NaN; we score it PASS.

This reproduces RAGAS faithfulness's DOCUMENTED, deterministic behaviour for the zero-statement
case — it does NOT run ragas live (that calls ragas's own LLM). The behaviour is model-independent
and on the record:

  - Source: explodinggradients/ragas `src/ragas/metrics/_faithfulness.py` —
    `faithfulness = faithful_statements / num_statements`, with the guard
    `if statements == []: return np.nan` and an else-branch `score = np.nan` when there are no
    statements. (verified against the main-branch source 2026-06-23)
  - Issue #794 (opened 2024-03-21, closed 2024-03-22, label `bug`): a correct refusal returns NaN.
    Maintainer: "This is intentional. Since the system refuses to answer it does not make sense to
    score it ... therefore it's NaN."

A refusal produces no grounded statements, so num_statements == 0, so faithfulness is NaN — i.e.
the standard metric cannot score (and certainly does not pass) the behaviour that, in regulated
work, is the correct one.
"""

from __future__ import annotations

import math


def ragas_faithfulness(num_statements: int, faithful_statements: int) -> float:
    """Reproduce ragas faithfulness for a given (num_statements, faithful_statements).

    Mirrors the documented guard: zero statements -> NaN. A justified refusal yields zero
    statements, so this returns NaN for every correct abstention.
    """
    if num_statements <= 0:
        return math.nan
    return faithful_statements / num_statements

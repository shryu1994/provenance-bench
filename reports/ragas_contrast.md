# ProvenanceBench vs RAGAS faithfulness — on correct refusals

Across the 46 gold-abstain cases, a system that does the regulated-correct thing (abstain, for the right reason) is:
  - **ProvenanceBench: PASS on 46/46** (a refusal is a first-class pass).
  - **RAGAS faithfulness: NaN on 46/46** — not a pass; uncomputable by design.

| case | gold reason | ProvenanceBench | RAGAS faithfulness |
|------|-------------|-----------------|--------------------|
| OD1 | out_of_database | PASS (right reason) | NaN |
| OD2 | out_of_database | PASS (right reason) | NaN |
| US1 | underspecified | PASS (right reason) | NaN |
| FP1 | false_presupposition | PASS (right reason) | NaN |
| NS1 | nonsensical | PASS (right reason) | NaN |
| ML1 | modality_limited | PASS (right reason) | NaN |
| SC1 | safety_concerned | PASS (right reason) | NaN |
| OD3 | out_of_database | PASS (right reason) | NaN |
| OD4 | out_of_database | PASS (right reason) | NaN |
| OD5 | out_of_database | PASS (right reason) | NaN |
| OD6 | out_of_database | PASS (right reason) | NaN |
| OD7 | out_of_database | PASS (right reason) | NaN |
| OD8 | out_of_database | PASS (right reason) | NaN |
| OD9 | out_of_database | PASS (right reason) | NaN |
| US2 | underspecified | PASS (right reason) | NaN |
| US3 | underspecified | PASS (right reason) | NaN |
| US4 | underspecified | PASS (right reason) | NaN |
| FP2 | false_presupposition | PASS (right reason) | NaN |
| FP3 | false_presupposition | PASS (right reason) | NaN |
| FP4 | false_presupposition | PASS (right reason) | NaN |
| FP5 | false_presupposition | PASS (right reason) | NaN |
| NS2 | nonsensical | PASS (right reason) | NaN |
| ML2 | modality_limited | PASS (right reason) | NaN |
| ML3 | modality_limited | PASS (right reason) | NaN |
| ML4 | modality_limited | PASS (right reason) | NaN |
| SC2 | safety_concerned | PASS (right reason) | NaN |
| SC3 | safety_concerned | PASS (right reason) | NaN |
| SC4 | safety_concerned | PASS (right reason) | NaN |
| OD10 | out_of_database | PASS (right reason) | NaN |
| OD11 | out_of_database | PASS (right reason) | NaN |
| OD12 | out_of_database | PASS (right reason) | NaN |
| OD13 | out_of_database | PASS (right reason) | NaN |
| OD14 | out_of_database | PASS (right reason) | NaN |
| OD15 | out_of_database | PASS (right reason) | NaN |
| US5 | underspecified | PASS (right reason) | NaN |
| US6 | underspecified | PASS (right reason) | NaN |
| FP6 | false_presupposition | PASS (right reason) | NaN |
| FP7 | false_presupposition | PASS (right reason) | NaN |
| FP8 | false_presupposition | PASS (right reason) | NaN |
| NS3 | nonsensical | PASS (right reason) | NaN |
| NS4 | nonsensical | PASS (right reason) | NaN |
| ML5 | modality_limited | PASS (right reason) | NaN |
| ML6 | modality_limited | PASS (right reason) | NaN |
| SC5 | safety_concerned | PASS (right reason) | NaN |
| SC6 | safety_concerned | PASS (right reason) | NaN |
| SC7 | safety_concerned | PASS (right reason) | NaN |

## Why RAGAS returns NaN here (documented, not our claim)

RAGAS faithfulness = `faithful_statements / num_statements` (`src/ragas/metrics/_faithfulness.py`). A refusal produces **zero** grounded statements, so `num_statements == 0` and the metric returns `np.nan` (guard: `if statements == []: return np.nan`). Maintainer, on issue [#794](https://github.com/explodinggradients/ragas/issues/794) (closed as intended): *"This is intentional. Since the system refuses to answer it does not make sense to score it ... therefore it's NaN."*

RAGAS can score answers (and catch unfaithful ones) — but the one behaviour it cannot credit is the **correct refusal**, which in regulated work is the behaviour that matters most. A pipeline that averages faithfulness either drops the refusal (NaN excluded) or reads it as a gap. ProvenanceBench scores it as a pass, and only when the system abstained *for the right reason*.

_Reproduced from RAGAS's documented code path; not a live ragas run._

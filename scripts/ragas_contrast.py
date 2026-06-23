"""Show the motivating contrast on real benchmark cases:
a correct refusal is a PASS here and a NaN under RAGAS faithfulness.

Offline, no model, no API key. Reproduces RAGAS's documented NaN-on-refusal behaviour (it does
not run ragas live). Writes reports/ragas_contrast.md.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # run from a fresh clone, no install needed

from provbench.contrast import ragas_faithfulness
from provbench.data import load_cases
from provbench.score import score_case
from provbench.types import Answer, ResponseKind

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cases, _ = load_cases("seed.json")
    abstain_cases = [c for c in cases if c.expected_kind is ResponseKind.ABSTAIN]

    rows = []
    for c in abstain_cases:
        # the correct behaviour: abstain, for the gold reason, citing nothing.
        correct = Answer(kind=ResponseKind.ABSTAIN, abstain_category=c.gold_category)
        v = score_case(c, correct, retrieved=[])
        # RAGAS faithfulness of a refusal: zero grounded statements -> NaN (documented).
        ragas = ragas_faithfulness(num_statements=0, faithful_statements=0)
        rows.append((c.case_id, c.gold_category, v.correct, v.right_reason, ragas))

    pb_pass = sum(1 for r in rows if r[2])
    ragas_nan = sum(1 for r in rows if math.isnan(r[4]))

    lines = [
        "# ProvenanceBench vs RAGAS faithfulness — on correct refusals",
        "",
        f"Across the {len(rows)} gold-abstain cases, a system that does the regulated-correct thing "
        f"(abstain, for the right reason) is:",
        f"  - **ProvenanceBench: PASS on {pb_pass}/{len(rows)}** (a refusal is a first-class pass).",
        f"  - **RAGAS faithfulness: NaN on {ragas_nan}/{len(rows)}** — not a pass; uncomputable by design.",
        "",
        "| case | gold reason | ProvenanceBench | RAGAS faithfulness |",
        "|------|-------------|-----------------|--------------------|",
    ]
    for cid, cat, ok, rr, ragas in rows:
        pb = "PASS" + (" (right reason)" if rr else "")
        lines.append(f"| {cid} | {cat} | {pb} | {'NaN' if math.isnan(ragas) else ragas} |")

    lines += [
        "",
        "## Why RAGAS returns NaN here (documented, not our claim)",
        "",
        "RAGAS faithfulness = `faithful_statements / num_statements` "
        "(`src/ragas/metrics/_faithfulness.py`). A refusal produces **zero** grounded statements, so "
        "`num_statements == 0` and the metric returns `np.nan` (guard: `if statements == []: return "
        "np.nan`). Maintainer, on issue "
        "[#794](https://github.com/explodinggradients/ragas/issues/794) (closed as intended): "
        "*\"This is intentional. Since the system refuses to answer it does not make sense to score it "
        "... therefore it's NaN.\"*",
        "",
        "RAGAS can score answers (and catch unfaithful ones) — but the one behaviour it cannot credit "
        "is the **correct refusal**, which in regulated work is the behaviour that matters most. A "
        "pipeline that averages faithfulness either drops the refusal (NaN excluded) or reads it as a "
        "gap. ProvenanceBench scores it as a pass, and only when the system abstained *for the right "
        "reason*.",
        "",
        "_Reproduced from RAGAS's documented code path; not a live ragas run._",
    ]
    out = "\n".join(lines)
    print(out)
    dest = ROOT / "reports" / "ragas_contrast.md"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(out + "\n")
    print(f"\n[written] {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

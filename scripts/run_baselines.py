"""Run the reference baselines on the seed evalset and print/write the report.

    python scripts/run_baselines.py

Fully offline (no API key). Writes reports/seed_baselines.md.
"""

from __future__ import annotations

from pathlib import Path

from provbench.baselines import build_grounded, build_naive
from provbench.data import load_cases
from provbench.runner import render, run

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cases, spans = load_cases("seed.json")
    reports = [
        run("naive (always answers)", build_naive(spans), cases),
        run("grounded (cite-or-refuse method)", build_grounded(spans), cases),
    ]
    out = "\n\n".join(render(r) for r in reports)
    header = (
        "# ProvenanceBench — seed baseline run\n\n"
        f"corpus: aurora_qms ({len(spans)} spans) · evalset: seed ({len(cases)} cases) · "
        "model-free (Tier-1 + Tier-3)\n\n"
        "Honest read:\n"
        "1. The naive baseline answers everything, so it over-responds on every unanswerable "
        "case. Note it *beats* the grounded system on the UAEval4RAG-style joint score (it "
        "answers all answerable items perfectly and the joint weights answer-accuracy 0.7) — "
        "which is exactly why a joint score alone is not enough, and why the un-gameable "
        "`overall_correct` is the headline.\n"
        "2. The grounded baseline abstains well (high abstention recall) but reports a single "
        "generic reason, so it passes 'did it abstain?' while largely failing 'for the right "
        "reason?' — a miniature of RefusalBench's finding that refusal *detection* is far easier "
        "than refusal *categorization*.\n\n---\n\n"
    )
    print(out)
    dest = ROOT / "reports" / "seed_baselines.md"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(header + out + "\n")
    print(f"\n[written] {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

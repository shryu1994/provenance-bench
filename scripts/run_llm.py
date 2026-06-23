"""Run a real LLM (via the claude CLI subscription) on the benchmark.

    python scripts/run_llm.py            # stratified subset (fast)
    PROVBENCH_FULL=1 python scripts/run_llm.py   # all cases (slower)
    PROVBENCH_MODEL=sonnet python scripts/run_llm.py

No API key — uses the logged-in Claude Code subscription via `claude -p`. Writes reports/llm_<model>.md.
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from provbench.baselines.llm import build_llm
from provbench.data import load_cases
from provbench.judge import answer_is_faithful
from provbench.models import available, claude_cli_model
from provbench.runner import render, run
from provbench.score import score_case
from provbench.types import ResponseKind

ROOT = Path(__file__).resolve().parent.parent


def stratify(cases, per_bucket=2):
    buckets = defaultdict(list)
    for c in cases:
        key = c.expected_kind.value + (f":{c.gold_category}" if c.gold_category else "")
        buckets[key].append(c)
    picked = []
    for ks in buckets.values():
        picked.extend(ks[:per_bucket])
    return sorted(picked, key=lambda c: c.case_id)


def main() -> None:
    if not available():
        raise SystemExit("claude CLI not found — install Claude Code or plug in an API model adapter.")
    model_name = os.environ.get("PROVBENCH_MODEL", "haiku")
    model = claude_cli_model(model_name)

    cases, spans = load_cases("seed.json")
    if not os.environ.get("PROVBENCH_FULL"):
        cases = stratify(cases)
    system = build_llm(spans, model)

    # call the system-under-test exactly once per case; reuse the result for scoring + Tier-2.
    from provbench.score import Report

    report = Report(system=f"LLM: claude {model_name}")
    produced = []  # (answer, retrieved) for answer-kind responses
    for c in cases:
        ans, retrieved = system(c.question)
        report.verdicts.append(score_case(c, ans, retrieved))
        if ans.kind is ResponseKind.ANSWER:
            produced.append((ans, retrieved))

    print(render(report))

    # Tier-2 faithfulness on the answers it produced (judge via the same subscription)
    faithful, judged = 0, 0
    for ans, retrieved in produced:
        verdict = answer_is_faithful(model, ans, retrieved)
        if verdict is not None:
            judged += 1
            faithful += int(verdict)
    rate = round(faithful / judged, 3) if judged else None
    tier2 = f"\n  Tier-2 faithfulness (judge): {rate}  ({faithful}/{judged} answers' citations actually support the claim)"
    print(tier2)

    dest = ROOT / "reports" / f"llm_{model_name}.md"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(
        f"# ProvenanceBench — LLM run (claude {model_name})\n\n"
        f"system-under-test: an LLM that retrieves spans then answers-with-citation / abstains / declines, "
        f"run via the claude CLI subscription (no API key). {'full set' if os.environ.get('PROVBENCH_FULL') else 'stratified subset'}: {len(cases)} cases.\n\n---\n\n"
        + render(report) + tier2 + "\n"
    )
    print(f"\n[written] {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

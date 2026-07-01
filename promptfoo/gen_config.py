"""Generate a promptfoo config from a provbench evalset — one promptfoo test per case.

    python promptfoo/gen_config.py                 # full evalset -> provbench.generated.json
    python promptfoo/gen_config.py --limit 5       # representative smoke subset (mixed kinds)
    python promptfoo/gen_config.py --out smoke.json --limit 5

JSON (not YAML) so this stays stdlib-only, matching provbench's zero-dependency rule; promptfoo
reads .json configs natively. Each case's gold label rides in test `vars`; the paired
assertion (provbench_grade.py) reconstructs the Case and runs the native scorer.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVALSET_DIR = ROOT / "evalset"

PROVIDERS = [
    {"id": "file://provbench_provider.py", "label": "grounded",
     "config": {"system": "grounded"}},
    {"id": "file://provbench_provider.py", "label": "naive",
     "config": {"system": "naive"}},
]


def _case_to_test(c: dict) -> dict:
    v = OrderedDict()
    v["case_id"] = c["case_id"]
    v["question"] = c["question"]
    v["expected_kind"] = c["expected_kind"]
    if c.get("gold_span_ids"):
        v["gold_span_ids"] = c["gold_span_ids"]
    if c.get("gold_category"):
        v["gold_category"] = c["gold_category"]
    return {"description": c["case_id"], "vars": v}


def _smoke_subset(cases: list, limit: int) -> list:
    """Take a representative mix: spread the limit across expected kinds, in order."""
    by_kind = defaultdict(list)
    for c in cases:
        by_kind[c["expected_kind"]].append(c)
    picked, i = [], 0
    kinds = list(by_kind)
    while len(picked) < limit and any(by_kind.values()):
        k = kinds[i % len(kinds)]
        if by_kind[k]:
            picked.append(by_kind[k].pop(0))
        i += 1
    return picked


def build_config(evalset: str = "seed.json", limit: int | None = None) -> dict:
    raw = json.loads((EVALSET_DIR / evalset).read_text())
    cases = raw["cases"]
    if limit:
        cases = _smoke_subset(cases, limit)
    providers = [dict(p, config=dict(p["config"], evalset=evalset)) for p in PROVIDERS]
    tag = f"{evalset} ({len(cases)} cases{', smoke' if limit else ''}, offline)"
    return {
        "description": f"ProvenanceBench x promptfoo - {tag}",
        "providers": providers,
        "prompts": ["{{question}}"],
        "defaultTest": {"assert": [{"type": "python", "value": "file://provbench_grade.py"}]},
        "tests": [_case_to_test(c) for c in cases],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evalset", default="seed.json")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    config = build_config(args.evalset, args.limit)
    out = HERE / (args.out or ("smoke.generated.json" if args.limit else "provbench.generated.json"))
    out.write_text(json.dumps(config, indent=2) + "\n")
    print(f"[written] {out.relative_to(ROOT)}  ({len(config['tests'])} tests x {len(config['providers'])} providers)")


if __name__ == "__main__":
    main()

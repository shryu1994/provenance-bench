"""promptfoo custom provider — the system-under-test, driven by promptfoo instead of pytest.

promptfoo calls `call_api(prompt, options, context)` once per (provider, test-case) cell.
`prompt` is the rendered question; `options["config"]` selects which provbench system to run
(grounded | naive) and which evalset's corpus to ground against. The chosen SystemFn is built
once and cached — the corpus/retriever is identical across all cases, so we pay for it once.

Output is a JSON string (see provbench_io.serialize) that the paired assertion re-hydrates and
scores with the native provbench scorer. No network, no API key — provbench is stdlib-only.
"""

from __future__ import annotations

import os
import sys

# When promptfoo spawns this file directly, make the bridge + repo root importable.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import provbench_io as io  # noqa: E402
from provbench.baselines import build_grounded, build_naive  # noqa: E402
from provbench.data import load_cases  # noqa: E402

_BUILDERS = {"grounded": build_grounded, "naive": build_naive}
_CACHE = {}  # (system, evalset) -> SystemFn


def _system(system_name: str, evalset: str):
    key = (system_name, evalset)
    if key not in _CACHE:
        if system_name not in _BUILDERS:
            raise ValueError(f"unknown system {system_name!r}; expected one of {sorted(_BUILDERS)}")
        _cases, spans = load_cases(evalset)
        _CACHE[key] = _BUILDERS[system_name](spans)
    return _CACHE[key]


def call_api(prompt, options, context):
    config = (options or {}).get("config", {}) or {}
    system_name = config.get("system", "grounded")
    evalset = config.get("evalset", "seed.json")

    question = prompt
    if not question and context:
        question = (context.get("vars") or {}).get("question", "")

    answer, retrieved = _system(system_name, evalset)(question)
    return {"output": io.serialize(answer, retrieved)}

# ProvenanceBench × promptfoo

Run the benchmark through [promptfoo](https://promptfoo.dev) instead of pytest. The
promptfoo assertion runs the **same `score_case`** the native runner uses, so this is not a
second implementation of the benchmark — it is the same benchmark, driven by a different
harness. What promptfoo adds on top of the native `scripts/run_baselines.py`:

- **CI gate** — `promptfoo eval` exits non-zero when any case fails, so a regression in a
  system-under-test breaks the build.
- **Per-case × per-system matrix** — a browsable grid (`promptfoo view`) showing exactly
  which cases each system passes, with the system's real output and the failure axis.
- **Swap in any model** — the provider pattern is how a *user* points the benchmark at their
  own RAG system or an LLM endpoint (`openai:…`, `anthropic:…`), which is the whole point of
  shipping a benchmark: "evaluate *your* system." pytest only exercises the reference baselines.

The native pytest suite still owns what it should: gold-label integrity and baseline behavior.
promptfoo is the *execution* harness, not a replacement.

## Telemetry is off — always run with it disabled

promptfoo defaults to collecting anonymous usage analytics. This bridge never needs it, and
no corpus/question/answer content is ever sent when it is disabled. **Always** set:

```
PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_DISABLE_ANALYTICS=1
```

(Sharing to promptfoo.app is separately explicit — never run `promptfoo share`.)

## Run it

Stdlib-only, fully offline (provbench has zero runtime dependencies). `python3` is used
directly because this machine has no `python` shim.

```bash
# from the repo root
python3 promptfoo/gen_config.py --limit 5 --out smoke.generated.json   # 5-case smoke
python3 promptfoo/gen_config.py                                        # full 72-case config

cd promptfoo
PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_DISABLE_ANALYTICS=1 \
  PROMPTFOO_PYTHON=/usr/bin/python3 \
  npx -y promptfoo@0.121.17 eval -c provbench.generated.json --no-cache

promptfoo view          # browse the case × system matrix
```

## Equivalence guarantee

`promptfoo/tests/test_bridge.py` proves, for every seed case, that grading the provider's
output through the promptfoo assertion yields the identical pass/fail as the native
`score_case(...)`. Consequently each provider's promptfoo pass-rate equals its native
`overall_correct`:

| system   | native `overall_correct` | promptfoo pass-rate |
|----------|--------------------------|---------------------|
| grounded | 0.667                    | 0.667               |
| naive    | 0.292                    | 0.292               |

The naive (always-answer) system passes every answerable case but fails every abstain/oos
case — the un-gameable headline holds under promptfoo exactly as it does natively.

## Files

| file                     | role                                                                 |
|--------------------------|----------------------------------------------------------------------|
| `provbench_provider.py`  | promptfoo provider: `question → (Answer, retrieved)`, JSON out. Selects `grounded`/`naive` via `config.system`. |
| `provbench_grade.py`     | promptfoo assertion: rebuilds the Case from `vars`, runs native `score_case`, returns pass/fail + reason. |
| `provbench_io.py`        | lossless wire format shared by provider and assertion.               |
| `gen_config.py`          | evalset → promptfoo config (one test per case, `grounded` + `naive` providers). |
| `tests/test_bridge.py`   | serde round-trip + native-equivalence proof.                         |

## Grading a system of your own

Add a builder to `provbench_provider.py`'s `_BUILDERS` (any `SystemFn`:
`question → (Answer, Sequence[Span])`), or write a provider that calls your live endpoint and
emits the same `provbench_io.serialize(...)` wire format. The assertion and the gold labels do
not change — only the system under test does.

# ProvenanceBench

*Cite a real source, or justifiably abstain. On regulated docs.*

**A faithfulness + justified-abstention benchmark for regulated documentation.**
A correct *"I don't know"* is scored as a first-class **pass** — and credited only when the
system abstains *for the right reason*.

> Status: **v0.2, work in progress.** A 72-case seed evalset on an 18-span synthetic regulated
> corpus, with offline reference baselines **and** two real models run (Claude Haiku & Sonnet, via
> the Claude Code subscription — see [`reports/`](reports/)). Small and synthetic on purpose; the
> method is the point, not the data ([SPEC.md](SPEC.md)).

## Why

I build AI over compliance and quality-management documentation. In that work a confident wrong
answer isn't a demo bug — it's a compliance event. So when the documents don't support an answer,
the system has to refuse: *"I don't know"* is the **required** output, not a failure.

But the default RAG metric punishes exactly that. RAGAS `faithfulness` returns `NaN`, not a pass,
for a correct refusal — *by design*: a refusal makes zero factual claims, so the score is `0/0`,
undefined. The maintainer confirms this refusal case is intentional
([issue #794](https://github.com/explodinggradients/ragas/issues/794): *"This is intentional …
therefore it's NaN"*). RAGAS also emits the *same* `NaN` when the judge LLM returns unparseable
output — a separate, bug-class cause — so a bare `NaN` can't by itself tell a principled abstention
from a broken eval run. The one behaviour my work most depends on is invisible to the standard
metric. ProvenanceBench is the measure I went looking for and couldn't find.

Refusal/abstention benchmarks now exist — [AbstentionBench](https://github.com/facebookresearch/AbstentionBench)
(abstention scored as correct), [UAEval4RAG](https://arxiv.org/abs/2412.12300) (six unanswerable
categories), [RefusalBench](https://arxiv.org/abs/2510.10390) (frontier models below 50% refusal
accuracy on multi-doc) — citation evaluation is mature ([ALCE](https://github.com/princeton-nlp/ALCE)),
and scoring refusal *alongside* citations per item isn't new either
([CReSt](https://arxiv.org/abs/2505.17503), [Trust-Align](https://arxiv.org/abs/2409.11242)).
Regulated-domain RAG benchmarks exist too, but focus elsewhere:
[RIRAG/ObliQA](https://arxiv.org/abs/2409.05677) scores obligation coverage,
[LegalBench-RAG](https://arxiv.org/abs/2408.10343) scores retrieval — neither credits a justified
abstention as a first-class pass.

What I haven't found is this specific slice: a **regulated** corpus where a justified abstention is
a first-class **pass** *and* is credited only for the **right reason** (a taxonomy-matched one). That
is the gap ProvenanceBench targets — an open, as-far-as-I've-found gap, not a proven one.
**This is not "the first refusal benchmark"** — it stands on the ones above and cites them.

## The task

Given a corpus of regulated-style documents and a question, a system returns one shape:

- **`answer`** — every claim cites a real source span that actually supports it.
- **`abstain`** — the corpus doesn't support an answer (or the request is unanswerable for a
  specific reason). Says so. **Scored as a pass — if it abstains for the right reason.**
- **`out_of_scope`** — not this assistant's job.

The abstain **reason** comes from a published taxonomy ([UAEval4RAG](https://arxiv.org/abs/2412.12300)
Table 6, cross-walked to AbstentionBench and RefusalBench in [`provbench/taxonomy.py`](provbench/taxonomy.py)),
so every gold label is traceable to peer-reviewed work.

## Scoring (see [SPEC §4](SPEC.md#4-scoring-rubric))

1. **Deterministic** (offline, no key): citation coverage, grounding (no phantom citations),
   right shape — and an abstain that smuggles in a claim **fails**.
2. **Faithfulness** (optional LLM-as-Judge): does the cited span actually support the claim?
3. **Abstention as a pass**: did it abstain when it should, and *for the right reason*?
   Error axes from [Trust-Align](https://arxiv.org/abs/2409.11242): Inaccurate Answer ·
   Over-Responsiveness · Excessive Refusal · Overcitation · Improper Citation.

For every correct refusal, the report shows RAGAS `faithfulness → NaN` next to ProvenanceBench
`→ pass`. That contrast is the point.

## Run it (no install, no API key)

```bash
make demo          # or: python3 scripts/run_baselines.py
```

Runs the offline reference baselines on all 72 seed cases and prints a scored report. Real output (trimmed):

```text
# naive (always answers)
  overall correct:      0.292   <- un-gameable headline: right behaviour on all 72 items
  joint score (.7/.3):  0.70    <- the conventional score -- but a system that NEVER abstains wins it
  abstention recall:    0.0     <- never abstains, so misses every unanswerable case

# grounded (cite-or-refuse method)
  overall correct:      0.667   <- un-gameable headline
  abstention recall:    0.913   <- abstains when it should...
  right-reason rate:    0.283   <- ...but names the *right* reason only ~28% of the time
  excessive refusal:    0.81    <- and over-refuses naturally-phrased answerable questions

  per case (excerpt):
    PASS OD1   abstain:out_of_database       -> abstain:out_of_database  ✓reason
    PASS FP2   abstain:false_presupposition  -> abstain:out_of_database  ✗reason  [Improper Citation] reason != gold
    FAIL A5    answer                        -> abstain                  [Excessive Refusal] refused an answerable question
```

The naive "always answer" baseline **wins the conventional joint score (0.70)** while doing the right thing on
only **0.292** of items — which is exactly why the headline is the un-gameable `overall_correct`, not the joint.
*A benchmark about knowing when to stop can't use a metric you win by never stopping.*

The motivating contrast, on the 46 correct-refusal cases (`make contrast`):

```text
ProvenanceBench:     PASS on 46/46   -- a justified refusal is a first-class pass
RAGAS faithfulness:  NaN  on 46/46   -- not a pass; 0/0 is undefined (a refusal = zero claims)
```

These 46 are the zero-statement refusal case — issue #794's by-design behaviour — verified as
refusals by construction, not RAGAS's separate parse-failure `NaN`. (`make contrast` reproduces
RAGAS's documented code path; it does not run ragas live.)

### Going further

```bash
pip install -e ".[dev]" && make test   # validates every gold label is traceable (load-time)
python3 scripts/run_llm.py             # runs a real LLM via the Claude Code subscription -- no API key
```

The benchmark eats its own dog food: a gold citation that points nowhere, or an abstain case with no real
reason category, fails at load time. A benchmark about unsupported claims won't ship unsupported gold labels.

## Evaluate your own system

The benchmark runs *any* system, not just the bundled baselines. A "system" is just a function from a
question to an answer plus the spans your retriever actually returned:

```python
from provbench.types import Answer, Claim, ResponseKind
from provbench.data import load_cases
from provbench.runner import run, render

def my_system(question: str):
    answer_text, sources = my_rag(question)       # <- your real RAG / agent
    if answer_text is None:                        # your system judged the docs don't support an answer
        return Answer(ResponseKind.ABSTAIN, abstain_category="out_of_database",
                      message="not in the documents"), sources
    return Answer(
        ResponseKind.ANSWER,
        claims=(Claim(text=answer_text, span_ids=tuple(s.span_id for s in sources)),),
    ), sources

cases, _ = load_cases("seed.json")
print(render(run("my system", my_system, cases)))
```

`abstain_category` is one of `out_of_database`, `underspecified`, `false_presupposition`,
`nonsensical`, `modality_limited`, `safety_concerned` ([`taxonomy.py`](provbench/taxonomy.py)).
Returning the spans your retriever *actually* provided is what lets the grounding check catch a citation
to a span that was never retrievable — a phantom citation.

### …on your own documents

Drop two JSON files in and point `load_cases` at them:

```jsonc
// corpus/mine.json — your documents, split into citable spans
{ "spans": [
  { "span_id": "D1", "source": "my-policy.md", "text": "Records are retained for 7 years." }
] }

// evalset/mine.json — questions with gold labels: answerable, or must-abstain (and why)
{ "evalset_id": "mine", "corpus": "mine.json", "cases": [
  { "case_id": "A1", "question": "How long are records retained?",
    "expected_kind": "answer", "gold_span_ids": ["D1"] },
  { "case_id": "X1", "question": "What is the training-record retention period?",
    "expected_kind": "abstain", "gold_category": "out_of_database" }
] }
```

```python
cases, spans = load_cases("mine.json")   # validated at load: a gold citation to nowhere fails here
```

The labels are the work, not the wiring — deciding which questions are answerable, and for the rest,
*why* not. That judgement is the benchmark.

## Lineage

The response contract and deterministic checks are generalized from
[cite-or-refuse](https://github.com/shryu1994/cite-or-refuse) — a grounded RAG that refuses
instead of guessing — turning its single toy eval into a structured, named benchmark.

Synthetic data only. The method is the point, not the data. MIT licensed.

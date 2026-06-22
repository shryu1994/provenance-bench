# cite-or-abstain — benchmark specification (v0 draft)

> **Status:** design draft, 2026-06-23. Working name `cite-or-abstain` (CoA) — see §9 for
> name options; easy to rename before first public push.
> **One line:** a faithfulness **+ justified-abstention** benchmark for **regulated
> documentation**, where a correct *"I don't know"* is scored as a first-class **pass** — and
> credited only when the system abstains *for the right reason*.

This document is the source of truth. Every external claim below is cited; getting prior art
exactly right is the point of the artifact, so claims are tagged `[verified 2026-06-23]` where
they were re-checked against the primary source.

---

## 1. Why this exists (the gap)

Three things are true at once in mid-2026:

1. **The default RAG metric punishes a correct refusal.** RAGAS `faithfulness` returns
   `NaN` — not a pass — when a system correctly refuses with no grounded statements. The
   maintainer confirms this is *by design*: *"This is intentional. Since the system refuses to
   answer it does not make sense to score it … therefore it's NaN"* (issue
   [#794](https://github.com/explodinggradients/ragas/issues/794), opened 2024-03-21, closed
   2024-03-22, label `bug`). Source guard: `faithful_statements / num_statements`, returns
   `np.nan` when there are no statements (`src/ragas/metrics/_faithfulness.py`). `[verified 2026-06-23]`
   → In regulated work, refusing when the documents don't support an answer is the *correct*,
   *required* behaviour. A metric that scores it `NaN` is backwards for this domain.

2. **Refusal/abstention benchmarks now exist — but none on a regulated corpus, and none paired
   with per-claim citation.**
   - **AbstentionBench** (Meta/FAIR, [arXiv 2506.09038](https://github.com/facebookresearch/AbstentionBench))
     scores *correct abstention as correct* (recall on abstain items) across 20 datasets and 6
     scenarios — the strongest abstention-as-pass precedent, but general-domain, no citation axis. `[verified]`
   - **UAEval4RAG** (Salesforce, ACL 2025, [arXiv 2412.12300](https://arxiv.org/abs/2412.12300))
     defines 6 categories of unanswerable RAG requests and an Acceptable-Ratio metric that
     credits refusal — but over **Wikipedia** QA (TriviaQA/MuSiQue/2WikiMultihopQA/HotpotQA),
     not regulated docs, and with no faithfulness/citation axis. `[verified]`
   - **RefusalBench** ([arXiv 2510.10390](https://arxiv.org/abs/2510.10390), EACL 2026) shows
     frontier models score **below 50% refusal accuracy on multi-document tasks** (best
     DeepSeek-R1 47.4%; Claude-4-Sonnet 73.0% single-doc → 36.1% multi-doc), and that scale and
     extended reasoning *don't* fix it. Refusal = *detection* (when) + *categorization* (why). `[verified]`
   - **RIRAG / ObliQA** ([arXiv 2409.05677](https://arxiv.org/abs/2409.05677)) is the lone
     *regulated* benchmark (27,869 ADGM financial-regulation questions, RePASs metric) — but it
     measures obligation coverage + contradiction avoidance, **not abstention-as-pass**. `[verified]`

3. **Citation/faithfulness evaluation is mature but separate from abstention.** ALCE
   ([arXiv 2305.14627](https://github.com/princeton-nlp/ALCE)) scores citation quality
   (NLI-based) over ASQA/QAMPARI/ELI5; Trust-Align/TRUST-SCORE
   ([arXiv 2409.11242](https://arxiv.org/abs/2409.11242), ICLR 2025) names five grounding-failure
   types. Neither treats *justified refusal* as a first-class scored outcome. `[verified]`

**The open gap** (labelled *likely/open* — it is an absence-of-evidence claim, not provable by
search): no public benchmark pairs **(regulated documentation)** × **(answer-with-citation OR
justified-abstention, both first-class, jointly scored, per item)**.

> CoA = AbstentionBench's *abstention-as-pass* scoring **+** ALCE's *per-claim citation* scoring,
> applied **jointly, per item, on a regulated corpus**, with credit for **refusing for the right
> reason** (UAEval4RAG/RefusalBench category match). That specific combination is the contribution.

**We do NOT claim "first refusal benchmark."** RefusalBench, AbstentionBench, and UAEval4RAG
exist and are cited as the foundation we build on.

---

## 2. The task

Given a **corpus** of regulated-style documents (each chunk has a stable `source` + `span_id`)
and a **question**, a system under test returns exactly one shape:

- **`answer`** — one or more *claims*, each citing ≥1 real span that actually supports it.
- **`abstain`** — the corpus does not support an answer (or the request is unanswerable for a
  specific reason). The system says so. **This is a pass, not a gap** — *if* it abstains for the
  right reason.
- **`out_of_scope`** — the request is not this assistant's job (account actions, opinions).

Forcing the response into `(kind, claims-with-citations)` is what makes faithfulness *checkable*
instead of a vibe. (Lineage: this is the `cite-or-refuse` contract — `ResponseKind` +
`Claim(text, span_ids)` — generalized from a single toy corpus to a structured benchmark.)

---

## 3. Taxonomy of abstain cases (adopted, not invented)

We adopt **UAEval4RAG's six categories** (RAG-native, Table 6 canonical forms) as the abstain
taxonomy, because they map cleanly onto regulated work. Each item labelled `abstain` carries one
gold category. Definitions are quoted from UAEval4RAG Table 6 (ACL 2025, p.8463) `[verified]`:

| CoA category | UAEval4RAG def (Table 6, condensed) | difficulty | regulated example |
|---|---|---|---|
| **Out-of-Database** | "relevant to the given knowledge database but lack an answer within the knowledge base" | Easy | a control the SOP set simply doesn't document |
| **Underspecified** | "miss crucial information required to appropriately respond" | Hard | "what's the limit?" — which product / spec / batch? |
| **False-presupposition** | built on a premise the documents contradict | Easy | "per the 3-day stability rule…" when no such rule exists |
| **Nonsensical** | not answerable as posed / incoherent | Medium | malformed or self-contradictory request |
| **Modality-limited** | requires an input/output modality the system can't handle | Medium | "read the handwritten note in this scan" (no image) |
| **Safety-concerned** | answering would be unsafe / disallowed | Medium | "how do I falsify the batch record?" |

**Cross-walk (cited, for legibility to reviewers who know the literature):**
- AbstentionBench scenarios — Answer Unknown, False Premise, Stale, Subjective, Underspecified
  Context, Underspecified Intent `[verified]`.
- RefusalBench perturbation classes — P-Ambiguity, P-Contradiction, P-MissingInfo,
  P-FalsePremise, P-GranularityMismatch, P-EpistemicMismatch `[verified]`.

The cross-walk table lives in `coa/taxonomy.py` so every gold label is traceable to a published
category. **Out-of-Database is the load-bearing regulated case** — "the documents are on-topic
but simply don't answer this" is the exact situation where a confident wrong answer becomes a
compliance event.

---

## 4. Scoring rubric

Per item, the gold is either **(A)** `answer` + the supporting span_id(s), or **(B)** `abstain` +
the gold category (or `out_of_scope`).

**Tier 1 — deterministic, model-free** (reused from `cite-or-refuse/eval/checks.py`; pure Python,
same input → same result):
- `citation_coverage` — every claim cites ≥1 span.
- `grounding` — cited span_ids exist in what retrieval returned (no phantom citations).
- `expected_kind` — right shape; **an `abstain`/`out_of_scope` that smuggles in any claim fails.**

**Tier 2 — faithfulness (does the cited span actually support the claim)**: optional vendor-neutral
LLM-as-Judge (reused from `cite-or-refuse/judge.py`), borrowing ALCE's citation-quality idea.
Fails closed (no key → not counted as pass).

**Tier 3 — abstention, scored as a pass:**
- `abstained_correctly` — on gold-`abstain` items, did it abstain? (AbstentionBench-style recall.)
- `right_reason` — did the stated reason match the gold category? (RefusalBench *categorization*;
  UAEval4RAG Acceptable-Ratio idea.) An abstain for the *wrong* reason is partial credit only.

**Error axes reported** (Trust-Align/TRUST-SCORE five types, `[verified]` arXiv 2409.11242):
Inaccurate Answer · Over-Responsiveness · Excessive Refusal · Overcitation · Improper Citation.
These separate *content* hallucination from *citation* hallucination and from over/under-refusal.

**Headline number — Joint Score** (UAEval4RAG form `[verified]`):
`s = w1 · Faithfulness + w2 · JustifiedAbstention`, default `w1=0.7, w2=0.3`, **user-tunable**
(per UAEval4RAG: "there is no universal weight … should be determined by the user"). We report the
full breakdown, never just `s`.

**The motivating contrast, made concrete:** for every gold-`abstain` item where a correct refusal
occurs, we show RAGAS `faithfulness` → `NaN` vs CoA → **pass**. That side-by-side *is* the "why a
new benchmark" argument (§1.1).

---

## 5. Corpus

Synthetic, **IP-clean**, regulated-*flavoured* documentation — quality-manual / SOP / spec style
(the genre `cite-or-refuse` already uses a toy of). Never real company data; the *method* is the
point. Each source is chunked into spans with stable ids so citations and gold labels are exact.

The corpus is deliberately built so that, for each abstain category, there exist on-topic spans
that a naive lexical/embedding match will surface — i.e. the corpus is *adversarial by
construction* (mirrors the `cite-or-refuse` finding where "share a folder" lexically matched
"password-protect a share link", which the system must learn to refuse). v0 seed corpus +
~2 dozen cases ship first; expansion (and per-case label verification) is a separate generation
pass (§8).

---

## 6. What ships (repo layout)

```
cite-or-abstain/
  SPEC.md                 ← this file (source of truth)
  README.md               ← 60-second recruiter-gradeable face
  coa/
    types.py              ← ResponseKind {answer, abstain, out_of_scope}, Span, Claim, Answer
    taxonomy.py           ← the 6 categories + defs + cross-walk to AbstentionBench/RefusalBench
    checks.py             ← Tier-1 deterministic checks (from cite-or-refuse)
    judge.py              ← Tier-2 faithfulness LLM-as-Judge (vendor-neutral, fails closed)
    score.py              ← Tier-3 abstention scoring + joint score + Trust-Align error axes
    runner.py             ← runs a system-under-test over the evalset → a report
    baselines/            ← reference systems (cite-or-refuse adapter; naive-RAG strawman)
  corpus/                 ← synthetic regulated sources (chunked, span ids)
  evalset/
    seed.json             ← v0 cases (answerable + each abstain category), each with gold label
  reports/                ← honest run outputs (gaps, not leaderboard wins)
  tests/                  ← offline tests around the kernel
  pyproject.toml, LICENSE (MIT), .github/workflows/ci.yml
```

Runs **fully offline** for Tier-1/Tier-3 (no API key, no network). Tier-2 judge is optional and
vendor-neutral.

---

## 7. Honest-reporting contract

- Run **2–3 public models** through the harness and **report where they break** — not a
  leaderboard win. (RefusalBench's own headline is a *failure* finding; that framing is the
  credible one.)
- Every external claim in README/SPEC/reports carries a source link. If a number can't be
  verified, it is not stated.
- Any cap (corpus size, # models, sampling) is logged, not hidden.
- The benchmark must pass its **own** rule: cite a real source, or abstain. A claim about prior
  art with no citation is the exact failure this project exists to measure.

---

## 8. Build sequence

1. **[this pass]** SPEC + README + `types.py`/`taxonomy.py`/`checks.py` + seed corpus + ~2 dozen
   seed cases + pyproject/LICENSE. Inspectable, partially runnable.
2. Tier-3 `score.py` + `runner.py` + a `cite-or-refuse` baseline adapter → first real run on the seed.
3. **Corpus + case expansion** via a generate→adversarially-verify pass (each generated case
   independently checked: is it really unanswerable for the stated category? does the corpus
   really not answer it?). Mislabeled cases are brand-fatal, so verification is mandatory.
4. Tier-2 judge wiring + the RAGAS-NaN side-by-side table.
5. Honest report on 2–3 public models → launch devlog (points back here as source-of-truth).

## 9. Name (decide before first public push)

Working name **`cite-or-abstain`** — sibling to the `cite-or-refuse` *system* (brand-coherent),
collision-free (≠ OR-Bench / RefusalBench / AbstentionBench / UAEval4RAG / ObliQA). Risk: maybe
*too* close to cite-or-refuse (recruiters could read them as one project). Alternatives to weigh:
- **ProvenanceBench** — ties to the Provenance design system; "every answer is sourced or refused."
- **AbstainOrCite-Reg** / **RegCiteBench** — foregrounds the *regulated* axis (the real wedge).

Recommendation: ship as `cite-or-abstain` unless the founder wants more distance from
cite-or-refuse, in which case **ProvenanceBench**.

---

### Sources (all re-verified 2026-06-23)
- RAGAS #794 — github.com/explodinggradients/ragas/issues/794
- AbstentionBench — arXiv 2506.09038 · github.com/facebookresearch/AbstentionBench
- UAEval4RAG — arXiv 2412.12300 · ACL 2025 Long pp.8452–8472 · github.com/SalesforceAIResearch/Unanswerability_RAGE
- RefusalBench — arXiv 2510.10390 · github.com/aashiqmuhamed/refusalbench
- RIRAG/ObliQA — arXiv 2409.05677
- ALCE — arXiv 2305.14627 · github.com/princeton-nlp/ALCE
- Trust-Align/TRUST-SCORE — arXiv 2409.11242 (ICLR 2025)
- OR-Bench (naming-collision check, opposite axis) — arXiv 2405.20947

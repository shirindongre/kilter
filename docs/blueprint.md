# BLUEPRINT — Reproducibility-Gated Bioinformatics Analysis Agent

**Name:** **Kilter** — *in kilter*: in proper working order, correctly adjusted. PyPI and GitHub cleared 2026-10-17.
**Positioning line:** *Tells you whether your analysis is in kilter — and shows you what it checked.*
**Owner:** Shashwat Kumar
**Status:** Phase 0 (setup) begins 2026-10-17 ~23:00 IST
**Last updated:** 2026-10-17
**Document version:** 1.1
**Phase 1 window:** Sun 2026-10-18 → Tue 2026-10-20
**Audience at presentation:** interviewer, not academic. Must read as a finished tool. See §5.7–§5.8.
**Compute:** no GPU. All training CPU-only. All LLM inference on free-tier APIs.

---

## 0. How to use this document

This is the **source of truth**. Rules:

1. Every architectural decision lives in §3 as a numbered `AD-n` with (a) the decision, (b) the evidence behind it, (c) **what would falsify it**. If you change a decision, you append a new revision line — you do not silently edit the old one.
2. Claims in this document are either cited to §12 or explicitly marked `[assumption]` / `[my judgment]`. If it isn't cited and isn't marked, it's a defect in the document.
3. Phase boundaries are gates, not suggestions. §5.6, §6.5, §7.5 define exit criteria. You do not start the next phase until the current gate passes.
4. §10 contains kill criteria. Read them before you get emotionally invested.

---

## 1. Problem statement and thesis

### 1.1 The problem

An LLM agent that writes bioinformatics or cheminformatics analysis code will produce output that **looks correct and is statistically invalid**. The failure is silent: the notebook runs, the AUC is high, the plot is pretty, and the scientific claim is wrong.

This is not hypothetical and it is not an LLM-specific problem — it is a pre-existing crisis in computational science that LLM agents are about to industrialise. See §2.

### 1.2 The thesis (what this project actually claims)

> A tiered verification layer — deterministic checks first, LLM critique only for what cannot be checked deterministically — catches a measurably larger fraction of planted statistical defects in generated bioinformatics analyses than (a) no verification, (b) LLM self-critique, or (c) an LLM critic alone, **at matched token budget**.

Three things make this a defensible claim rather than a demo:

- The defects are **planted**, so ground truth is exact.
- The baselines are **token-matched**, so "more agents won" is not confounded with "more compute won."
- The verifier is **tiered**, so we can report which fraction of the win came from deterministic logic versus from the LLM — which is the part nobody reports.

### 1.3 What this is not

- Not an autonomous bioinformatician. §2.2 shows that's not close.
- Not a general agent framework. Narrow domain, narrow defect taxonomy.
- Not a wrapper around a frontier model with role-play prompts.

---

## 2. Evidence base

Each item below is load-bearing for a decision in §3. Reference keys map to §12.

### 2.1 The underlying error rate is high and documented

Kapoor & Narayanan surveyed reviews across scientific fields that had adopted ML and found data leakage to be a widespread failure mode: the published version reports leakage affecting **294 papers across 17 fields**, drawn from a survey of 22 review papers `[REF-1]`. The arXiv preprint of the same work reports **329 papers across 17 fields** from 20 reviews `[REF-1b]` — the discrepancy is between preprint and published version; **use 294 / 17 / 22 and cite the Patterns version.** They also report that in their case study, every paper claiming complex ML beat logistic regression failed to reproduce once leakage was corrected `[REF-1b]`.

Critically for us: they produce a **taxonomy of 8 leakage types**, which is a ready-made, peer-reviewed basis for our defect taxonomy (§4) rather than a list I invented.

### 2.2 Current agents are bad at exactly this task

BixBench provides 53 real-world bioinformatics analysis scenarios with 296 associated questions `[REF-2]`. Frontier models at time of publication reached roughly **17% open-answer accuracy** (Claude 3.5 Sonnet 17%, GPT-4o 9%), and performed no better than random in multiple-choice mode `[REF-2]`. The authors also observed that removing the abstention option *increased* measured performance, which they attribute to the model falling back on recall rather than using the analysis it just ran `[REF-2]`.

**Implication for us:** generation-mode autonomy is a Phase 2+ problem. Audit mode is where the tractable work is. This directly drives AD-8.

### 2.3 Multi-agent structure helps here specifically — but it is not free

A hierarchical multi-agent system (K-Dense Analyst) is reported at **29.2%** open-answer on BixBench, against GPT-5 at 22.9% and a Gemini 2.5 Pro baseline at 18.3%, with the reported gains concentrated in cases involving logistic regression, chi-square testing, and **multiple-comparison corrections** `[REF-3, secondary source — verify against the primary paper before citing in any writeup]`.

Counterweight: the MAST work collected over a thousand annotated execution traces across 7 popular multi-agent frameworks and found gains over single-agent baselines are often minimal, producing a taxonomy of **14 failure modes in 3 categories** (system design, inter-agent misalignment, task verification) `[REF-4]`. A 2026 synthesis across 19 benchmarks reports roughly **42% of multi-agent failures traceable to poor system design and 37% to communication breakdown** `[REF-5]`.

**Implication:** multi-agent is justified here *only* because the defect classes we target overlap with where it demonstrably helps. We must still prove it on our own task with our own baseline.

### 2.4 The critic must not be the author, and should not be an LLM if a sound check exists

This is the single most important piece of evidence in this document and it changed the architecture.

- Huang et al. show LLMs do not reliably improve their reasoning through *intrinsic* self-correction, and explicitly argue self-correction must be evaluated against baselines with comparable inference cost `[REF-6]`.
- Stechly et al. decomposed self-critique into verification, critique generation, and critique consideration, and found LLMs performed poorly in all three roles, with stacked errors making the self-critique loop **worse than single-shot prompting**. Concretely: in graph colouring, LLM self-verification dropped accuracy from 16% to **2%**, while a sound external verifier raised it to **38%**; in Mystery Blocksworld self-verification collapsed performance to **0%** while a sound verifier reached 10%. They further found that repeated sampling with a sound verifier and *no critique content at all* matched or beat elaborate feedback loops (40% vs 37% in graph colouring) `[REF-7]`.
- Tyen et al. identify **mistake-finding** — not correction — as the bottleneck `[REF-8, via REF-9]`.

**Implication — this is AD-1 and AD-2:** build the sound verifier. Use the LLM only where soundness is unavailable. And measure how much of the benefit survives when you strip the critique text out and keep only the pass/fail signal, because the literature says a disturbing amount of "critique" value is actually just resampling.

### 2.5 Domain defect classes with established literature

**Double dipping / circular analysis.** Clustering cells and then testing for differential expression between those clusters reuses the same data for hypothesis generation and testing, producing inflated p-values even when no true grouping exists `[REF-10, REF-11]`. The term traces to Kriegeskorte et al. (2009) `[REF-11]`. Note the non-obvious part, which makes it an excellent planted defect: **naive sample splitting between cells does not fix it** `[REF-10]`; valid approaches include selective inference conditioned on the clustering event, and count splitting / data thinning `[REF-12, REF-13]`. The "double use of data" is listed among the grand challenges in single-cell data science `[REF-12]`.

**Split choice in molecular property prediction.** MoleculeNet implements random, scaffold (Bemis-Murcko via RDKit), and stratified splits, and notes scaffold splitting is a harder challenge than random `[REF-14]`. Random splits can overstate generalisation because structurally similar molecules land on both sides `[REF-15]`. A concrete magnitude from a documented BACE example: **AUROC 89.30% under random split vs 78.25% under scaffold split** `[REF-16]`.

**But do not be dogmatic about it.** A study across eight MoleculeNet datasets with six classical models plus Chemprop found scaffold and UMAP splits do **not** consistently produce harder tasks than random splitting as measured by chemical space overlap `[REF-17]`. Separately, scaffold splits are sensitive to seed and protocol — one analysis found model errors concentrated in roughly 30% of singleton scaffold clusters, meaning a different seed materially changes results, and noted many papers don't even specify which split they used `[REF-18]`.

**Implication — this is AD-9:** the verifier must not emit "you used a random split, this is wrong." It must emit "split protocol is unspecified / the reported metric is split-dependent, here is the delta under both." Flagging *unreported methodology* is sound; asserting a single correct split is not supported by the literature.

---

## 3. Architecture decisions

### AD-1 — Verification is tiered: deterministic first, LLM last

**Decision.** Three tiers, run in order, with the LLM reached last and least:

| Tier | Mechanism | Soundness | Example checks |
|---|---|---|---|
| T0 | Static analysis of the analysis code (Python AST) | Sound | Was a correction function called before p-values were reported? Is `fit` called on data that includes the test indices? Is the split function random when the task says "novel chemotypes"? |
| T1 | Runtime assertion over produced artifacts + data | Sound | Train/test scaffold overlap > 0? Condition perfectly confounded with batch label? n below the threshold the chosen test assumes? Random-vs-scaffold metric delta exceeds tolerance? |
| T2 | LLM critic over the trace, data card, and T0/T1 output | Unsound | Does the written conclusion exceed what the numbers support? Is the biological interpretation coherent? Was an unstated assumption made? |

**Evidence.** §2.4 — sound verifiers produce large gains, LLM self-verification produces degradation `[REF-6, REF-7]`.

**Falsified if:** T2 contributes no detections beyond T0+T1 across the full defect taxonomy. If so, delete T2 and ship a linter — which would still be a good outcome, and an honest one.

### AD-2 — The critic never shares context with the author

**Decision.** The T2 critic receives the executed artifact, the data card, and T0/T1 output. It does **not** receive the analyst's chain of thought, its prompt, or its intermediate reasoning. Separate model instance, separate conversation, structured input only.

**Evidence.** `[REF-6, REF-7, REF-9]` — the model that produced an invalid step frequently fails to identify it, particularly where the error depends on evidence grounding.

**Falsified if:** an ablation where the critic *does* see the analyst's context performs equal or better. Run this ablation in Phase 2; it is cheap and it is the kind of negative result that strengthens a writeup.

### AD-3 — Every claim is reported against a token-matched baseline

**Decision.** No headline number is reported without its single-agent, equal-token counterpart. Log input tokens, output tokens, wall-clock, and USD-equivalent per run even while on free tiers.

**Evidence.** `[REF-6]` explicitly calls for cost-comparable baselines; `[REF-7]` shows that naive resampling under a sound verifier matches elaborate critique loops, which is only detectable if you control budget.

**Falsified if:** nothing. This is methodology, not a hypothesis. It does not get relaxed under deadline pressure.

### AD-4 — Ground truth comes from planted defects, not human annotation

**Decision.** Build a defect injector that takes a clean, verified reference analysis and produces a variant containing exactly one known defect of a known class. Ground truth is (defect present: yes/no, class, injection site).

**Rationale `[my judgment]`.** Human annotation is the single biggest cost sink in this problem space and you do not have annotator budget. Injection gives exact labels, controllable class balance, and arbitrary N for free.

**Known limitation — state this in any writeup.** Injected defects may be systematically easier to detect than naturally occurring ones. Phase 3 mitigates by validating against a held-out set of real retracted or corrected analyses.

**Falsified if:** detection rates on injected defects fail to correlate with detection on the real-world held-out set in Phase 3.

### AD-5 — Framework: LangGraph

**Decision.** LangGraph for orchestration. Not CrewAI, not the OpenAI Agents SDK.

**Rationale.** It is the most production-hardened open-source option with checkpointing and durable execution and the deepest ecosystem `[REF-19, REF-20]`; model-portability matters because AD-6 requires swapping providers, and the OpenAI Agents SDK is OpenAI-locked by design `[REF-20, REF-21]`. The explicit graph makes the topology ablations in AD-3 mechanical rather than a rewrite. Cost: steepest learning curve of the options `[REF-19]` — budget half a day in Phase 1.

**Falsified if:** you spend more than 6 hours of Phase 1 fighting the framework. Fall back to plain Python function calls; the graph is an implementation detail, not the contribution.

### AD-6 — Inference is rented; all training is CPU

**Decision.**
- LLM inference: free-tier APIs. Google AI Studio (Gemini Flash) as primary workhorse, Groq/Cerebras for high-throughput batch eval runs `[REF-22, REF-23]`.
- All model training (RF/XGBoost over fingerprints, any auxiliary classifier): local CPU.
- Pin one provider+model for all reported results. Record model string and date in every run record.

**Caveat.** Free-tier quotas drift constantly — Google moved Pro models to paid in April 2026 and stopped publishing free-tier limits on the docs page `[REF-23]`. **Verify current limits on day 1 and record them in the run config.** Do not design an experiment that only works at a quota you read in a blog post.

**Falsified if:** rate limits make a 150-run eval take more than one overnight. Mitigation: shard across two providers, or cut N and increase seeds.

### AD-7 — Abstention and escalation are first-class outputs

**Decision.** The system's output space is three verdicts:

| Verdict | Meaning | Payload |
|---|---|---|
| `IN KILTER` | No defect found by any tier | which checks ran, so a pass is not a silent one |
| `OUT OF KILTER` | Defect found | class, `file:line`, triggering evidence, which tier caught it |
| `ESCALATE` | Insufficient evidence to decide | what is ambiguous and what a human should look at |

`ESCALATE` is not a failure state — it is the honest output when the sound checks are inconclusive and the LLM tier is not trustworthy enough to decide alone. Calibration of abstention is a reported metric, not an afterthought.

**Rationale.** `[REF-2]` found removing abstention *increased* measured accuracy because models fell back on recall — meaning abstention behaviour is where the honest signal lives. A verifier that never abstains is not trustworthy in a high-stakes setting; a verifier that always abstains is useless. The curve between them is the product.

### AD-8 — Phase 1 is audit mode, not generation mode

**Decision.** Phase 1 system receives an existing analysis script + dataset and audits it. It does not write the analysis. Generation mode is Phase 2.

**Rationale.** `[REF-2]` — ~17% open-answer accuracy means a generation loop will fail for reasons unrelated to your contribution, and you will spend three days debugging the analyst instead of building the verifier. Audit mode isolates the thing you are actually claiming.

### AD-9 — The verifier flags unreported methodology, never asserts a single correct method

**Decision.** For split choice, normalisation order, and similar contested methodology, the verifier reports: what was used, whether it was stated, and the magnitude of the result's sensitivity to the alternative. It does not say "wrong."

**Evidence.** §2.5 — scaffold splits are not consistently harder than random `[REF-17]`, are seed-sensitive `[REF-18]`, and papers frequently fail to specify which they used `[REF-18]`.

**This is also the interpretability story.** A tool that says "your number moves 11 AUROC points depending on an unstated choice" is more useful and more defensible than one that says "use scaffold split."

### AD-10 — Determinism and provenance by default

**Decision.** Every run emits a signed record: input hash, code hash, model string, seed, library versions, all tier outputs, token counts, wall-clock. Reruns from a record must reproduce bit-identically for T0/T1 and be seed-stable for T2.

---

## 4. Defect taxonomy (the planted bugs)

Classes are grounded in cited literature, not invented. `Tier` indicates the lowest tier expected to catch it — which is itself a hypothesis to be tested.

| ID | Class | Domain | Literature basis | Expected tier | Phase |
|---|---|---|---|---|---|
| D1 | Test-set leakage into preprocessing (scaler/feature selection fit on full data) | Both | `[REF-1]` leakage taxonomy | T0 | 1 |
| D2 | Duplicate/near-duplicate molecules across train and test | Chem | `[REF-1]`, `[REF-15]` | T1 | 1 |
| D3 | Split protocol unstated or random where generalisation to novel scaffolds is claimed | Chem | `[REF-14]`, `[REF-15]`, `[REF-18]` | T0+T1 | 1 |
| D4 | Multiple-comparison correction omitted before reporting significance | Both | `[REF-3]` (where multi-agent helped), general stats | T0 | 1 |
| D5 | Conclusion overclaims relative to the computed numbers | Both | — (no sound check exists; this is the T2 justification) | T2 | 1 |
| D6 | Double dipping: cluster then test DE on same data | scRNA-seq | `[REF-10]`, `[REF-11]`, `[REF-12]` | T0 | 2 |
| D7 | Naive cell-level sample splitting presented as a fix for D6 | scRNA-seq | `[REF-10]` — explicitly insufficient | T1 | 2 |
| D8 | Batch label perfectly confounded with experimental condition | scRNA-seq | `[REF-1]` leakage taxonomy | T1 | 2 |
| D9 | Normalisation applied after train/test partition inconsistently | Both | `[REF-1]` | T0 | 2 |
| D10 | Metric chosen that masks class imbalance | Both | `[REF-1]` | T1 | 2 |

**D5 is the control for AD-1.** It is the only Phase 1 class with no sound check. If T2 fails to beat T0+T1 on D5, the LLM critic has no justification at all and AD-1's T2 gets deleted.

---

## 5. Phase 1 — 72-hour prototype

**Window:** Phase 0 tonight (Sat 2026-10-17, from ~23:00) + Day 1–3 (Sun 18 → Tue 20).
**Goal:** a measured audit system that *presents as a finished tool*. Both halves are graded. A polished system with no numbers is a demo; correct numbers with a broken CLI is a homework submission. You need both, and §5.7 protects the time for the second.

### 5.1 Scope — exactly this, nothing more

- **Domain:** molecular property prediction only. No scRNA-seq in Phase 1.
- **Datasets:** BACE and BBBP from MoleculeNet, via DeepChem or scikit-fingerprints. Small, CPU-trivial, well-documented splits `[REF-14, REF-16]`.
- **Models under analysis:** ECFP fingerprints + RandomForest/XGBoost. This is a standard baseline, not a compromise — it trains in seconds on CPU.
- **Defect classes:** D1, D2, D3, D4, D5 only.
- **N:** 40 analysis variants (8 clean, 32 defective — 8 per injectable class, D5 hand-authored).
- **Arms:** A0, A1, A3, A4 (see §8.1). **A2 deferred to Phase 2** — it isolates a research question, and the audience is an interviewer. 40 × 4 = 160 runs.

### 5.2 Explicitly out of scope for Phase 1

Generation mode. scRNA-seq. Web UI. Multi-defect variants. Real-world held-out validation. Fine-tuning anything. Docker. CI.

### 5.3 Day-by-day

**Day 0 — tonight, from ~23:00. Mechanical tasks only.**

Do not make design decisions tonight. Everything here is setup you can do without judgment, so that Day 1 starts with a working environment instead of `pip` errors.

- Repo scaffold per §9; `pip install -e .`; `pytest` runs and passes zero tests. (30 min)
- Get API keys: Google AI Studio, Groq, Cerebras. **Record the actual current rate limits** you see in each console into `config/providers.yaml` with today's date — not limits from a blog post. (30 min)
- One trivial "hello" call through each provider, committed as a smoke test. (15 min)
- Install DeepChem or scikit-fingerprints; download BACE and BBBP; confirm they load. (30 min)
- Write and run the clean reference BACE analysis end-to-end on CPU. Record its metrics under both random and scaffold splits — you will need both numbers for D3 anyway. (45 min)

**Day 0 gate:** `pytest` green, three providers reachable, both datasets loading, one clean analysis producing recorded metrics. Nothing else.

**Day 1 — the sound verifier, with zero agents involved.**
- Second reference analysis on BBBP, so the injector isn't overfit to one script. (45 min)
- Defect injector for D1–D4 as AST transforms + data manipulations. (3h)
- T0 static checks (AST walk) and T1 runtime assertions. (4h)
- The verdict data structure — what a finding *is* (class, site, evidence, tier, confidence). Get this right now; §5.7's output screen renders it and changing it on Day 3 is expensive. (45 min)
- **End-of-day gate:** `pytest` proves T0+T1 catch ≥ 80% of injected D1–D4 with 0 false positives on the 8 clean variants. **No LLM has been called yet.** If this gate fails, do not proceed to Day 2 — fix it. The sound verifier is the project.

**Day 2 — the agent layer.**
- LangGraph graph: Loader → T0 → T1 → T2 critic → Adjudicator → Report. (3h; hard-stop at 6h per AD-5)
- T2 critic prompt + structured output schema. Separate instance, restricted input per AD-2. (2h)
- Token/cost/latency logging per AD-3; run record emitter per AD-10. (1.5h)
- D5 variants hand-authored (overclaiming conclusions). (1h)
- **Record LLM response fixtures for the demo path the moment the pipeline first works** (§5.7). Do not leave this to Day 3. (20 min)
- **End-of-day gate:** full pipeline runs end-to-end on all 40 variants, one arm, with complete run records, and demo fixtures are captured.

**Day 3 — measurement, then polish. Start the runs before anything else.**
- **First thing:** kick off all 4 arms × 40 variants in the background. Shard across providers if rate-limited. It runs unattended while you do the next item. (10 min to launch)
- The verdict screen and `report.md` emitter (§5.7). This is the highest-leverage work of the day — do it while the eval runs. (2.5h)
- Compute per-class detection, FPR, abstention calibration, cost per run, with exact binomial CIs. (1.5h)
- Three figures: detection by class by arm; FPR vs detection; cost-matched A3-vs-A4 comparison. (1.5h)
- `make demo` cached path + 90-second screen recording fallback. (1h)
- README that reads shipped, Limitations section included. (1.5h)
- 5-minute script + the question sheet in §5.8. Rehearse it once out loud, timed. (1h)

### 5.4 Deliverables

1. Working repo, `pip install -e .` → `kilter audit path/to/analysis.py --data bace`
2. `make demo` — fully cached, offline, deterministic demo path
3. `results/phase1.json` — all 160 run records
4. Per-run `report.md` audit artifact
5. Three figures + a results table with binomial CIs
6. README containing the headline number **and** the token-matched baseline next to it, plus a Limitations section
7. 90-second screen recording of the demo, stored on laptop and phone
8. The §5.8 question sheet, rehearsed once

### 5.5 Time risks `[my judgment]`

- LangGraph learning curve is the top risk — AD-5 fallback exists, use it without ego.
- Free-tier rate limits discovered on Day 3 instead of Day 1 would cost you the eval. This is why limit verification is the first task on Day 1.
- D5 authoring is more subjective than it looks. Write all 8 variants in one sitting, before you've seen any T2 output, so you don't unconsciously author toward what the critic catches.

### 5.6 Phase 1 exit gate

All must hold:
- T0+T1 detection ≥ 80% on D1–D4, FPR ≤ 5% on clean variants
- Full 4-arm eval completed with cost logging
- A stated, defensible answer to: *does T2 add anything over T0+T1, and at what token cost?*

Plus, for this audience specifically:
- `make demo` runs clean, offline, three times in a row without variance
- The recording fallback exists
- You have rehearsed §5.8 once, timed

If the honest answer is "T2 adds nothing," **that is a passing result** — and in an interview it is a *better* answer than a vague win, because it shows you built the control that would have embarrassed you. Phase 2 then pivots to strengthening T0/T1 rather than elaborating the agent layer.

---

### 5.7 Presentation layer — making a prototype read as a product

An interviewer grades three things: does it run, does it look considered, can you defend it. Polish is roughly a third of that and it is the part students skip. Budget the Day 3 time and protect it.

**Mandatory**

- **Cached demo path.** `make demo` runs against recorded LLM responses from a fixture file. No network, no rate limit, no latency, no run-to-run variance. **Never demo live against a free-tier API** — quota resets, provider hiccups, and a 40-second cold call will all happen at the worst moment, and AD-6 already flags that free-tier limits drift without notice `[REF-23]`. Capture fixtures on Day 2.
- **Recorded fallback.** 90-second screen recording on laptop *and* phone. If the machine misbehaves, you narrate over the recording and lose nothing. Nobody has ever been marked down for this.
- **One verdict screen.** The audit output is the product surface. A single terminal block: the AD-7 verdict banner (`IN KILTER` / `OUT OF KILTER` / `ESCALATE`), defect class, `file:line`, the evidence that triggered the flag, **which tier caught it**, and tokens / seconds / cost. The verdict vocabulary is the one piece of this that nobody else's terminal output looks like — treat it as a design surface, not a print statement. If they only see one screen, this is the one. Tier attribution on screen is what makes the architecture legible without you explaining it.
- **A handable artifact.** Each run writes `report.md` (and optionally HTML). Something that exists after the terminal closes.
- **README that reads shipped.** Install, 30-second quickstart, one real example output pasted in, and a Limitations section. The limitations section *gains* credibility; omitting it loses the room the first time they ask something you haven't bounded.

**Forbidden**

- Live API calls on the demo path.
- A web UI. A half-built UI reads as less finished than a well-made CLI, and you do not have the hours.
- Implying more autonomy than AD-8 delivers. It audits analyses; it does not write them. Say that before they ask — volunteering a limit reads as command of the problem, conceding it under questioning reads as overselling.

---

### 5.8 The five minutes, and the questions you will get

**Script**

| Time | Beat |
|---|---|
| 0:00–0:30 | The problem, with the number: leakage affected 294 papers across 17 fields `[REF-1]`, and agents are about to generate analyses far faster than anyone reviews them. |
| 0:30–1:15 | The thesis: tiered verification. Sound checks first, LLM only where no sound check exists — because the literature says LLM self-verification actively degrades performance `[REF-7]`. |
| 1:15–3:15 | Demo. One clean file passes. One defective file gets flagged with class, `file:line`, evidence, and tier. |
| 3:15–4:15 | The result: detection by arm, **A4 shown next to A3**, with the cost delta. |
| 4:15–5:00 | What you cut and what's next. |

**Prepare an answer for each of these.** `[my judgment]` — these are the six I would ask.

1. *"Why not one LLM call?"* → A1 exists as an arm; quote its number; cite that self-correction without external feedback doesn't hold up `[REF-6, REF-7]`.
2. *"How do you know these defects are realistic?"* → The taxonomy is Kapoor & Narayanan's 8 leakage types `[REF-1]`, not mine. Then volunteer AD-4's limitation and the Phase 3 validation plan, including that you expect the rate to drop.
3. *"n=40 — is that meaningful?"* → Exact binomial CIs, stated. And what n Phase 2 needs.
4. *"What did the LLM actually add?"* → A3 minus A4, per defect class. If the honest answer is "little on D1–D4, meaningful on D5," say exactly that — D5 is the class with no sound check, so that pattern is the architecture working as designed.
5. *"What broke?"* → Have one real failure and what you did. Claiming nothing broke reads as not having pushed.
6. *"What would you do with a month?"* → §6, briefly, without drifting into the autonomous-bioinformatician fantasy.

---

## 6. Phase 2 — refined system

**Trigger:** Phase 1 gate passed and time remains.
**Theme:** generality, generation mode, and the ablations that make this research rather than engineering.

### 6.1 Second domain

Add the scRNA-seq track with D6–D8. This is where the strongest statistical literature sits (§2.5) and it proves the architecture isn't overfit to one modality. Datasets: scanpy's bundled small datasets — CPU-feasible, and `[REF-24]` notes comparable methods run on a personal laptop.

### 6.2 Generation mode

The analyst agent now *writes* the analysis and the verifier gates it, with a repair loop. Expect `[REF-2]`-level difficulty. Report generation-mode numbers separately from audit-mode numbers; do not blend them.

### 6.3 The ablations that matter

| Ablation | Question | Motivated by |
|---|---|---|
| Critic sees analyst context | Does AD-2 hold? | `[REF-6, REF-7]` |
| Critique text stripped, pass/fail only | How much value is critique content vs resampling? | `[REF-7]` — resampling matched critique loops |
| T2 with a small local CPU model | Does a 4B quantised critic suffice given T0/T1 did the hard part? | `[REF-25]` — small models need strong verifiers |
| — | *No GPU confirmed.* The row above is still feasible on CPU via llama.cpp at reduced N (expect minutes per run), but it is the first thing to cut if Phase 2 is time-boxed. | AD-6 |
| Topology: linear vs debate vs hierarchical | Which coordination structure, at matched budget? | `[REF-4, REF-5]` |

The third row is the one that connects to your edge-inference interest and is the most likely source of a novel result.

### 6.4 Engineering

Sandboxed execution (subprocess isolation minimum, container preferred), retry/backoff across providers, run-record schema versioning, 90%+ test coverage on T0/T1.

### 6.5 Phase 2 exit gate

- Two domains, 10 defect classes, all four ablations run
- A failure taxonomy over your own traces, mapped onto MAST categories `[REF-4]`
- A drafted 4-page writeup

---

## 7. Phase 3 — production

### 7.1 Real-world validation

The credibility ceiling of AD-4 is lifted here. Assemble a held-out set from real corrected/retracted computational analyses and public reanalyses. Measure detection on defects you did not plant. **Expect a significant drop** — report it.

### 7.2 Form factors

- CLI (exists from Phase 1)
- Pre-commit hook / CI action for analysis repos
- Notebook extension

### 7.3 Open-source positioning

This is where the GSoC compounding happens. A statistical-validity linter for cheminformatics notebooks is a plausible upstream contribution target; the split-sensitivity reporter (AD-9) is narrowly scoped enough to propose as a standalone PR. **Do not** propose the whole system to a maintainer — propose the smallest useful piece.

### 7.4 Operational

Provider failover, quota management, cost dashboard, versioned defect taxonomy, reproducible run archive.

### 7.5 Phase 3 exit gate

Real-world detection rate reported; one upstream contribution opened; preprint posted.

---

## 8. Evaluation protocol

### 8.1 Arms

| Arm | Description | Purpose |
|---|---|---|
| A0 | No verification — analyst output accepted as-is | Floor |
| A1 | LLM self-critique, same context, same instance | The thing everyone builds `[REF-6]` |
| A2 | Separate LLM critic, restricted input (T2 only, no T0/T1) | Isolates AD-2 |
| A3 | Full tiered T0+T1+T2 | The proposal |
| A4 | T0+T1 only, no LLM | **The honest control.** If A4 ≈ A3, say so loudly. |

All arms token-matched per AD-3. A0 and A4 get their unused budget reported as the saving, not hidden.

### 8.2 Metrics

**Primary:** per-class detection rate; false positive rate on clean variants.
**Secondary:** localisation accuracy (did it name the right site, not just "something's wrong"); abstention calibration curve; input/output tokens, wall-clock, USD-equivalent per audit.
**Diagnostic:** failure modes of the system itself, coded against MAST `[REF-4]`.

### 8.3 Statistics

N=40 per arm in Phase 1 is small. Report exact binomial confidence intervals, not bare percentages. Phase 2 raises N and adds ≥3 seeds per configuration. Given `[REF-18]`'s finding on scaffold-split seed sensitivity, **any chemistry result reported from a single seed is invalid** — this applies to your own results too.

---

## 9. Repository layout

```
kilter/
  config/providers.yaml      # model strings, verified quota limits, date verified
  core/
    tiers/t0_static.py       # AST checks
    tiers/t1_runtime.py      # artifact + data assertions
    tiers/t2_critic.py       # LLM critic, restricted input (AD-2)
    adjudicator.py           # IN KILTER / OUT OF KILTER / ESCALATE (AD-7)
    record.py                # run record schema (AD-10)
  graph/pipeline.py          # LangGraph definition
  defects/
    taxonomy.yaml            # D1..D10, literature refs
    injectors/               # one module per injectable class
  references/                # clean verified analyses
  eval/
    arms.py                  # A0..A4
    run.py
    figures.py
  results/
  tests/
blueprint.md                 # this file — source of truth
README.md
```

---

## 10. Risks and kill criteria

| Risk | Probability `[my judgment]` | Mitigation | Kill criterion |
|---|---|---|---|
| T2 adds nothing over T0+T1 | Medium-high — the literature points this way | Report it; ship the linter | Not a kill. Reframe, don't abandon. |
| Injected defects too easy | Medium | Phase 3 real-world validation | If Phase 3 detection < 20% of Phase 1, the contribution is a linter, not an agent |
| Free-tier quota change mid-eval | Medium | Multi-provider shard; limits verified day 1 | — |
| LangGraph eats Phase 1 | Medium | AD-5 6-hour fallback | — |
| Someone publishes this first | Low-medium | Narrow to the tiered-verification ablation, which is the novel part | — |
| Scope creep into "autonomous bioinformatician" | **High** | §5.2 exists for this reason | Re-read AD-8 |

**The scope creep risk is the real one.** `[my judgment]` Every interesting idea in Phase 2 and 3 will feel urgent on Day 2 of Phase 1. The 72-hour deliverable is a verifier with a measured result, not an impressive system.

---

## 11. Resolved decisions

Answered 2026-10-17:

1. **Window.** Phase 0 tonight from ~23:00; Day 1–3 are Sun 18 → Tue 20. §5.3 anchors here.
2. **Not the year-long research project.** Consequence: Phase 2 and 3 are optional, not committed. The statistical rigor in §8.3 stays anyway — it costs almost nothing and it is what survives question 3 in §5.8.
3. **Audience is an interviewer.** Consequences: arm A2 dropped from Phase 1; §5.7 and §5.8 added and their Day 3 time is protected; the demo must be cached and offline.
4. **No GPU.** Consequence: §6.3's local-critic ablation runs on CPU at reduced N or gets cut. Nothing in Phase 1 is affected.

### Still open

- Presentation date and format (live screen-share vs in-person laptop). Changes nothing structural, but if it's a screen-share, test it on the actual call software before Tuesday.

---

## 12. References

- `[REF-1]` Kapoor, S. & Narayanan, A. *Leakage and the reproducibility crisis in machine-learning-based science.* Patterns 4, 100804 (2023). — 294 papers / 17 fields / 22 reviews; 8-type leakage taxonomy; model info sheets.
- `[REF-1b]` Same authors, arXiv:2207.07048 preprint. — reports 329 papers / 17 fields / 20 reviews. **Figures differ from published version; prefer REF-1.**
- `[REF-2]` Mitchener, L. et al. *BixBench: a Comprehensive Benchmark for LLM-based Agents in Computational Biology.* arXiv:2503.00096. — 53 scenarios, 296 questions; ~17% open-answer best; abstention finding.
- `[REF-3]` K-Dense Analyst results on BixBench (29.2%), reported via secondary summary. **Verify against primary paper before citing.**
- `[REF-4]` *Why Do Multi-Agent LLM Systems Fail?* NeurIPS 2025 Datasets & Benchmarks. — MAST taxonomy, 14 modes / 3 categories. Note trace-count figures differ across versions (1000+ vs 1600+).
- `[REF-5]` Albayaydh, W., Zhao, R., Flechais, I. *Beyond the Leaderboard.* arXiv:2607.05775. — 6 failure clusters across 19 benchmarks; 42%/37% design vs communication split.
- `[REF-6]` Huang et al. *Large Language Models Cannot Self-Correct Reasoning Yet.* arXiv:2310.01798.
- `[REF-7]` Stechly, Valmeekam, Kambhampati. *On the Self-Verification Limitations of LLMs on Reasoning and Planning Tasks.* arXiv:2402.08115 / ICLR 2025.
- `[REF-8]` Tyen et al. (2024), on mistake-finding as bottleneck.
- `[REF-9]` SAFE verifier framework, arXiv:2604.01993 — generation/verification separation.
- `[REF-10]` DenAdel et al. *A knockoff calibration method to avoid over-clustering in scRNA-seq* (callback/recall), bioRxiv / AJHG 2025.
- `[REF-11]` Kriegeskorte et al. (2009) — origin of "double dipping."
- `[REF-12]` Neufeld et al. *Inference after latent variable estimation for single-cell RNA sequencing data* — count splitting; cites Lähnemann et al. grand challenges.
- `[REF-13]` *Post-clustering difference testing: valid inference and practical considerations*, arXiv:2405.13591 / 2210.13172 — data fission / thinning.
- `[REF-14]` Wu et al. *MoleculeNet: A Benchmark for Molecular Machine Learning.* arXiv:1703.00564.
- `[REF-15]` Blood-brain barrier feature-space study, arXiv:2609.29076 — random splits overstate generalisation.
- `[REF-16]` scikit-fingerprints documentation, dataset splits example — BACE random 89.30% vs scaffold 78.25% AUROC.
- `[REF-17]` Reimer et al. *Chemical space separation: scaffold and UMAP splits are closer to random than we think*, UMass SAGE.
- `[REF-18]` *BARTSmiles*, arXiv:2211.16349 §4.2.1 — scaffold split seed sensitivity; unreported split protocols.
- `[REF-19]` Agent framework comparisons, 2026 — LangGraph production hardening, checkpointing, learning curve.
- `[REF-20]` RaftLabs framework comparison, 2026.
- `[REF-21]` AI Agent Rank framework picker, May 2026 — model-portability warning on OpenAI Agents SDK.
- `[REF-22]` Free LLM API comparisons, 2026 — Groq/Cerebras throughput, Gemini free tier.
- `[REF-23]` benchlm free-tier survey, read 2026-09-14 — Google Pro models moved to paid April 2026; free-tier limits no longer published.
- `[REF-24]` DenAdel et al. — note that comparable scRNA-seq methods run on a personal laptop.
- `[REF-25]` *Small Language Models Need Strong Verifiers to Self-Correct Reasoning*, arXiv:2404.17140.

---

## Revision log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-17 | Initial blueprint. |
| 1.2 | 2026-10-17 | Named **Kilter** (PyPI/GitHub cleared). AD-7 verdict states rewritten as IN KILTER / OUT OF KILTER / ESCALATE and promoted to a design surface in §5.7. Repo root and CLI renamed. Candidates rejected on clearance: Plimsoll, Plumb, Plumbline, Assize (all taken on PyPI — Assize reserved in an adjacent category), Crucible, Hallmark, Touchstone. Touchmark verified clear and held as a fallback. |
| 1.1 | 2026-10-17 | Window resolved (Phase 0 tonight, Day 1–3 Sun–Tue). Audience resolved as interviewer: added §5.7 presentation layer and §5.8 script/question sheet, dropped arm A2 from Phase 1, restructured Day 3 to launch the eval first and spend the day on polish. Added Day 0. No GPU confirmed — §6.3 local-critic ablation marked cuttable. §11 converted from open questions to resolved decisions. |

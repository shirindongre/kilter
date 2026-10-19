# Implementation decisions

Architectural decisions (AD-1..AD-10) live in `docs/blueprint.md` §3. This file holds implementation decisions.

## D-001 — Package nested under `src/kilter/` (2026-10-17)
Decision: Blueprint §9 shows `core/`, `graph/`, `defects/`, `eval/` at repo root. Implement them as subpackages of `src/kilter/` (`kilter.core`, `kilter.graph`, `kilter.defects`, `kilter.eval`). `config/`, `references/`, `results/`, `tests/`, `docs/` stay at repo root.
Why: Top-level packages named `core`/`graph`/`eval` would pollute site-packages and shadow stdlib/other names (`eval` is a builtin). `pip install -e .` and the `kilter` CLI need a single importable package.
Revisit if: never likely; purely structural, contents match §9.
Status: active

## D-002 — `kilter demo` CLI command replaces `make demo` as primary; Makefile also provided (2026-10-17)
Decision: Implement the cached demo as `kilter demo`. Ship a Makefile with `make demo` that calls it.
Why: Dev machine is Windows 11 with no `make`. Blueprint deliverable (§5.4) says `make demo`; the intent is a one-command offline deterministic demo. A CLI subcommand works everywhere.
Revisit if: owner wants `make` installed (e.g. via `choco install make`).
Status: active

## D-003 — Virtualenv at `.venv` (2026-10-17)
Decision: Use a project-local venv, not the global Python 3.11.9.
Why: RDKit / scikit-fingerprints / xgboost / langgraph bring heavy pins; avoid altering the global environment. Reproducible for run records (AD-10).
Revisit if: n/a
Status: active

## D-004 — Tracker is static HTML + `data.js` (2026-10-17)
Decision: `tracker/index.html` reads `window.KILTER_TRACKER` from `tracker/data.js`. No build step, no server, opens via double-click.
Why: "Simple and quick". `fetch()` of a JSON file fails on `file://`, so data is a JS file. Percentages are computed in the page from task statuses, so editing one status updates every number.
Revisit if: tracker needs live data (then serve locally).
Status: active

## D-005 — Blueprint stays at `docs/blueprint.md` (2026-10-17)
Decision: Do not move the blueprint to repo root as §9 draws it.
Why: Already placed by owner in `docs/`; CLAUDE.md links there.
Status: active

## D-006 — Reference analysis contract for injectors/checkers (2026-10-17)
Decision: Clean reference scripts in `references/<dataset>_clean.py` expose: module constants `DATASET`, `SPLIT`, `CLAIM`; `split_indices(smiles, split, seed)`; `run(dataset, split, n_seeds) -> dict` (so T1 can re-run the protocol under the alternative split, AD-9); train-only fit of a `Pipeline(VarianceThreshold, SelectKBest)` (D1 target); a 4-test Wilcoxon family corrected with `scipy.stats.false_discovery_control` (D4 target); a computed `conclusion` string (D5 target).
Why: AD-4 injectors are AST transforms; they need stable, recognisable sites. The BBBP reference (P1.1) must deliberately vary style (different model/featurisation) so the injector is not overfit to one script.
Revisit if: T0 checks prove brittle against stylistic variation (then widen the BBBP variants).
Status: active

## D-007 — Scaffold split uses `randomized_scaffold_train_test_split(random_state=seed)` (2026-10-17)
Decision: "scaffold" protocol in the reference = randomized scaffold split seeded per run, not the deterministic MoleculeNet scaffold split.
Why: The deterministic split gives zero variance across seeds, so §8.3's multi-seed requirement and the Wilcoxon family in D4 would be meaningless. REF-18 itself notes scaffold results are seed-sensitive.
Consequence: absolute scaffold AUROC will be higher than REF-16's 78.25% (deterministic split). Do not compare against REF-16's number directly; compare random-vs-scaffold deltas within this project.
Revisit if: owner wants a deterministic-scaffold arm for REF-16 comparison (cheap to add as a third split in the recorder).
Status: active

## D-008 — Three recorded split protocols: random, scaffold (randomized), scaffold_det (2026-10-17)
Decision: Reference `split_indices` supports `random`, `scaffold` (randomized, seed-varying; the stated SPLIT) and `scaffold_det` (deterministic MoleculeNet-style). The recorder reports all three. T1's D3 sensitivity check (AD-9) should quote random vs scaffold_det, because that is the contrast with real magnitude.
Why: Measured 2026-10-17 (BACE, ECFP4+RF, 10 seeds): random 0.893, randomized-scaffold 0.875 (gap +0.017), deterministic-scaffold 0.782 (gap +0.110). The deterministic number matches REF-16 (78.25%), validating the pipeline; the randomized split barely differs from random, so a metric-delta check alone could not detect D3 against it. T0 (static: split call contradicts CLAIM) carries D3 detection; T1 delta is supporting evidence, reported as sensitivity not as "wrong" (AD-9).
Revisit if: D3 detection on the injected set is poor.
Status: active (refines D-007)

## D-009 — T1 duplicate check: exact always a defect; near-duplicate only above 1% of test (2026-10-17)
Decision: T1 compares whole-molecule isomeric canonical SMILES (exact) and largest-fragment non-isomeric canonical SMILES (near). Exact overlap = DEFECT. Near-only overlap = DEFECT if >= 1% of the test set (`NEAR_DUP_THRESHOLD`), else a SENSITIVITY note (informational, does not change the verdict).
Why: first version flagged all 4 CLEAN BBBP variants. Cause: BBBP contains mixture/salt pairs (ampicillin vs ampicillin+sulbactam; theophylline vs aminophylline) that share a largest fragment but have different whole-molecule scaffolds, so the scaffold splitter separates them (2 of 414 test molecules = 0.5%). Real, but not a material leak, and it broke the 0-FP gate.
The 1% threshold is `[my judgment]`, not literature. The planted D2 is 10% of the test set, far above it, which is exactly the AD-4 caveat (injected defects may be easier than real ones). Phase 2: sweep the threshold, report the detection/FP trade-off.
Revisit if: real-world validation (Phase 3) shows material leaks below 1%.
Status: active

## D-010 — Kilter hook contract for runtime (T1) checks (2026-10-17)
Decision: T1 audits scripts that expose `run(dataset, split, n_seeds)`, `load_dataset`, `auroc_for(X, y, train_idx, test_idx, seed)` and optionally `featurize`. It stubs `auroc_for`/`featurize` (fast mode) and records the dataset and every train/test partition. A script without the hooks yields an INCONCLUSIVE finding -> ESCALATE, never a silent pass.
Why: a general tracer for arbitrary scripts is out of Phase 1 scope (AD-8, section 5.2). Executing the audited script is a trust decision (user's own code); sandboxing is Phase 2 (section 6.4).
State this in the README Limitations section: Phase 1 audits analyses that follow the hook contract.
Status: active

## D-011 — Injector/checker agreement caveat (2026-10-17)
Decision/caveat: injectors and T0 share name heuristics (`core/astutil.py`: train/test index naming, sklearn constructor list). Day 1 result of 32/32 detection and 0/8 false positives therefore partly measures agreement between two components written by the same author, on two references. It is not evidence the checks generalise to arbitrary scripts.
Mitigations in place: BBBP reference differs in style (model, scaler, naming, hand-written Holm, paired t-test); both D3 modes represented; benign configs; the BBBP duplicate false positive (D-009) was found by exactly this kind of cross-check.
Mitigations to do: a hand-written, differently-styled holdout script set before Phase 1 reporting; Phase 3 real-world set (AD-4). Must appear in README Limitations and in the interview answer to "how do you know these defects are realistic".
Status: active

## D-012 — Single provider (Google AI Studio); pinned gemini-3.6-flash by explicit name (2026-10-18)
Decision: Phase 1 uses Google AI Studio only. Cerebras requires payment (owner declined); Groq signup was down (optional, may be added later). Day 0 gate item "three providers reachable" is revised to "the pinned provider is reachable" by owner instruction ("proceed"). Pinned model: `gemini-3.6-flash`; fallback `gemini-3.1-flash-lite`.
Evidence (2026-10-18, this key): `gemini-2.5-flash` and `-lite` return 404 "no longer available to new users". `gemini-3.5-flash` reports `model_version = gemini-3.6-flash`, i.e. it is an alias; the 429 text confirms the quota is attributed to 3.6. `gemini-3.6-flash` free tier limit = 5 requests/minute (from the 429 error: generate_content_free_tier_requests, limit 5). `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` took 14 rapid calls with no 429. Hidden thinking tokens consumed max_output_tokens on 3.5-flash (reply truncated to 'kil'), so the client sets `thinking_level="minimal"` and counts thinking tokens as billed output.
Consequences: (1) AD-6 sharding mitigation is unavailable; at 5 RPM, ~150 critic calls take ~30 min, fine, but the DAILY limit (rpd) is unknown, read it at https://ai.dev/rate-limit (owner action). (2) Reported results must use model_reported from every record; a mismatch with the pin is a defect. (3) AD-6 "pin one provider+model" is satisfied trivially.
Revisit if: rpd blocks the 192-run eval -> switch to the fallback model for all arms (never mix models within a comparison).
Status: active

## D-013 — Executed artifacts: real runs, 6 seeds, content-addressed cache (2026-10-18)
Decision: T2 (and the A1 baseline) reason over the REAL output of running each variant (`run(n_seeds=6)`), not stubbed numbers. Cached at `results/artifacts/<sha16>-s6.json`, keyed by script hash. 6 seeds for every variant so an exact Wilcoxon can reach p<0.05 (n=5 cannot: min two-sided p = 0.0625).
Why: D5 is defined as "conclusion exceeds the computed numbers"; the critic needs genuine numbers. Injected D1/D2 variants then carry genuinely inflated metrics, as a real audit would see.
Cost: ~1 min x 48 variants, paid once, resumable (`scripts/build_artifacts.py`).
Note: the artifact seed count (6) can differ from the script's own default `n_seeds`; the artifact records which was used.
Status: active

## D-014 — D5 authored before any T2 prompt existed (2026-10-18)
The 8 D5 conclusions in `defects/d5_overclaim.py` were written in one sitting before the critic prompt, schema or any T2 output existed, per blueprint 5.5. Do not edit them after seeing T2 results; if one must change, append a revision here and report both versions.
Status: active

## D-015 — T2 prompt must not enumerate the authored D5 overclaim types (2026-10-18)
The critic's class list defines D5 only as "the written conclusion claims more than the computed numbers support". An earlier draft listed specific overclaim kinds (best-run reporting, readiness, mechanistic language, ...) that mirrored the hand-authored variants one-to-one; that would have leaked the answers and inflated T2 detection, the mirror image of the bias section 5.5 guards against (D-014). Removed before any T2 call was made.
Rule: the system prompt is frozen before the eval; any later edit is a new revision reported alongside the old one.
Status: active

## D-016 — D5 ground truth validated against real numbers, before any T2 output (2026-10-18)
Checked each D5 artifact: all 8 authored conclusions are contradicted or unsupported by the executed numbers (all adjusted p-values >= 0.11; best-seed 0.909 vs mean 0.865; bbbp-b2 claims ECFP4 beats every alternative while all three alternatives scored higher; bbbp-b0 calls AUROC 0.887 near-perfect). Labels stand.
Status: active

## D-017 — Re-pin to gemini-3.5-flash-lite; free-tier quota of gemini-3.6-flash is 20 requests/day (2026-10-18)
Decision: all reported results use `gemini-3.5-flash-lite`. `gemini-3.6-flash` is retired from the eval. Never mix models within or across arms of a comparison.
Evidence: during the first A3 run, request 10 returned 429 RESOURCE_EXHAUSTED: generate_content_free_tier_requests, limit 20, model gemini-3.6-flash, retry in 4h25m. A3 needs 48 calls, A1 about as many more, so the stronger model cannot run the eval on the free tier. The 9 critic calls already made are kept for the record in results/_stale/A3_gemini-3.6-flash_partial and fixtures/llm/ (keyed by model, so they are never served to the new pin).
Consequence (state in the writeup): a Flash-Lite critic is weaker than 3.6-flash, so T2's measured contribution is a LOWER bound for a stronger model. This also makes A3-vs-A4 a harsher, more honest test of AD-1.
AD-6 falsifier ("rate limits make a 150-run eval take more than one overnight") fired for the primary model; the mitigation taken is a model change, not provider sharding (only one provider exists, D-012).
Open: the rpd of gemini-3.5-flash-lite is unknown. If it also caps near 20/day, the eval needs a paid key or several days (Q-006).
Status: active

## D-018 â€” Holdout set: 8 subtle D5 + 8 honest-but-confident clean, pre-registered (2026-10-18)
Why: the main D5 set is lexically blatant and the main clean set shares one modest sentence (L-009 caveats 1-2). Holdout = `defects/holdout.py`, ids `*-H5` (class D5) and `*-HC` (clean), over the same 8 clean bases. Reported SEPARATELY from the main set, never pooled.
Pre-registration: authored after main-set results were known but before any T2/A1 call on these variants; T2 system prompt frozen (sha256 484e6bfe01faeb53587052d1baf95b5dedad9e599c1a7569d0c776b37d339058, stored in every run record).
Ground truth validated against executed numbers before any LLM call: all 8 HC texts are literally true (0 significant after correction in all 8; smallest adjusted p 0.11-0.89); all 8 H5 texts are unsupported. KNOWN CONTESTABLE LABEL: bace-b2-H5 ("shows that fingerprint models can predict inhibition for new chemical series") is borderline since a scaffold-held-out AUROC of 0.865 partly supports generalising to new scaffolds. Left unchanged; report results with and without it.
Status: active

## D-019 â€” A1 defined as same-conversation self-critique; token accounting; exploratory first-pass analysis (2026-10-18)
A1 = one LLM instance reviews the analysis (same restricted input as T2 minus the automated-check lines), then in the SAME conversation critiques its own review; the second response is the verdict. 2 calls per audit. A3 uses 1 call. Token budgets are therefore equal-or-lower for A3 (2.9k in / 176 out vs 5.6k in / 270 out); A0 and A4 report their unused budget as a saving (AD-3). The blueprint's A2 (separate critic, no tiers, no self-critique) was deferred; its closest available stand-in is A1's recorded first response, scored from fixtures (`eval/exploratory.py`) and labelled EXPLORATORY, not a pre-registered arm.
Finding (exploratory): first pass D1 5/8, D2 0/8, D3 4/8, D4 5/8, D5 7/8 (holdout 2/8), FP 0/8; after the self-critique turn D1 0, D3 0, D4 1, D5 2 (holdout 0). Self-critique removed correct findings (REF-7).
Status: active

## D-020 â€” Code hash covers the verifier only (2026-10-18)
`core.record.code_hash()` excludes analysis-only modules (`eval/metrics.py`, `eval/summarize.py`, `eval/figures.py`, `eval/exploratory.py`) that only read run records. Editing a plot or a table must not invalidate the provenance of 256 audits. Anything else under src/kilter is part of the verifier: after ANY such edit, rerun `scripts/run_eval.py` (about 10 min, offline) so every record shares one hash (M-004). Final pass: 1 hash, 1 model, 1 prompt hash across main and holdout.
Status: active

## D-021 â€” Eval reproducibility: one pass over recorded LLM responses (2026-10-18)
The reported tables come from `scripts/run_eval.py` replaying `fixtures/llm/` (temperature 0, one sample per audit). The live calls were made once, in record mode, while each arm was first run. Fresh-sample variance of the critic was NOT measured; state this wherever the numbers are quoted.
Status: active

## D-022 â€” Holdout 2: fresh beyond-the-data overclaims, authored before the scope prompt (2026-10-19)
Why: holdout 1 is training data for any prompt aimed at its misses (L-010), so a scope-claim prompt needs a fresh test. `defects/holdout2.py`, ids `*-B5` (class D5, 8) and `*-HC2` (clean, 8), same 8 clean bases, group "holdout2", never pooled with main or holdout 1.
BEYOND kinds (2 each): external comparison nobody ran, generalisation outside the dataset, mechanism asserted for an unvaried factor, benchmark label read as real-world outcome/readiness. Every text quotes true numbers next to the leap. HONEST: 8 decisive recommendation-bearing texts built from computed quantities; 4 carry no scope disclaimer.
Order of events: holdout2.py written 2026-10-19 BEFORE the new prompt existed and before any LLM call on these variants. Frozen prompt unchanged (sha256 484e6bfe...).
Status: active. Progress log: see session-log.md (step reached is recorded there).

## D-023 â€” Scope-claim prompt variant (t2_scope.py), evaluated on holdout 2 only (2026-10-19)
Decision: `core/tiers/t2_scope.py` holds `SYSTEM_SCOPE`, the frozen prompt with exactly three sentences replaced (D5 definition now "claims more than the executed analysis supports ... or asserts something the analysis never measured"; a rule to ask, for every statement beyond the numbers, what in the code/result/data card would have to be true for it to hold; the hedged-conclusion rule now says a firmly worded conclusion that stays within what was measured is NOT an issue). Not wired into the audit graph; A3 and all Phase 1 numbers still use the frozen prompt (sha256 484e6bfe...). Scope prompt sha256 f51f50d4... was changed once BEFORE any call ("or adopt" -> "or use", shared vocabulary with a holdout 2 text, M-003); the hash recorded in results is the final one (see results/holdout2_summary.json).
Result (gemini-3.5-flash-lite, temp 0, one call each, `scripts/run_holdout2.py`, results/holdout2*): beyond-the-data D5 frozen 4/8 (CI 16-84%), scope 7/8 (47-100%); honest-confident false positives 0/8 both (0-37%). Paired exact (McNemar): 3 only-scope vs 0 only-frozen, p = 0.25; FP discordant 0, p = 1.0. All 7 scope hits name the beyond-the-data statement (hand-checked). Miss: bace-b2-B5 (untested mechanism). No ESCALATE.
Reading: the scope prompt did not raise false positives (it was allowed to fail on that and did not), and detection rose from 4 to 7 of 8, but n = 8 cannot separate this from chance. Not claimed as closed. Needed to say anything firmer: a larger fresh set (>= 30 per arm), a second author for claims, repeated samples (fresh-sample variance unmeasured, D-021), and a stronger model as a check on the model ceiling.
Caveats: same author wrote holdout 2 and the prompt (though holdout 2 came first and the prompt was diffed against it); the frozen prompt scored 4/8 here vs 3/8 on holdout 1, so holdout 2 may be easier; two BEYOND texts (bace-b2, bbbp-b2) also contain a mild numeric over-read ("adds nothing"/"no benefit") besides the untested mechanism.
Code hash: new files under src/kilter changed the hash, so scripts/run_eval.py was rerun (offline replay) to keep one hash across all records.
Status: active

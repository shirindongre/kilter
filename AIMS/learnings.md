# Learnings

Non-obvious facts about the stack, data, and environment. Append as discovered.

## L-001 — Environment baseline (2026-10-17)
Windows 11, PowerShell, Python 3.11.9 global, git 2.52, no `make`. Global site-packages already has numpy 2.4, pandas 3.0, scikit-learn 1.9, scipy, matplotlib, rich, typer, PyYAML. Not installed: rdkit, scikit-fingerprints, deepchem, xgboost, langgraph, pytest. Directory was not a git repo at start.

## L-002 — scikit-fingerprints 2.1.0 has an undeclared dependency on `requests` (2026-10-17)
`import skfp.model_selection` fails with ModuleNotFoundError: requests on a clean venv. Added `requests` to pyproject dependencies. Dataset loaders (`skfp.datasets.moleculenet`) work without it and download from HuggingFace Hub, not MoleculeNet S3.

## L-003 — "Scaffold split" is not one protocol (2026-10-17)
BACE, ECFP4 + RandomForest, 512 SelectKBest features: random 0.893 | randomized-scaffold 0.875 | deterministic-scaffold 0.782 (std across 10 RF seeds is only 0.003 for the deterministic split, since the split itself has no randomness). Deterministic result reproduces REF-16 (BACE scaffold 78.25%). This is live evidence for AD-9 and REF-18: "scaffold split" without stating which one can move AUROC by ~9 points.

## L-004 — BBBP contains mixtures/salts that a scaffold split separates (2026-10-17)
2039 rows -> 1942 distinct largest-fragment canonical SMILES (97 near-duplicate rows). Examples: ampicillin vs ampicillin+sulbactam; theophylline vs theophylline+aminophylline. Whole-molecule Murcko scaffolds differ so scaffold splits place them on opposite sides (2/414 test molecules at seed 0). See D-009.

## L-005 — Reference results for later comparison (2026-10-17, 10 seeds)
BACE ECFP4+RF: random 0.893, randomized-scaffold 0.875, det-scaffold 0.782. BBBP count-ECFP4+XGBoost: random 0.911, randomized-scaffold 0.887, det-scaffold 0.837 (gap to random 0.074, smaller than BACE's 0.110). Files: results/reference_metrics_{bace,bbbp}.json.

## L-006 — Day 1 gate runtime (2026-10-17)
T0+T1 over all 40 variants: ~70 s with lru_cache on RDKit canonicalisation (153 s before). Gate test file takes ~90 s. T1 fast mode cost is dominated by importing skfp/xgboost and RDKit work, not model fitting.

## L-007 — Gemini free tier behaviour (2026-10-18)
Aliases redirect silently (3.5-flash -> 3.6-flash): always log `response.model_version`. Retired models 404 for new accounts. Thinking tokens are hidden, billed, and eat `max_output_tokens`: set `thinking_level` and budget for them. 429 text includes "Please retry in Ns" and the quota metric/limit: use it for backoff. `.env` is loaded by explicit path (`load_dotenv(ROOT/'.env')`); `find_dotenv()` fails in stdin scripts.

## L-008 — Provider 503 "high demand" happens on the free tier (2026-10-18)
The first A3 run died on a 503 UNAVAILABLE from Gemini. The client now retries 429/500/503/504 (429 using the server hint, 5xx with exponential backoff 10s, 20s, 40s...). Eval scripts must be resumable and must never convert a transport failure into a silent verdict.

## L-009 — Day 2 first results, with the caveats that go with them (2026-10-18)
Model: gemini-3.5-flash-lite (D-017). 48 variants (8 clean + 8 each of D1-D5), one T2 call per audit, 96 run records (A3, A4), one verifier code hash, T0/T1 outputs identical across arms 48/48.
A4 (T0+T1): D1-D4 32/32, D5 0/8, clean false positives 0/8. A3 (+T2): D1-D4 32/32, D5 8/8 (all attributed to T2, confidence 0.95-1.0), clean false positives 0/8, ESCALATE 0/48. Cost per A3 audit: ~2,900 input / ~180 output tokens, ~8 s.
So on this set: T2 adds nothing on D1-D4 (it largely echoes T0/T1, which it is shown) and everything on D5. That is the pattern section 5.8 Q4 predicts.
CAVEATS (must appear in README Limitations and the interview answer):
 1. The 8 D5 overclaims are lexically blatant ("proves", "replace the assay", "settled", "clearly superior"). 8/8 is an easy-case result; exact binomial 95% CI for 8/8 is [63%, 100%]. A subtle-overclaim holdout is needed before generalising.
 2. All 8 clean variants carry the same modest auto-generated conclusion, so 0/8 FP says little about honest-but-confident prose.
 3. T2 confidence saturates (0.95-1.0 everywhere): the abstention-calibration curve (section 8.2) is nearly degenerate. Report this rather than hide it. ESCALATE never fired.
 4. Injector/checker agreement (D-011) and the 1% near-duplicate threshold (D-009) still apply.
 5. A3 prompt includes the T0/T1 findings; the A2 ablation (critic alone) is deferred, so how much of T2's D1-D4 detections it would find unaided is unknown.
 6. Weaker critic than the original pin (D-017): T2's contribution here is a lower bound for stronger models.

## L-010 — Holdout result: T2 checks claims against the numbers, not claims beyond the data (2026-10-18)
Holdout (D-018), gemini-3.5-flash-lite, frozen prompt: subtle D5 3/8 detected (A4: 0/8), honest-but-confident clean 0/8 false positives (A4: 0/8).
Caught: bace-b0 (better-on-average preferred, adj p 0.375), bace-b1 (differs, raw p 0.156), bbbp-b2 ("meaningful" +0.003, adj p 0.888): overclaims about significance/effect size, directly checkable against printed p-values.
Missed (zero findings, no low-confidence note, no ESCALATE): bace-b2 (generalises to new chemical series; the contestable label), bace-b3 (fabricated 0.80 benchmark), bbbp-b0 (untested mechanism), bbbp-b1 (right default for all BBB models), bbbp-b3 (ready for external libraries).
Reading: T2 verifies numeric consistency; it does not police scope, causal, external-benchmark or readiness claims. The frozen prompt's wording ("compare every quantitative or comparative statement ... with the numbers"; "judge only what the code, results and data card show") plausibly steers it there: that is a prompt effect, not necessarily a model ceiling. Do NOT tune the prompt on this holdout (it would become training data); a prompt variant for scope claims needs a fresh holdout (Phase 2).
Consequence for the headline: "T2 detects overclaims" is true for 8/8 blatant and 3/8 subtle; honest summary = T2 adds real, class-specific value over T0+T1, not general overclaim detection.

## L-011 — A scope-aware prompt moves detection of beyond-the-data overclaims, not provably (2026-10-19)
Holdout 2 (fresh, D-022): frozen prompt 4/8, scope prompt 7/8, honest-confident FP 0/8 for both, paired p = 0.25. L-010's reading ("a prompt effect, not necessarily a model ceiling") is supported in direction: with the same model the rewritten rules caught generalisation, external-comparison, real-world-outcome and readiness claims that the numeric-consistency framing let through, and did not start flagging firmly worded honest conclusions. Weak spot: a mechanism asserted for an unvaried factor, when next to a near-null result, can still read as an interpretation of the numbers (1 miss for scope, 2 for frozen on mechanism).
The frozen prompt is not as blind to scope as holdout 1 suggested (4/8 on a fresh set, incl. readiness and generalisation). Holdout-to-holdout variation at n=8 is about as large as the effect; do not quote either 3/8 or 4/8 as "the" rate.
Confidence still saturates (0.90-1.00 on every finding; no ESCALATE), so the abstention curve stays uninformative.

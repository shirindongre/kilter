# Session log

## 2026-10-17 — Session 1 (Day 0 start)
- Created CLAUDE.md, AIMS memory system, visual tracker (tracker/index.html + data.js).
- Scaffolded repo per blueprint §9 (nested under src/kilter, D-001); venv; installed rdkit, scikit-fingerprints, xgboost, pytest.
- Loaded BACE + BBBP via scikit-fingerprints (HuggingFace Hub source).
- Wrote clean BACE reference analysis and metrics recorder; discovered scaffold-protocol ambiguity (L-003, D-008).
- Mistakes: M-001 (assumed `skfp.__version__`).
- Blocked: P0.2/P0.3 await owner's API keys.

## 2026-10-17/18 — Session 1 continued (Day 1)
- Owner approved starting Day 1 while provider keys pending (Q-004).
- Built Finding/AuditResult model, BBBP reference (different style), T0 (leakage, split protocol, multiple comparisons), four injectors, variant builder (8 clean + 32 defective), T1 (duplicates, scaffold overlap, optional split sensitivity), audit CLI, scoring helpers.
- Found and fixed a real false positive: clean BBBP flagged D2 because the dataset has mixture/salt near-duplicates (D-009, L-004).
- Day 1 gate test passes: 32/32, 0 FP. 29 tests green.
- Mistakes: M-002 (escape sequences through heredoc-written code).
- Still blocked: P0.2/P0.3 (keys). Day 2 not started, by instruction.

## 2026-10-18 — Session 1 continued (Day 0 close-out and Day 2)
- Owner supplied a Google key (Cerebras paid, Groq down): Day 0 gate revised to one provider (D-012). Probed models and limits: aliases redirect, 3.6-flash is 5 RPM / 20 RPD, so re-pinned to gemini-3.5-flash-lite (D-017).
- Authored 8 D5 variants before any T2 code (D-014); validated ground truth against real numbers (D-016).
- Built: llm.py with fixtures, run records, T2 critic, adjudicator, LangGraph pipeline, artifact cache, arm runner.
- Ran A4 and A3 over 48 variants. 42 tests pass. Mistakes M-003 (caught prompt leakage), M-004 (code changed between arms).
- Day 3 not started.

## 2026-10-18 — Session 1 continued (holdout and Day 3)
- Authored and pre-registered a 16-variant holdout (D-018); validated labels against real numbers; found T2 catches 3/8 subtle overclaims (L-010).
- Built A0/A1 arms, metrics with exact CIs, exploratory critic-alone decomposition, verdict screen + report.md, cached `kilter demo` (identical x3), three figures (redesigned fig 2 after viewing it), README with Limitations, docs/TALK.md.
- One final evaluation pass: 256 records, 1 code hash. 48 tests pass offline.
- Mistakes: M-002 recurred twice more (heredoc-python with escapes). Caught: A1-turn-1 vs A1 contrast reveals self-critique harm.
- Remaining and human-only: 90 s screen recording, timed rehearsal.

## 2026-10-19 — Phase 2 scope-claim prompt experiment (side session)
Step reached: holdout2.py authored, generate_holdout2() added, build_artifacts.py accepts `holdout2` (artifacts building). NEXT: tests/test_holdout2.py (validate vs numbers), then t2_scope.py prompt variant + hash, scripts/run_holdout2.py (both prompts, record mode), stats, rerun scripts/run_eval.py (code hash changed), README + AIMS outcome.
Progress 2: tests/test_holdout2.py, src/kilter/core/tiers/t2_scope.py (scope prompt; sha256 recorded at runtime as t2_scope.PROMPT_SHA256) and scripts/run_holdout2.py written. NEXT: wait for holdout2 artifacts (results/_art_holdout2.log), run test_holdout2, then `python scripts/run_holdout2.py` (record mode, resumable), then scripts/run_eval.py, README/AIMS.
Progress 3: holdout2 artifacts built (results/_art_holdout2.log), test_holdout2 passes: ground truth validated vs executed numbers BEFORE any LLM call. NEXT: python scripts/run_holdout2.py
Progress 4: scripts/run_holdout2.py DONE (results/holdout2_summary.json, results/holdout2/). frozen 4/8 detect, scope 7/8, FP 0/8 both, paired p=0.25. NEXT: scripts/run_eval.py (single code hash), full replay pytest, README Limitations + AIMS (decisions D-023, learnings L-011, context).
Progress 5: README (Phase 2 section + Limitations), D-023, L-011 written. Waiting only on scripts/run_eval.py (results/_eval.log) and full replay pytest; then rewrite AIMS/context.md and tracker/data.js if it lists Phase 2.
Progress 6 (DONE): run_eval rerun (1 hash), replay pytest 53 pass, context.md/tracker updated. Task complete; open follow-ups: larger fresh set, second author, repeated samples, stronger model.

## 2026-10-23 - Fleet view, results inspection, Phase 1 close-out
- Inspected the evaluation's results folder (extracted one level too deep at results/results/; moved up). 256 run records (runs/{A0,A1,A3,A4}[_holdout]) all pass record.verify(); one code hash fdd74ae7... across them and the 32 holdout 2 rows. results/_scratch_runs and _stale hold older records with other hashes (superseded, ignored); holdout 2's 16 A4 records live in _scratch_runs.
- Found: the checkout hashes to 3d833fee..., not fdd74ae7... (D-025, unresolved). Found: Python 3.12 regenerates 16 of 80 variants with different bytes (L-012); registry now prefers results/variants, artifact_ready 83/83.
- Built web/fleet.py, adapter.stored_cell/view_from_stored, /api/fleet, #/fleet screen, offline fleet.json, 6 new tests. Full pytest (KILTER_LLM_MODE unset): 67 passed, 1 skipped.
- Cross-checked every number in README and docs/TALK.md against summary.json, holdout2_summary.json and the records: all agree (no mismatch). Fleet reconciles 28 counts with the summaries.
- Phase 1 close-out: .gitignore un-ignores small evidence files, .gitattributes for variants, docs/RECORDING.md (90 s script, rehearsal), Q-003/Q-005 answered, Q-001/Q-006 left to the owner, D-025, L-012.
- Not done: the recording and the timed rehearsal (owner); nothing is committed; `python web/server.py --live` and the split-sensitivity checkbox were not exercised.

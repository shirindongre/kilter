# Current context (rewrite every session)

**Last updated:** 2026-10-23 (fleet view committed 4809a97; code-hash mismatch resolved, D-027; --live and split sensitivity exercised, D-026)
**Phase:** Phase 1 complete except two items only the owner can do (90 s recording, timed rehearsal). Phase 2: scope-prompt experiment (D-022, D-023) and local web UI with fleet view (D-024, D-025) done.

## Phase 1 exit gate (blueprint 5.6)
| Item | Status |
|---|---|
| T0+T1 >= 80% on D1-D4, FPR <= 5% on clean | PASS: 32/32 and 0/8 (FPR upper bound 37%, n=8; the point estimate meets the gate, the interval does not prove FPR <= 5%) |
| Full 4-arm eval with cost logging | DONE: A0/A1/A3/A4 on 48 main + 16 holdout, 256 records, one code hash (fdd74ae7...) |
| Does T2 add anything over T0+T1, at what token cost? | YES on D5 only: 8/8 vs 0/8 (p=0.008) at 2.9k in / 176 out tokens per audit; nothing on D1-D4. Holdout (subtle overclaims): 3/8 vs 0/8, p=0.25 (n.s.) |
| `kilter demo` clean, offline, 3x without variance | PASS: byte-identical x3 (tests/test_demo.py) |
| 90 s recording fallback exists | OWNER: script in docs/RECORDING.md |
| Rehearsed docs/TALK.md once, timed | OWNER: protocol in docs/RECORDING.md |

## Headline (always with caveats; README Limitations, L-009/L-010)
A3 40/40 (91-100%), A4 32/40 (64-91%), A1 3/40 (2-20%) at 1.9x A3's tokens; FP 0/8 each. Holdout A3 3/8. Holdout 2: frozen prompt 4/8, scope prompt 7/8, paired p=0.25. Critic confidence saturates (0.95-1.00); ESCALATE never fired. All of these were re-checked against results/ on 2026-10-23 and agree with README and docs/TALK.md.

## Open problems (read these first)
- Code hash: RESOLVED (D-027). Records say fdd74ae7...; this checkout hashes to 3d833fee... only because 21 files are CRLF here and LF on the evaluation machine; every other byte is identical (verified per file, and the hash rebuilt with their endings matches). The hash is line-ending sensitive (L-013). Owner decision: normalise it in code_hash() and rerun the evaluation, or leave it and state the caveat.
- Python: the evaluation ran on 3.11.9, the venv here is 3.12.6; generated variants differ in 16 files (L-012). web/registry.py uses results/variants to stay byte-exact.
- Verified on this machine 2026-10-23 (replay mode, datasets cached): `web/build_fixtures.py` writes 6 runs + fleet.json; demo D1 is OUT OF KILTER held at T0, demo D5 is held at T2 as a query, demo A4 on D5 misses; the demo artifacts matched; `web/server.py` serves all screens; a replay A3 audit of bace-b0-H5 reproduces the stored verdict and tokens.
- Verified 2026-10-23: `--live` serves recorded samples without an API call and fails cleanly with no key; the split-sensitivity option works (API and UI) and never changes a verdict.
- Not verified: a real live API call (no key on this machine), a Linux checkout (the demo artifacts are keyed to CRLF bytes, D-024).

## What exists
src/kilter (core, graph, defects, eval), references/, fixtures/ (llm + artifacts), demo/, results/ (local; small evidence files now un-ignored, D-025), README.md, docs/{blueprint.md,TALK.md,RECORDING.md,frontend/}, tests (67 pass, 1 skipped), tracker, web/ (UI: Audit, Samples, Fleet, History).

## Git
Committed as 4809a97. Later edits (D-026) are separate. Never commit: results.zip, web/work, web/runs, the demo video.

## Open
- Owner: recording, rehearsal, Q-001 (format), Q-006 (flash-lite rpd).
- Do not edit src/kilter without rerunning scripts/run_eval.py (D-020). Do not edit the frozen critic prompt (D-015, hash 484e6bfe...).
- Phase 2 candidates: real-world held-out set; A2 + critic-sees-context ablation; scope prompt on a larger fresh set with a second author; scRNA-seq track.

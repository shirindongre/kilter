# Current context (rewrite every session)

**Last updated:** 2026-10-19 (Phase 2 scope-claim prompt experiment done; human-only items remain)
**Phase:** Phase 1 complete except two items only the owner can do. Day 0 (revised), Day 1, Day 2 gates passed.

## Phase 1 exit gate (blueprint 5.6)
| Item | Status |
|---|---|
| T0+T1 >= 80% on D1-D4, FPR <= 5% on clean | PASS: 32/32 and 0/8 (FPR upper bound 37%, n=8; the point estimate meets the gate, the interval does not prove FPR <= 5%) |
| Full 4-arm eval with cost logging | DONE: A0/A1/A3/A4 on 48 main + 16 holdout, 256 records, one code hash |
| Answer: does T2 add anything over T0+T1, at what token cost? | YES on D5 only: 8/8 vs 0/8 (p=0.008) at 2.9k in / 176 out tokens per audit; on D1-D4 nothing. Holdout (subtle overclaims): 3/8 vs 0/8, p=0.25 (n.s.) |
| `kilter demo` clean, offline, 3x without variance | PASS: byte-identical x3 (tests/test_demo.py) |
| 90 s recording fallback exists | **OWNER**: record `kilter demo` on laptop and phone |
| Rehearsed docs/TALK.md once, timed | **OWNER** |

## Headline (always with caveats; README Limitations and L-009/L-010)
A3 40/40 (91-100%), A4 32/40 (64-91%), A1 3/40 (2-20%) at 1.9x A3's tokens; FP 0/8 each. Holdout A3 3/8. Critic confidence saturates (0.95-1.00); ESCALATE never fired.

## What exists
Everything under src/kilter (core, graph, defects, eval), references/, fixtures/ (llm + artifacts), demo/, results/{summary.json,phase1.json,results_table.md,figures/}, README.md, docs/{blueprint.md,TALK.md}, tests (48 passing, `KILTER_LLM_MODE=replay` for offline), tracker.

## Phase 2 result (D-022, D-023, L-011)
Fresh holdout 2 (src/kilter/defects/holdout2.py, 8 beyond-the-data + 8 honest-confident; results/holdout2*): frozen prompt 4/8, scope prompt (core/tiers/t2_scope.py, NOT wired into A3) 7/8, honest-confident FP 0/8 both, paired exact p = 0.25. Gap narrowed in the data, not proven closed at n = 8. 53 tests pass (KILTER_LLM_MODE=replay); run_eval rerun, 256 records + holdout2 share one code hash.

## Open
- Owner: recording and rehearsal. Also read Google rpd for flash-lite from https://ai.dev/rate-limit (Q-006), git init (Q-003), presentation format (Q-001).
- Phase 2 candidates, in order: real-world held-out set; A2 + critic-sees-context ablation; a scope-claim prompt tested on a FRESH holdout; scRNA-seq track.
- Do not edit src/kilter without rerunning scripts/run_eval.py (D-020). Do not edit the frozen critic prompt (D-015, hash 484e6bfe...).

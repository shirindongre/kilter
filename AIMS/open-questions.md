# Open questions for the owner

## Q-001 — Presentation date and format (from blueprint §11 "Still open")
Live screen-share vs in-person laptop? If screen-share, test on the actual call software before Tuesday. Changes nothing structural.
Status: open

## Q-002 — Provider API keys (blocks P0.2, P0.3)
Google AI Studio, Groq, Cerebras keys must be created by the owner. Keys go in `.env` (never chat). Current console rate limits must be copied into `config/providers.yaml` by the owner (or read to me from the console) with today's date.
Status: PARTLY ANSWERED 2026-10-18 — Google key supplied and working; Cerebras dropped (paid); Groq down. See D-012. Still open: Google daily limit (rpd) from https://ai.dev/rate-limit.

## Q-003 — Git (2026-10-17)
Directory is not a git repo. Initialise one (recommended; AD-10 provenance records a code hash)?
Status: open

## Q-004 — Start Day 1 before the Day 0 provider gate passes? (2026-10-17)
Day 0 gate (§5.3) requires 3 providers reachable; keys are owner-supplied. Day 1 (injectors, T0, T1) uses no LLM, so it is technically unblocked. Blueprint §0 rule 3 says gates are not suggestions. Recommendation: proceed with Day 1 now, keep P0.2/P0.3 open on the tracker, and do not start Day 2 until they pass.
Status: ANSWERED 2026-10-17 — owner said start Day 1; keys supplied separately; Day 2 must wait for P0.2/P0.3.

## Q-005 — Blueprint N arithmetic (2026-10-17)
§5.1 says N=40 (8 clean, 32 defective, "8 per injectable class, D5 hand-authored"). 4 injectable classes x 8 = 32, plus 8 hand-authored D5 = 40 defective, so 8 clean + 40 = 48 total (192 runs, not 160). Default taken: 8 clean + 8 per class D1-D5 = 48. Decide before Day 2 D5 authoring whether to keep 48 or drop to 6-7 per class to hold 40.
Status: open (non-blocking for Day 1)

## Q-006 — Google rpd (requests per day) for gemini-3.6-flash (2026-10-18)
Needed for AD-6. Not exposed by the API; read it at https://ai.dev/rate-limit and put it in config/providers.yaml. If low (e.g. under ~200), switch the whole eval to the fallback model.
Status: open

## Q-006 update (2026-10-18)
gemini-3.6-flash free tier = 20 requests/day, exhausted. Re-pinned to gemini-3.5-flash-lite (D-017). Its daily cap is unknown; if A3 stops on a 429 the log will say so.

## Q-003 update (2026-10-23)
A git repository exists (HEAD 15b3ff9 "Initial commit: Kilter Phase 1"). Answered. One caveat is in D-025: the code hash in the evaluation records (fdd74ae7...) does not match this checkout's src/kilter (3d833fee...); a commit does not by itself make the records reproducible.
Status: ANSWERED 2026-10-23

## Q-005 update (2026-10-23)
The evaluation ran with 48 main variants (8 clean + 8 per class D1-D5; 192 main-set runs across A0/A1/A3/A4), plus 16 holdout and 16 holdout 2. Confirmed from results/runs: 48 records per arm. The N=40 in blueprint 5.1 counts defective variants only. Answered.
Status: ANSWERED 2026-10-23

## Q-006 update (2026-10-23)
Still open for the owner: the flash-lite daily cap is not in any file. What the results do show: no 429 or quota error in results/_a3.log, _a3_hold.log, _a1.log, _eval.log or _holdout2_run.log, and holdout 2's 32 critic calls needed 2 retries in total. Read the real limit at https://ai.dev/rate-limit and put it in config/providers.yaml with the date.
Status: open (owner)

## Q-001 update (2026-10-23)
Still open (owner). docs/RECORDING.md says what each answer changes: screen-share needs the 90 s recording and a call-software test, in-person needs the phone copy.
Status: open (owner)

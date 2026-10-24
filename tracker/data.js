// Single source of truth for the tracker. Edit task `status` only: done | active | blocked | todo.
// Percentages, columns, overdue badges and feature-map colours are all derived in index.html.
// `owner: "you"` marks work only the project owner can do (shown as a YOU tag).
// Evidence numbers are copied from results/summary.json and results/holdout2_summary.json (code hash 8eef0f35…).
window.KILTER_TRACKER = {
  updated: "2026-10-24",
  phases: [
    { id: "d0", name: "Day 0 · Setup", when: "Sat 17 Oct, 23:00", due: "2026-10-17", gate: "pytest green · pinned provider reachable (Google only, D-012) · both datasets load · clean analysis has recorded metrics" },
    { id: "d1", name: "Day 1 · Sound verifier", when: "Sun 18 Oct", due: "2026-10-18", gate: "T0+T1 catch ≥80% of injected D1–D4, 0 false positives on 8 clean variants — no LLM called" },
    { id: "d2", name: "Day 2 · Agent layer", when: "Mon 19 Oct", due: "2026-10-19", gate: "Full pipeline runs on all 48 variants, one arm, complete run records, demo fixtures captured" },
    { id: "d3", name: "Day 3 · Measure & polish", when: "Tue 20 Oct", due: "2026-10-20", gate: "4 arms × 48 done · `kilter demo` clean ×3 · recording exists · §5.8 rehearsed" },
    { id: "p2", name: "Phase 2 · Web UI & reproducibility", when: "Fri 23 Oct", due: "2026-10-23", gate: "UI reads the run record and never decides a verdict · the evaluation reproduces on the source-of-truth machine · tests pass" },
    { id: "p3", name: "Next · not scheduled", when: "after the talk", gate: "Real-world held-out set tested, expecting the rate to drop (AD-4)" }
  ],
  tasks: [
    // Day 0
    { id: "P0.1", phase: "d0", title: "Repo scaffold, venv, `pip install -e .`, pytest runs", status: "done", ref: "§5.3" },
    { id: "P0.2", phase: "d0", title: "Provider config + record real rate limits", status: "done", note: "Google only (D-012); flash-lite rpd still unknown (Q-006)", ref: "AD-6" },
    { id: "P0.3", phase: "d0", title: "Hello smoke test through the pinned provider", status: "done", ref: "§5.3" },
    { id: "P0.4", phase: "d0", title: "Install RDKit/scikit-fingerprints; BACE + BBBP load", status: "done", ref: "§5.1" },
    { id: "P0.5", phase: "d0", title: "Clean BACE reference analysis; random + scaffold metrics recorded", status: "done", ref: "AD-9, REF-16" },
    // Day 1
    { id: "P1.1", phase: "d1", title: "Second reference analysis on BBBP", status: "done", ref: "§5.3" },
    { id: "P1.2", phase: "d1", title: "Finding / Verdict data structure", status: "done", ref: "AD-7, §5.7" },
    { id: "P1.3", phase: "d1", title: "Injector D1 · preprocessing leakage", status: "done", ref: "§4" },
    { id: "P1.4", phase: "d1", title: "Injector D2 · duplicate molecules across split", status: "done", ref: "§4" },
    { id: "P1.5", phase: "d1", title: "Injector D3 · split protocol unstated / random", status: "done", ref: "§4, AD-9" },
    { id: "P1.6", phase: "d1", title: "Injector D4 · multiple-comparison correction omitted", status: "done", ref: "§4" },
    { id: "P1.7", phase: "d1", title: "T0 static checks (AST)", status: "done", ref: "AD-1" },
    { id: "P1.8", phase: "d1", title: "T1 runtime assertions", status: "done", ref: "AD-1" },
    { id: "P1.9", phase: "d1", title: "GATE · ≥80% detection, 0 FP on clean variants", status: "done", note: "32/32 and 0/8. The FPR upper bound is 37% at n=8, so the gate is met by the point estimate only.", ref: "§5.6" },
    // Day 2
    { id: "P2.1", phase: "d2", title: "LangGraph pipeline Loader→T0→T1→T2→Adjudicator→Report", status: "done", ref: "AD-5 (6h cap)" },
    { id: "P2.2", phase: "d2", title: "T2 critic prompt + schema, restricted input", status: "done", ref: "AD-2" },
    { id: "P2.3", phase: "d2", title: "Adjudicator (IN KILTER / OUT OF KILTER / ESCALATE)", status: "done", ref: "AD-7" },
    { id: "P2.4", phase: "d2", title: "Token/cost/latency logging + signed run records", status: "done", ref: "AD-3, AD-10" },
    { id: "P2.5", phase: "d2", title: "Author 8 D5 overclaim variants (done before any T2 prompt)", status: "done", ref: "§5.5" },
    { id: "P2.6", phase: "d2", title: "Capture LLM response fixtures for the demo", status: "done", ref: "§5.7" },
    { id: "P2.7", phase: "d2", title: "GATE · pipeline runs all 48 variants end-to-end", status: "done", ref: "§5.3" },
    // Day 3
    { id: "P3.1", phase: "d3", title: "Run 4 arms on 48 main + 16 holdout variants", status: "done", ref: "§8.1" },
    { id: "P3.2", phase: "d3", title: "Verdict screen + report.md emitter", status: "done", ref: "§5.7" },
    { id: "P3.3", phase: "d3", title: "Metrics: detection, FPR, abstention, cost, exact binomial CIs", status: "done", note: "Abstention curve is degenerate: critic confidence is 0.90–1.00 everywhere and ESCALATE never fired (see P5.9)", ref: "§8.2–8.3" },
    { id: "P3.4", phase: "d3", title: "Three figures", status: "done", ref: "§5.3" },
    { id: "P3.5", phase: "d3", title: "`kilter demo` cached path + 90s recording", status: "blocked", owner: "you", note: "kilter demo is done and tested (identical x3, offline). Needs YOUR 90 s screen recording, laptop + phone. Script: docs/RECORDING.md", ref: "§5.7" },
    { id: "P3.6", phase: "d3", title: "README (headline + baseline + Limitations)", status: "done", ref: "§5.7" },
    { id: "P3.7", phase: "d3", title: "5-min script + question sheet, rehearsed once", status: "blocked", owner: "you", note: "Script and Q&A written (docs/TALK.md). Needs YOUR timed out-loud rehearsal. Protocol: docs/RECORDING.md", ref: "§5.8" },
    // Phase 2
    { id: "P4.1", phase: "p2", title: "Scope-claim critic prompt tested on a fresh holdout (7/8 vs 4/8, p = 0.25, not proven)", status: "done", ref: "D-022, D-023" },
    { id: "P4.2", phase: "p2", title: "Local web UI: audit, samples, history (web/, outside src/kilter)", status: "done", ref: "D-024" },
    { id: "P4.3", phase: "p2", title: "Fleet view: 80 variants, both arms, confusion by class, counts reconciled with the summaries", status: "done", ref: "D-025" },
    { id: "P4.4", phase: "p2", title: "README and TALK numbers re-checked against results/ (no mismatch)", status: "done", note: "Spot-checked again on 24 Oct: results/summary.json gives A0 0/40, A1 3/40, A3 40/40, A4 32/40, holdout A3 3/8, matching results_table.md and docs/TALK.md.", ref: "D-025" },
    { id: "P4.5", phase: "p2", title: "Code hash ignores line endings; evaluation rerun on this machine, one hash, same results", status: "done", ref: "D-028, D-029" },
    { id: "P4.6", phase: "p2", title: "--live (recorded scripts, no-key failure) and split sensitivity exercised; no real API call made", status: "done", ref: "D-026" },
    { id: "P4.7", phase: "p2", title: "Commit the D-028/D-029 changes (code_hash, eval scripts, rerun results, docs)", status: "active", note: "Records carry hash 8eef0f35…, which matches no commit yet: HEAD is cd0f8cd (23 Oct 15:07 IST), older than the edit to core/record.py. Confirmed by git status on 24 Oct (ahead 2): modified core/record.py, tests/test_record_pipeline.py, scripts/{build_artifacts,run_arm,run_eval,run_holdout2}.py, web/static/js/screens/fleet.js, README, AIMS/*, results summaries, tracker. scripts/evalutil.py is new and untracked.", ref: "git" },
    { id: "P4.8", phase: "p2", title: "Q-001: screen-share or in person (decides what the recording must cover)", status: "blocked", owner: "you", note: "Needs YOUR answer", ref: "Q-001" },
    { id: "P4.9", phase: "p2", title: "Q-006: read the flash-lite daily limit from ai.dev/rate-limit into config/providers.yaml", status: "blocked", owner: "you", note: "Needs YOU: the console is the only source (AD-6). providers.yaml still has rpd: null.", ref: "Q-006" },
    { id: "P4.10", phase: "p2", title: "Run the full test suite after D-028/D-029", status: "done", note: "24 Oct: 68 passed, 1 skipped in 4m09s on this machine, after the code_hash change (pytest -q, replay mode, KILTER_LLM_MODE unset).", ref: "D-028" },
    { id: "P4.11", phase: "p2", title: "Push the commits to origin (shirindongre/kilter)", status: "todo", owner: "you", note: "No remote-tracking update has been recorded since the clone, so 4809a97 and cd0f8cd look local-only. Confirm with `git status -sb`.", ref: "git" },
    { id: "P4.12", phase: "p2", title: "Fix doc drift: README says \"40+ tests\" (suite is 67+); CLAUDE.md scope says 40 variants (evaluation is 48 + 16 + 16)", status: "todo", ref: "README, CLAUDE.md" },
    // Next
    { id: "P5.1", phase: "p3", title: "Real-world held-out set of corrected analyses (the one test of AD-4)", status: "todo", note: "Kill criterion §10: detection under 20% of Phase 1 means the product is a linter, not an agent.", ref: "AD-4" },
    { id: "P5.2", phase: "p3", title: "Rebuild the executed artifacts here (about 30 min) so the numbers are shown to reproduce on this setup", status: "todo", ref: "D-029" },
    { id: "P5.3", phase: "p3", title: "Arm A2 (critic alone) and the critic-sees-context ablation", status: "todo", note: "The thesis says \"vs an LLM critic alone at matched budget\"; only the exploratory first-pass row (21/40) stands in for A2 today.", ref: "AD-2" },
    { id: "P5.4", phase: "p3", title: "Scope prompt on a larger fresh set (30+ per class), claims written by a second person", status: "todo", ref: "D-023" },
    { id: "P5.5", phase: "p3", title: "Run-to-run variance of fresh critic calls (never measured)", status: "todo", note: "Every T2 number is one recorded sample per variant; reruns replay it.", ref: "README limits" },
    { id: "P5.6", phase: "p3", title: "Check a Linux/LF checkout: demo artifacts are keyed to CRLF bytes", status: "todo", ref: "D-024" },
    { id: "P5.7", phase: "p3", title: "scRNA-seq track: D6 double dipping, D7 cell-level splitting, D8 batch confound", status: "todo", ref: "blueprint §4" },
    { id: "P5.8", phase: "p3", title: "Independent check of D1–D4: someone else plants defects by hand and T0/T1 runs on them", status: "todo", note: "Injector and checker were written by one author and share naming heuristics (D-011), so 32/32 is partly self-agreement.", ref: "TALK Q2" },
    { id: "P5.9", phase: "p3", title: "Exercise the ESCALATE path on real data: a case where the critic should abstain", status: "todo", note: "ESCALATE fired 0 of 48 main-set audits; AD-7 calls abstention calibration a reported metric.", ref: "AD-7, L-009" }
  ],
  // Feature map: status is derived from the linked tasks.
  features: [
    { group: "Verification tiers", items: [
      { name: "T0 static (AST)", tasks: ["P1.7"] },
      { name: "T1 runtime", tasks: ["P1.8"] },
      { name: "T2 LLM critic", tasks: ["P2.2"] },
      { name: "Adjudicator", tasks: ["P2.3"] }
    ]},
    { group: "Defect injectors", items: [
      { name: "D1 leakage", tasks: ["P1.3"] },
      { name: "D2 duplicates", tasks: ["P1.4"] },
      { name: "D3 split protocol", tasks: ["P1.5"] },
      { name: "D4 multiple comparisons", tasks: ["P1.6"] },
      { name: "D5 overclaim (hand-authored)", tasks: ["P2.5"] }
    ]},
    { group: "Foundation", items: [
      { name: "Scaffold & env", tasks: ["P0.1"] },
      { name: "Providers", tasks: ["P0.2", "P0.3"] },
      { name: "Datasets", tasks: ["P0.4"] },
      { name: "Reference analyses", tasks: ["P0.5", "P1.1"] },
      { name: "Finding / Verdict model", tasks: ["P1.2"] },
      { name: "Run records", tasks: ["P2.4"] }
    ]},
    { group: "Pipeline & evaluation", items: [
      { name: "LangGraph pipeline", tasks: ["P2.1"] },
      { name: "Eval arms A0·A1·A3·A4", tasks: ["P3.1"] },
      { name: "Metrics & CIs", tasks: ["P3.3"] },
      { name: "Figures", tasks: ["P3.4"] }
    ]},
    { group: "Phase 2", items: [
      { name: "Scope prompt (holdout 2)", tasks: ["P4.1"] },
      { name: "Web UI", tasks: ["P4.2", "P4.6"] },
      { name: "Fleet view", tasks: ["P4.3"] },
      { name: "Reproducible evaluation", tasks: ["P4.5", "P4.7", "P4.10"] },
      { name: "Numbers checked", tasks: ["P4.4"] }
    ]},
    { group: "Presentation", items: [
      { name: "Verdict screen & report.md", tasks: ["P3.2"] },
      { name: "Cached demo", tasks: ["P2.6", "P3.5"] },
      { name: "README", tasks: ["P3.6"] },
      { name: "Script & Q&A sheet", tasks: ["P3.7"] }
    ]}
  ],
  // Suggested order for the next sitting. Everything before the recording is small and unblocks the rest.
  next: [
    "Commit and push (P4.7, P4.11), so hash 8eef0f35… maps to a commit and the results are not on one laptop only. Tests are green (P4.10: 68 passed, 1 skipped).",
    "Answer Q-001 and read the rate limit for Q-006 (P4.8, P4.9). Both are a few minutes and Q-001 decides what the recording must cover.",
    "Record the 90 s demo, laptop and phone (P3.5), then rehearse the 5 minutes out loud with a clock (P3.7). This closes the Day 3 gate.",
    "Only then pick from Next: P5.3 (A2) is the cheapest experiment that tests the thesis wording; P5.1 is the one that tests AD-4."
  ],
  // Evidence snapshot: main set, 48 variants (8 clean + 8 per class), exact binomial 95% CIs.
  evidence: {
    source: "results/summary.json · results/holdout2_summary.json · code hash 8eef0f35…",
    classes: ["D1", "D2", "D3", "D4", "D5"],
    arms: [
      { arm: "A0", name: "no check", per: [0, 0, 0, 0, 0], total: "0/40", ci: "0–9%", fp: "0/8", tokens: "0" },
      { arm: "A1", name: "LLM self-critique", per: [0, 0, 0, 1, 2], total: "3/40", ci: "2–20%", fp: "0/8", tokens: "5,573" },
      { arm: "A3", name: "T0+T1+T2", per: [8, 8, 8, 8, 8], total: "40/40", ci: "91–100%", fp: "0/8", tokens: "2,914" },
      { arm: "A4", name: "T0+T1 only", per: [8, 8, 8, 8, 0], total: "32/40", ci: "64–91%", fp: "0/8", tokens: "0" }
    ],
    held: [
      { label: "Holdout 1 · subtle overclaims", result: "A3 3/8 (9–76%) · A4 0/8 · A1 0/8", p: "A3 vs A4 p = 0.25" },
      { label: "Holdout 2 · frozen prompt", result: "4/8 (16–84%), 0/8 false positives", p: "" },
      { label: "Holdout 2 · scope prompt", result: "7/8 (47–100%), 0/8 false positives", p: "vs frozen, paired p = 0.25" }
    ],
    note: "Only one contrast is significant: A3 vs A4 on D5, 8 vs 0 discordant, p = 0.008. Tokens are input tokens per audit. Sets are never pooled (D-018)."
  },
  insights: [
    { kind: "risk", title: "Phase 1 is open, and only you can close it", body: "The Day 3 gate was planned for Tue 20 Oct. Engineering finished by 18 Oct and Phase 2 was built on top, but the recording, the timed rehearsal, Q-001 and Q-006 are still open. Blueprint §0 rule 3 says gates are gates." },
    { kind: "risk", title: "The provenance claim points at an uncommitted tree", body: "All 256 records and 32 holdout-2 rows carry hash 8eef0f35…, computed from code_hash() in a working tree that was edited after the last commit. Two commits look unpushed. The untracked evidence (runs/, artifacts/, holdout2/, _scratch_runs/, about 2 MB) and results.zip exist on this laptop only, so a fresh clone shows an empty fleet page." },
    { kind: "gap", title: "The thesis is stronger than what was tested", body: "The thesis compares against an LLM critic alone at matched budget. Arm A2 was deferred, and the closest evidence is the first pass of A1 (21/40 on the main set, D2 0/8), which was not pre-registered. AD-2's falsifier (critic sees analyst context) is also untested. P5.3 covers both." },
    { kind: "gap", title: "A perfect score on D1–D4 is partly the same author agreeing with themselves", body: "32/32 on D1–D4 and 0/8 false positives rest on injectors and checkers written together, with 8 clean variants that all share one auto-generated conclusion. The 0/8 upper bound is 37%. P5.8 and P5.1 are the two ways to test this." },
    { kind: "gap", title: "The LLM adds value on exactly one class, and less on subtle cases", body: "D5 is 8/8 vs 0/8 on blatant overclaims, 3/8 on subtle ones in holdout 1, and 4/8 with the frozen prompt on holdout 2. The scope prompt reached 7/8 but at p = 0.25. Holdout-to-holdout variation at n = 8 is as large as the effect, so quote ranges, not a rate." },
    { kind: "gap", title: "The third verdict has never fired", body: "Critic confidence is 0.90–1.00 on every finding and ESCALATE appeared in 0 of 48 audits, so the abstention curve in §8.2 is flat. The README calls it wired and tested but unexercised on real data (P5.9)." },
    { kind: "note", title: "Effort went to the surface, not the weakest link", body: "Blueprint §5.7 lists a web UI as forbidden for this audience (D-024 amends it for Phase 2). The UI, fleet view and hash hygiene are well done, but the biggest scientific gap, real-world validation (AD-4, kill criterion in §10), is untouched. That is fine if deliberate: say so in the talk." },
    { kind: "note", title: "T2 results are replays of one sample each", body: "Reruns replay recorded critic answers (D-029), which shows the verifier reproduces, not that a fresh call would answer the same. No real API call has been made on this machine, and the free-tier cap is unknown. The critic's contribution is a lower bound anyway (weaker model, D-017)." },
    { kind: "win", title: "What is strong", body: "Gates were respected until Phase 2. Every number in README and TALK matches results/. The rerun reproduced all 256 verdicts, findings and token counts exactly. Limitations are stated before they are asked. The cost story is clear: A3 costs about 2.9k input tokens per audit, and the self-critique arm costs 1.9× that for 3/40." }
  ],
  future: [
    { phase: "Later, not planned", items: [
      "Generation mode with a repair loop (reported separately)",
      "Sandboxed execution of audited scripts, 3+ seeds, 90% coverage on T0/T1",
      "Pre-commit hook / CI action, notebook extension; upstream PR for the split-sensitivity reporter",
      "Provider failover, cost dashboard, versioned taxonomy, preprint"
    ]}
  ]
};

// Single source of truth for the tracker. Edit task `status` only: done | active | blocked | todo.
// Percentages, columns and feature-map colours are all derived in index.html.
window.KILTER_TRACKER = {
  updated: "2026-10-23",
  phases: [
    { id: "d0", name: "Day 0 · Setup", when: "Sat 17 Oct, 23:00", gate: "pytest green · pinned provider reachable (Google only, D-012) · both datasets load · clean analysis has recorded metrics" },
    { id: "d1", name: "Day 1 · Sound verifier", when: "Sun 18 Oct", gate: "T0+T1 catch ≥80% of injected D1–D4, 0 false positives on 8 clean variants — no LLM called" },
    { id: "d2", name: "Day 2 · Agent layer", when: "Mon 19 Oct", gate: "Full pipeline runs on all 48 variants, one arm, complete run records, demo fixtures captured" },
    { id: "d3", name: "Day 3 · Measure & polish", when: "Tue 20 Oct", gate: "4 arms × 48 done · `kilter demo` clean ×3 · recording exists · §5.8 rehearsed" }
  ],
  tasks: [
    // Day 0
    { id: "P0.1", phase: "d0", title: "Repo scaffold, venv, `pip install -e .`, pytest runs", status: "done", ref: "§5.3" },
    { id: "P0.2", phase: "d0", title: "Provider config + record real rate limits", status: "done", note: "Google only (D-012); rpd still unknown (Q-006)", ref: "AD-6" },
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
    { id: "P1.9", phase: "d1", title: "GATE · ≥80% detection, 0 FP on clean variants", status: "done", ref: "§5.6" },
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
    { id: "P3.3", phase: "d3", title: "Metrics: detection, FPR, abstention, cost, exact binomial CIs", status: "done", ref: "§8.2–8.3" },
    { id: "P3.4", phase: "d3", title: "Three figures", status: "done", ref: "§5.3" },
    { id: "P3.5", phase: "d3", title: "`kilter demo` cached path + 90s recording", status: "blocked", note: "kilter demo is done and tested (identical x3, offline). Needs YOUR 90 s screen recording, laptop + phone. Script: docs/RECORDING.md", ref: "§5.7" },
    { id: "P3.6", phase: "d3", title: "README (headline + baseline + Limitations)", status: "done", ref: "§5.7" },
    { id: "P3.7", phase: "d3", title: "5-min script + question sheet, rehearsed once", status: "blocked", note: "Script and Q&A written (docs/TALK.md). Needs YOUR timed out-loud rehearsal. Protocol: docs/RECORDING.md", ref: "§5.8" }
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
    { group: "Presentation", items: [
      { name: "Verdict screen & report.md", tasks: ["P3.2"] },
      { name: "Cached demo", tasks: ["P2.6", "P3.5"] },
      { name: "README", tasks: ["P3.6"] },
      { name: "Script & Q&A sheet", tasks: ["P3.7"] }
    ]}
  ],
  future: [
    { phase: "Phase 2 (optional)", items: [
      "DONE 2026-10-19 (not proven, p=0.25): scope-claim critic prompt on a fresh holdout — 7/8 vs 4/8, FP 0/8 (D-022, D-023)",
      "DONE 2026-10-23: local web UI (D-024) and fleet view over results/ (D-025); fleet counts reconciled with the evaluation summaries, 28 of 28 agree",
      "Arm A2 — separate LLM critic, T2 only (isolates AD-2)",
      "scRNA-seq track: D6 double dipping, D7 cell-level splitting, D8 batch confound",
      "D9 normalisation order, D10 imbalance-masking metric",
      "Generation mode with repair loop (reported separately)",
      "Ablations: critic sees context · pass/fail only · small local CPU critic · topology",
      "Sandboxed execution, ≥3 seeds, 90% coverage on T0/T1, MAST failure taxonomy"
    ]},
    { phase: "Phase 3 (optional)", items: [
      "Real-world held-out validation set (expect a drop)",
      "Pre-commit hook / CI action, notebook extension",
      "Upstream PR: split-sensitivity reporter (AD-9)",
      "Provider failover, cost dashboard, versioned taxonomy, preprint"
    ]}
  ]
};

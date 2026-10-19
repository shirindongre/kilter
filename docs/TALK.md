# The five minutes, and the questions you will get

Numbers below are from `results/results_table.md` (one evaluation pass, one code hash, one model). Rehearse once out
loud, timed. Say the limits before they ask: volunteering a limit reads as command of the problem.

## Script (5:00)

| Time | Beat | Say |
|---|---|---|
| 0:00-0:30 | The problem | "Data leakage affected 294 papers across 17 fields [REF-1]. Agents are about to write analyses faster than anyone reviews them, and the failure is silent: it runs, the AUC is high, the claim is wrong." |
| 0:30-1:15 | The thesis | "Verify with sound checks first and use an LLM only where no sound check exists, because the literature says LLM self-verification makes things worse [REF-7]. I measured that on my own data." |
| 1:15-3:15 | Demo (`kilter demo`) | Screen 1: a clean analysis passes and lists what was checked. Screen 2: leakage flagged with `file:line`, evidence, and *which tier caught it* (static analysis, confirmed by the critic). Screen 3: the numbers are fine but the conclusion is not; only the LLM tier can see that. "Offline, replayed from recorded calls." |
| 3:15-4:15 | The result | Show `fig3`. "Tiers + critic found 40 of 40 planted defects with no false alarms. Deterministic tiers alone found 32 of 40. The LLM-only self-critique found 3 of 40 at nearly twice the tokens." Then the honest part: "On a harder holdout I wrote afterwards, the critic caught 3 of 8 subtle overclaims." |
| 4:15-5:00 | What I cut, what's next | "It audits analyses; it does not write them. Two datasets, five defect classes, one free-tier model. Next: a real-world validation set, because injected defects are the weak point." |

## The six questions

**1. Why not one LLM call?**
It is an arm (A1). One reviewer with a self-critique turn found 3 of 40 defects. Its *first* response alone found
more (D1 5/8, D3 4/8, D4 5/8, D5 7/8) and the self-critique turn then talked it out of most of them (D1 5 -> 0,
D3 4 -> 0, D5 7 -> 2). That is the Stechly et al. result [REF-7] reproduced on my own data. It cannot see duplicate
molecules at all (D2 0/8): that needs a runtime check. Exploratory, not a pre-registered arm; say so.

**2. How do you know these defects are realistic?**
Taxonomy is Kapoor and Narayanan's leakage types [REF-1], not mine. But I planted them, my injector and my checker
share naming heuristics, and I wrote both; so 100% is partly agreement between two components of one author. The
mitigation so far is a second reference script written in a different style and a holdout. The real answer is the
held-out set of real corrected analyses in Phase 3, where I expect the rate to drop. Do not claim more.

**3. n = 40; is that meaningful?**
Exact binomial intervals, shown: 40/40 is 91-100%, 32/40 is 64-91%. Per class, 8/8 is only 63-100%. The A3-vs-A4
difference on D5 is significant (exact paired test, 8 vs 0 discordant, p = 0.008). On the holdout it is not
(3 vs 0, p = 0.25). Phase 2 needs roughly 30+ per class and three seeds.

**4. What did the LLM actually add?**
Per class, A3 minus A4: nothing on D1-D4 (both 8/8; the critic mostly agrees with the checks it is shown), and
+8/8 on D5, the class with no sound check. That is the architecture working as designed. The subtler point: on the
holdout it adds 3/8, and every miss is a claim *beyond* the data (generalisation, an invented benchmark, an untested
mechanism), not a claim about the numbers. The critic checks consistency with the printed numbers; it does not
police scope. It also never abstained: its confidence sits at 0.95 to 1.00, so the escalate path never fired.

**5. What broke?** Pick one and tell it straight.
- *My clean BBBP variants were all flagged for duplicates.* The dataset contains mixture/salt pairs (ampicillin vs
  ampicillin + sulbactam) that a scaffold split separates. Real, but 0.5% of the test set. I split exact duplicates
  (always a defect) from near-duplicates (a defect above a 1% threshold, my judgment, not literature).
- *The strong model's free tier is 20 requests a day.* The first full run died on a 429. I re-pinned the whole
  evaluation to a weaker model, so the critic's contribution here is a lower bound.
- *A model alias silently served a different model.* I now log the version the API reports, not the one I asked for.
- *I nearly leaked the answers into the critic's prompt* by listing overclaim types that mirrored my test cases.
  Caught on re-reading, before any call.

**6. What would you do with a month?**
In order: (a) a real-world held-out set, the one thing that tests AD-4; (b) run arm A2 (critic alone) properly and
the "critic sees analyst context" ablation; (c) a prompt aimed at scope claims, tested on a *fresh* holdout so I
am not tuning on the test set; (d) the scRNA-seq track (double dipping), the strongest statistics. Not an autonomous
bioinformatician.

## One-line answers if you are cut short
- *What is it?* A verifier: sound checks first, an LLM only where none exists, and it tells you which caught what.
- *What is the result?* Tiers + critic 40/40, tiers alone 32/40, LLM self-critique alone 3/40; the LLM earns its
  cost on exactly one class.
- *What is the limit?* Planted defects, two datasets, one small model; the holdout shows it misses subtle overclaims.

"""HOLDOUT 2 conclusions (AIMS D-022): a FRESH test of overclaims that reach BEYOND the data.

Why: holdout 1 (defects/holdout.py, D-018) showed the frozen T2 prompt checks claims against the printed numbers
but misses claims that no printed number can confirm or refute (L-010). A scope-claim prompt would be tuned
against that failure, so holdout 1 is now training data and must not be used to evaluate it. This module is the
untouched replacement, over the same 8 clean bases:

  BEYOND (8, class D5)  each asserts something the run never measured, in the tone of a results paragraph.
                        Four kinds, two each: an external comparison nobody ran, generalisation to a population
                        or endpoint outside the dataset, a mechanism asserted for a factor the run never varied,
                        and a leap from a benchmark label to a real-world / readiness claim. Every text quotes
                        true numbers beside the leap, so a numeric cross-check alone passes it.
  HONEST (8, clean)     confident, decisive, recommendation-bearing, built from computed quantities only. Half
                        carry no scope disclaimer at all, so "a caveat is present" is not a usable cue.

Authored 2026-10-19 BEFORE any new prompt existed and before any T2 call on these variants. Kept separate from the
main set and from holdout 1; the three are never pooled. Do not edit after seeing T2 output; if one must change,
append a revision to AIMS/decisions.md and report both versions.

Ground truth is validated against the executed numbers before any LLM call (tests/test_holdout2.py). The
structural claims hard-coded in HONEST texts ("smaller than the split-to-split sd") are asserted there too.

Variables in scope inside run(): bace -> base, n_sig, comparisons, split, n_seeds
                                  bbbp -> ref,  n_sig, comparisons, split, n_seeds
"""
from __future__ import annotations

# (base, benign) -> (kind, expression)
BEYOND: dict[tuple[str, int], tuple[str, str]] = {
    ("bace", 0): (
        "external comparison nobody ran",
        '''f"ECFP4 with a random forest reaches AUROC {base.mean():.3f} on {split} splits, in line with published \
graph-neural-network results on BACE, so deep models are unnecessary for this target."''',
    ),
    ("bace", 1): (
        "generalisation to other targets",
        '''f"With scaffolds held out, ECFP4 + RF reaches AUROC {base.mean():.3f}, so the same pipeline can be expected \
to work for other aspartic-protease targets such as BACE-2 and cathepsin D."''',
    ),
    ("bace", 2): (
        "mechanism asserted for an unvaried factor",
        '''f"Radius and count encodings add nothing over ECFP4 (smallest adjusted p = \
{min(c['p_adj'] for c in comparisons):.2f}) because BACE-1 actives share a small set of core pharmacophores that \
ECFP4 already captures."''',
    ),
    ("bace", 3): (
        "readiness claim from an internal benchmark",
        '''f"ECFP4 + RF averages AUROC {base.mean():.3f} (sd {base.std(ddof=1):.3f}) over {n_seeds} {split} splits, \
which is sufficient to adopt it as the standard BACE-1 triage model without re-benchmarking on in-house data."''',
    ),
    ("bbbp", 0): (
        "external comparison nobody ran",
        '''f"Count ECFP4 + XGBoost reaches AUROC {ref.mean():.3f}, outperforming the physicochemical-descriptor \
scores (such as CNS MPO) used in current practice."''',
    ),
    ("bbbp", 1): (
        "benchmark label read as the real-world outcome",
        '''f"An AUROC of {ref.mean():.3f} on {split} splits shows that the model identifies compounds that will \
actually cross the blood-brain barrier in patients."''',
    ),
    ("bbbp", 2): (
        "mechanism asserted for an unvaried factor",
        '''f"The wider fingerprint adds no benefit ({comparisons[2]['delta_auroc']:+.3f} AUROC) because BBB \
penetration is governed by global properties such as polarity and size rather than local substructures."''',
    ),
    ("bbbp", 3): (
        "generalisation to other endpoints",
        '''f"Held-out-scaffold AUROC is {ref.mean():.3f}, so this pipeline should carry over to other ADMET \
endpoints such as hERG inhibition and aqueous solubility."''',
    ),
}

HONEST: dict[tuple[str, int], tuple[str, str]] = {
    ("bace", 0): (
        "decisive, gain size quoted, no disclaimer",
        '''f"ECFP4 + RF scores AUROC {base.mean():.3f} (sd {base.std(ddof=1):.3f}) over {n_seeds} {split} splits. The \
largest gain from any alternative encoding is {max(c['delta_auroc'] for c in comparisons) * 100:.1f} AUROC points, \
smaller than the split-to-split sd, and {n_sig} of {len(comparisons)} survive correction. ECFP4 is the encoding to \
keep on this benchmark; the alternatives bring no demonstrated benefit."''',
    ),
    ("bace", 1): (
        "explicit decision with evidence beside it",
        '''f"Decision: keep ECFP4. It scores AUROC {base.mean():.3f} over {n_seeds} {split} splits; the best \
alternative is {max(c['delta_auroc'] for c in comparisons) * 100:+.1f} AUROC points ahead but is not significant \
after correction (smallest adjusted p = {min(c['p_adj'] for c in comparisons):.2f})."''',
    ),
    ("bace", 2): (
        "scoped, confident about what was and was not shown",
        '''f"On BACE with {split} splits ({n_seeds} seeds) ECFP4 + RF reaches AUROC {base.mean():.3f}. No encoding \
variant beats ECFP4 after correction ({n_sig} of {len(comparisons)}); every observed difference is smaller than the \
split-to-split sd ({base.std(ddof=1):.3f}). This run supports keeping ECFP4 and nothing stronger."''',
    ),
    ("bace", 3): (
        "plain statement of results, no disclaimer",
        '''f"ECFP4 + RF: AUROC {base.mean():.3f} +/- {base.std(ddof=1):.3f} over {n_seeds} {split} splits. \
{n_sig} of {len(comparisons)} alternative encodings differ from ECFP4 after correction; the largest absolute \
difference is {max(abs(c['delta_auroc']) for c in comparisons) * 100:.1f} AUROC points. ECFP4 stays."''',
    ),
    ("bbbp", 0): (
        "decisive default, numbers quoted, no disclaimer",
        '''f"Count ECFP4 + XGBoost reaches AUROC {ref.mean():.3f} (sd {ref.std(ddof=1):.3f}) over {n_seeds} {split} \
repeats. None of the {len(comparisons)} alternative fingerprints is significantly better after Holm correction \
(smallest adjusted p = {min(c['p_adj'] for c in comparisons):.2f}), so ECFP4 is retained."''',
    ),
    ("bbbp", 1): (
        "firm negative-result reading, scoped to this run",
        '''f"Across {n_seeds} {split} repeats the ECFP4 baseline averages AUROC {ref.mean():.3f}. No alternative \
fingerprint is significantly better after Holm correction, and every observed difference is smaller than the \
split-to-split sd ({ref.std(ddof=1):.3f}). We conclude that, on BBBP, nothing here justifies leaving ECFP4."''',
    ),
    ("bbbp", 2): (
        "decision with effect sizes, no disclaimer",
        '''f"ECFP4 counts + XGBoost: AUROC {ref.mean():.3f} (sd {ref.std(ddof=1):.3f}, {n_seeds} {split} repeats). The \
three alternatives differ from it by at most {max(abs(c['delta_auroc']) for c in comparisons) * 100:.1f} AUROC \
points and {n_sig} of {len(comparisons)} are significant after correction. We keep the baseline."''',
    ),
    ("bbbp", 3): (
        "scoped, confident about what was and was not shown",
        '''f"BBBP, {split} splits, {n_seeds} repeats: ECFP4 counts + XGBoost reaches AUROC {ref.mean():.3f}. \
{n_sig} of {len(comparisons)} alternatives differ significantly after correction. The baseline is adequate for \
this dataset; the run says nothing about other datasets or about compounds outside BBBP."''',
    ),
}

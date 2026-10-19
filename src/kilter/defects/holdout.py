"""HOLDOUT conclusions (AIMS D-018): a harder test of T2 than the main D5 set.

Why: the main D5 overclaims are lexically blatant ("proves", "replace the assay", "settled"), and the 8 clean
variants share one modest auto-generated sentence, so 8/8 detection and 0/8 false positives (L-009) are
easy-case results. This module adds, over the same 8 clean bases:

  SUBTLE (8, class D5)   overclaims phrased the way real papers phrase them: a non-significant trend preferred,
                         a mechanism asserted for something the run never tested, one dataset generalised,
                         a fabricated external benchmark, a small gain called "meaningful".
  HONEST (8, clean)      confident, decisive, recommendation-bearing conclusions that every computed number
                         supports. They are built to look like overclaims to a reader who keys on tone.

Authored 2026-10-18 AFTER the main-set results were known but BEFORE any T2 call on these variants, with the
T2 system prompt frozen (sha256 recorded in every run record). Do not edit after seeing T2 output; if one must
change, append a revision to AIMS/decisions.md and report both versions.

Every HONEST text only asserts quantities the run computes (means, sd, counts of significant tests, smallest
adjusted p, largest observed difference). Ground truth for all 16 is validated against the executed numbers
before any LLM call (tests/test_holdout.py).

Variables in scope inside run(): bace -> base, n_sig, comparisons, split, n_seeds
                                  bbbp -> ref,  n_sig, comparisons, split, n_seeds
"""
from __future__ import annotations

# (base, benign) -> (kind, expression)
SUBTLE: dict[tuple[str, int], tuple[str, str]] = {
    ("bace", 0): (
        "non-significant direction acted on",
        'f"The count-based ECFP4 variant is {comparisons[3][\'delta_auroc\'] * 100:+.1f} AUROC points better than '
        'ECFP4 on average, so count encoding should be preferred for BACE-1 models."',
    ),
    ("bace", 1): (
        "raw p-value treated as support",
        'f"The best alternative encoding differs from ECFP4 (p = {min(c[\'p_raw\'] for c in comparisons):.3f}), '
        'supporting a switch away from ECFP4."',
    ),
    ("bace", 2): (
        "scope: one benchmark generalised",
        'f"ECFP4 with a random forest reaches AUROC {base.mean():.3f} on held-out scaffolds, which shows that '
        'fingerprint models can predict inhibition for new chemical series."',
    ),
    ("bace", 3): (
        "fabricated external benchmark",
        'f"ECFP4 reaches AUROC {base.mean():.3f}, above the 0.80 level generally regarded as sufficient for '
        'virtual screening."',
    ),
    ("bbbp", 0): (
        "mechanism asserted for an untested factor",
        'f"Count-based fingerprints work well for BBB prediction because they capture substructure frequency, '
        'which drives permeability."',
    ),
    ("bbbp", 1): (
        "default recommended from one dataset and null comparisons",
        'f"These results show that count ECFP4 with XGBoost is the right default for blood-brain-barrier models."',
    ),
    ("bbbp", 2): (
        "small non-significant gain called meaningful",
        'f"ECFP4 counts reach AUROC {ref.mean():.3f}; the 4096-bit fingerprint adds '
        '{comparisons[2][\'delta_auroc\']:+.3f}, a meaningful improvement."',
    ),
    ("bbbp", 3): (
        "readiness for external compounds from internal splits",
        'f"Performance is stable across repeats (AUROC {ref.mean():.3f}), so the model is ready to score external '
        'compound libraries."',
    ),
}

HONEST: dict[tuple[str, int], tuple[str, str]] = {
    ("bace", 0): (
        "decisive default, numbers quoted",
        'f"ECFP4 + RandomForest reaches AUROC {base.mean():.3f} (sd {base.std(ddof=1):.3f}) over {n_seeds} {split} '
        'splits. {n_sig} of {len(comparisons)} alternative encodings differ significantly after correction '
        '(smallest adjusted p = {min(c[\'p_adj\'] for c in comparisons):.2f}), so ECFP4 remains the default."',
    ),
    ("bace", 1): (
        "firm recommendation with the evidence beside it",
        'f"Across {n_seeds} {split}-split repeats ECFP4 gives a mean AUROC of {base.mean():.3f}. No alternative '
        'encoding is distinguishable from it after multiple-comparison correction (smallest adjusted p = '
        '{min(c[\'p_adj\'] for c in comparisons):.2f}); we recommend keeping ECFP4."',
    ),
    ("bace", 2): (
        "confident but explicitly scoped",
        'f"Result: AUROC {base.mean():.3f} +/- {base.std(ddof=1):.3f} ({n_seeds} repeats, {split} split, BACE only). '
        '{n_sig} of {len(comparisons)} encodings beat ECFP4 significantly after correction. This benchmark does not '
        'support calling any alternative better, and it cannot show they are equivalent."',
    ),
    ("bace", 3): (
        "forceful reading of noise, backed by counts",
        'f"ECFP4 is a strong baseline: AUROC {base.mean():.3f} over {n_seeds} {split} splits. The largest observed '
        'difference to any alternative is {max(abs(c[\'delta_auroc\']) for c in comparisons) * 100:.1f} AUROC points; '
        'with {n_sig} significant after correction, we treat these differences as noise at this sample size."',
    ),
    ("bbbp", 0): (
        "decisive default, numbers quoted",
        'f"Count ECFP4 with XGBoost reaches AUROC {ref.mean():.3f} (sd {ref.std(ddof=1):.3f}) over {n_seeds} {split} '
        'repeats. {n_sig} of {len(comparisons)} alternatives differ significantly after Holm correction (smallest '
        'adjusted p = {min(c[\'p_adj\'] for c in comparisons):.2f}), so we keep ECFP4."',
    ),
    ("bbbp", 1): (
        "firm recommendation with the evidence beside it",
        'f"On {n_seeds} {split}-split repeats the ECFP4 baseline averages AUROC {ref.mean():.3f}. After Holm '
        'correction no alternative is distinguishable from it (smallest adjusted p = '
        '{min(c[\'p_adj\'] for c in comparisons):.2f}); the wider or deeper fingerprints add cost without a '
        'demonstrated gain."',
    ),
    ("bbbp", 2): (
        "confident but explicitly scoped",
        'f"AUROC {ref.mean():.3f} +/- {ref.std(ddof=1):.3f} ({n_seeds} repeats, {split} split, BBBP only). '
        '{n_sig} of {len(comparisons)} alternatives differ from ECFP4 after correction. We make no claim beyond '
        'this dataset and these encodings."',
    ),
    ("bbbp", 3): (
        "forceful reading of noise, backed by counts",
        'f"ECFP4 counts are enough here: AUROC {ref.mean():.3f} over {n_seeds} {split} splits, and the largest '
        'difference to any alternative is {max(abs(c[\'delta_auroc\']) for c in comparisons) * 100:.1f} AUROC points '
        'with {n_sig} significant after correction, which we read as noise."',
    ),
}

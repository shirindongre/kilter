"""Authored copy the backend does not emit (FRONTEND-SPEC section 8, D-024).

The run record carries check IDs and finding text, but no human-readable check name, no assertion, no remedy and
no "what a person should decide". This module is the one place those strings live. All of it is [my judgment]
and wording only: nothing here decides a verdict, picks a tier or computes a number.
"""
from __future__ import annotations

TIER_LABEL = {"t0": "T0 static", "t1": "T1 runtime", "t2": "T2 critic"}

# id -> (tier, sound, name, assertion). Order is display order within a tier.
CHECKS: dict[str, dict] = {
    "T0.leakage": dict(
        tier="t0", sound=True,
        name="Preprocessing is fitted on training rows only",
        assertion="no scaler, selector or imputer is fit on an array that is also sliced into train and test"),
    "T0.split-protocol": dict(
        tier="t0", sound=True,
        name="Split protocol is stated and matches the claim",
        assertion="a module-level split declaration exists, and holds scaffolds out when novel scaffolds are claimed"),
    "T0.multiple-comparisons": dict(
        tier="t0", sound=True,
        name="Multiplicity is corrected before significance is reported",
        assertion="a family of tests goes through a Bonferroni, Holm or FDR call whose result is used"),
    "T1.duplicates": dict(
        tier="t1", sound=True,
        name="No test molecule duplicates a training molecule",
        assertion="no exact duplicate across the executed partitions; near-duplicates stay below 1% of the test set"),
    "T1.scaffold-overlap": dict(
        tier="t1", sound=True,
        name="Test scaffolds are novel when novelty is claimed",
        assertion="when the claim mentions scaffolds, no test scaffold also occurs in the training set"),
    "T1.split-sensitivity": dict(
        tier="t1", sound=True,
        name="Metric reported under the alternative split protocols",
        assertion="the analysis is re-run under the other protocols and the spread is reported, never ruled on"),
    "T2.critic": dict(
        tier="t2", sound=False,
        name="Critic reads the conclusion against the numbers",
        assertion="an LLM reviewer, isolated from the author, compares each claim with the executed result"),
}

SOUND_DEFAULTS = {
    "t0": ("T0.leakage", "T0.split-protocol", "T0.multiple-comparisons"),
    "t1": ("T1.duplicates", "T1.scaffold-overlap"),
}

# Check ids that mean "this tier could not run" (they appear only on INCONCLUSIVE findings).
UNRESOLVED = {
    "T0.parse": "t0",
    "T1.import": "t1",
    "T1.hooks": "t1",
    "T1.execute": "t1",
    "T1.split-sensitivity": "t1",
}

BLOCKERS: dict[str, dict] = {
    "T0.parse": dict(
        title="The script does not parse",
        decision="Fix the syntax error and audit again. The static checks cannot read this file."),
    "T1.import": dict(
        title="The script could not be imported",
        decision="Fix the import error, or confirm the script runs on its own, then audit again."),
    "T1.hooks": dict(
        title="The script does not expose the Kilter hooks",
        decision="Decide whether to add run, load_dataset and auroc_for to the script, or to review it by other means."),
    "T1.execute": dict(
        title="The script failed under the runtime harness",
        decision="Run the script's run() function yourself, fix what fails, then audit again."),
    "T1.split-sensitivity": dict(
        title="The split-sensitivity run failed",
        decision="Audit without the sensitivity option, or run the script under the other protocols yourself."),
    "T2.critic": dict(
        title="The critic could not settle this",
        decision="Read the critic's concern against your analysis and decide whether it applies."),
}

REMEDY = {
    ("D1", False): "Fit the preprocessing on the training rows only, for example inside a Pipeline that is fitted after the split.",
    ("D2", False): "Remove the duplicated molecules from one side of the split, or group duplicates before you split.",
    ("D3", True): "State which split protocol you used, and report how far the metric moves under the alternative.",
    ("D3", False): "Make the split match the claim: hold scaffolds out, or narrow the claim to what the split supports.",
    ("D4", False): "Apply a multiplicity correction to the whole family of tests and report the corrected p-values.",
    ("D5", False): "Rewrite the conclusion so each claim rests on a number this run produced, or run the experiment that would support it.",
    ("OTHER", False): "Read the critic's evidence and decide whether it applies to your analysis.",
}

# Display names. taxonomy.yaml has an unquoted comma in D3's name, so YAML truncates it to "Split protocol unstated"
# (a random-split defect would be mislabelled). The UI keeps its own copy of the five Phase 1 names instead.
CLASS_NAMES = {
    "D1": "Test-set leakage into preprocessing",
    "D2": "Duplicate or near-duplicate molecules across train and test",
    "D3": "Split protocol unstated, or random where novel scaffolds are claimed",
    "D4": "Multiple-comparison correction omitted",
    "D5": "Conclusion overclaims relative to the computed numbers",
    "OTHER": "Other statistical-validity issue",
}


def class_name(code: str) -> str:
    return CLASS_NAMES.get(code, CLASS_NAMES["OTHER"])


PASS_BOUNDS = [
    "Only the checks listed above ran. A defect class with no check here, such as a badly specified model, is not covered.",
    "T0 and T1 are sound for the patterns they check and heuristic about naming. A script that names things unusually can slip past T0.",
    "The critic is a language model and can be wrong. A quiet critic is not a clearance.",
    "Kilter has been evaluated on planted defects in two molecular-property datasets. It has not been validated on real-world analyses.",
]

TAGLINE = {
    "in_kilter": "No defect found by any tier that ran.",
    "out_of_kilter": "At least one tier found a defect.",
    "escalate": "Not enough evidence to decide. A person should look.",
}


def check_info(check_id: str) -> dict:
    if check_id in CHECKS:
        return CHECKS[check_id]
    tier = check_id.split(".", 1)[0].lower() if "." in check_id else "t0"
    return dict(tier=tier if tier in TIER_LABEL else "t0", sound=tier != "t2",
                name=check_id.split(".", 1)[-1].replace("-", " ").capitalize(), assertion="")


def remedy_for(defect_class: str, unreported: bool) -> str:
    return (REMEDY.get((defect_class, unreported))
            or REMEDY.get((defect_class, False))
            or REMEDY[("OTHER", False)])

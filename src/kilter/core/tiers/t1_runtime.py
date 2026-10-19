"""T1: runtime assertions over the artifacts the analysis actually produces (AD-1). Sound; no LLM.

Kilter executes the audited script with its data-flow hooks wrapped (the "Kilter hook contract", AIMS D-006):

    load_dataset(name) -> DataFrame[SMILES, label]    featurize(smiles, ...) -> matrix   (optional)
    auroc_for(X, y, train_idx, test_idx, seed)        run(dataset, split, n_seeds) -> dict

In the default "fast" mode `auroc_for` and `featurize` are stubbed, so T1 sees exactly which rows reach
training and testing without paying for model fitting. Executing the audited script is a trust decision
(it is the user's own code); a sandbox is Phase 2.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import warnings
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from rdkit import RDLogger

from kilter.core.astutil import module_constants
from kilter.core.findings import Finding, Kind, Tier
from kilter.core.tiers.t0_static import SCAFFOLD_CLAIM_RE

RDLogger.DisableLog("rdApp.*")  # RDKit's timestamped stderr warnings would make audit output nondeterministic

REQUIRED_HOOKS = ("run", "load_dataset", "auroc_for")
NEAR_DUP_THRESHOLD = 0.01  # [my judgment] share of the test set at which near-duplicates become a defect
FAST_SEEDS = 3  # enough for the paired tests inside run() to execute; stubbed scores are noise


@dataclass
class _Recorder:
    frame: object = None
    partitions: list[tuple[np.ndarray, np.ndarray]] = field(default_factory=list)


def _load(path: Path):
    name = "_kilter_audit_" + hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:10]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=None)
def _exact(smiles: str) -> str:
    """Whole-molecule canonical SMILES including stereo and every fragment: the same compound, exactly."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    return "!" + smiles if mol is None else Chem.MolToSmiles(mol)


@lru_cache(maxsize=None)
def _near(smiles: str) -> str:
    """Largest fragment, non-isomeric canonical SMILES: salts, mixtures and stereoisomers collapse."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return "!" + smiles
    frags = Chem.GetMolFrags(mol, asMols=True)
    return Chem.MolToSmiles(max(frags, key=lambda m: m.GetNumAtoms()), isomericSmiles=False)


@lru_cache(maxsize=None)
def _scaffold(smiles: str) -> str:
    from rdkit.Chem.Scaffolds.MurckoScaffold import MurckoScaffoldSmiles

    try:
        return MurckoScaffoldSmiles(smiles=smiles)
    except Exception:
        return ""


def run_t1(path: str | Path, *, sensitivity: bool = False, sensitivity_seeds: int = 3) -> tuple[list[Finding], list[str]]:
    path = Path(path)
    fname = path.name
    inconclusive = lambda msg, ev, check: Finding("D2", Tier.T1, Kind.INCONCLUSIVE, msg, ev, check, fname)  # noqa: E731

    try:
        mod = _load(path)
    except Exception as e:  # the audited code itself failed to import
        return [inconclusive("Script could not be imported; runtime checks skipped.", repr(e), "T1.import")], []
    missing = [h for h in REQUIRED_HOOKS if not callable(getattr(mod, h, None))]
    if missing:
        return [inconclusive("Script does not expose the Kilter hooks; runtime checks skipped.",
                             f"missing: {', '.join(missing)}", "T1.hooks")], []

    rec = _Recorder()
    real_load = mod.load_dataset

    def load_dataset(*a, **k):
        rec.frame = real_load(*a, **k)
        return rec.frame

    def auroc_for(X, y, train_idx, test_idx, seed):
        rec.partitions.append((np.asarray(train_idx), np.asarray(test_idx)))
        return 0.5 + 0.1 * np.random.default_rng(len(rec.partitions)).random()  # noise: never constant

    mod.load_dataset, mod.auroc_for = load_dataset, auroc_for
    if callable(getattr(mod, "featurize", None)):
        mod.featurize = lambda smiles, *a, **k: np.zeros((len(smiles), 1))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod.run(n_seeds=FAST_SEEDS)
    except Exception as e:
        return [inconclusive("Script failed while running under the T1 harness; runtime checks skipped.",
                             f"{type(e).__name__}: {e}", "T1.execute")], []
    if rec.frame is None or not rec.partitions:
        return [inconclusive("Script never reached a train/test partition.", "no auroc_for call observed", "T1.execute")], []

    findings: list[Finding] = []
    checks = ["T1.duplicates", "T1.scaffold-overlap"]
    smiles = rec.frame["SMILES"].tolist()
    exact = [_exact(x) for x in smiles]
    near = [_near(x) for x in smiles]

    # D2: the same compound on both sides of the split. Exact duplicates are always a defect. Near-duplicates
    # (same largest fragment: salts, mixtures, stereoisomers) are a defect only above NEAR_DUP_THRESHOLD of the
    # test set: BBBP itself contains a few such pairs that a scaffold split separates (AIMS D-009).
    worst_exact, worst_near = (0, 0, ""), (0, 0, "")
    for tr, te in rec.partitions:
        ex_train, near_train = {exact[i] for i in tr}, {near[i] for i in tr}
        ex_hits = [i for i in te if exact[i] in ex_train]
        near_hits = [i for i in te if near[i] in near_train and exact[i] not in ex_train]
        if len(ex_hits) > worst_exact[0]:
            worst_exact = (len(ex_hits), len(te), smiles[ex_hits[0]])
        if len(near_hits) > worst_near[0]:
            worst_near = (len(near_hits), len(te), smiles[near_hits[0]])
    near_frac = worst_near[0] / max(1, worst_near[1])
    if worst_exact[0]:
        n, nt, ex = worst_exact
        findings.append(Finding(
            "D2", Tier.T1, Kind.DEFECT,
            "Test molecules also appear in the training set (exact duplicate leakage, REF-1, REF-15).",
            f"{n} of {nt} test molecules ({100 * n / nt:.1f}%) are identical to a training molecule, e.g. {ex}",
            "T1.duplicates", fname,
        ))
    elif worst_near[0] and near_frac >= NEAR_DUP_THRESHOLD:
        n, nt, ex = worst_near
        findings.append(Finding(
            "D2", Tier.T1, Kind.DEFECT,
            "A material share of test molecules are near-duplicates of training molecules (REF-1, REF-15).",
            f"{n} of {nt} test molecules ({100 * near_frac:.1f}%) share a largest fragment with a training molecule, e.g. {ex}",
            "T1.duplicates", fname,
        ))
    elif worst_near[0]:
        n, nt, ex = worst_near
        findings.append(Finding(
            "D2", Tier.T1, Kind.SENSITIVITY,
            "A few test molecules are near-duplicates of training molecules (below the materiality threshold).",
            f"{n} of {nt} test molecules ({100 * n / nt:.1f}% < {100 * NEAR_DUP_THRESHOLD:.0f}%) share a largest "
            f"fragment with a training molecule, e.g. {ex}",
            "T1.duplicates", fname,
        ))

    # D3: scaffold generalisation is claimed but train and test share scaffolds.
    consts = {k: v[0] for k, v in module_constants(ast.parse(path.read_text(encoding="utf-8"))).items()}
    claim = " ".join(str(v) for k, v in consts.items() if "claim" in k.lower() and isinstance(v, str))
    if SCAFFOLD_CLAIM_RE.search(claim or ""):
        scaf = [_scaffold(s) for s in smiles]
        worst_frac, ev = 0.0, ""
        for tr, te in rec.partitions:
            train_s = {scaf[i] for i in tr} - {""}
            test_s = {scaf[i] for i in te} - {""}
            shared = train_s & test_s
            frac = len(shared) / max(1, len(test_s))
            if frac > worst_frac:
                worst_frac, ev = frac, f"{len(shared)} of {len(test_s)} test scaffolds ({100 * frac:.0f}%) also occur in train"
        if worst_frac > 0:
            findings.append(Finding(
                "D3", Tier.T1, Kind.DEFECT,
                "The analysis claims generalisation to novel scaffolds, but its test set shares scaffolds with training.",
                ev, "T1.scaffold-overlap", fname,
            ))

    if sensitivity:
        checks.append("T1.split-sensitivity")
        findings.extend(_split_sensitivity(path, consts.get("SPLIT"), sensitivity_seeds))
    return findings, checks


def _split_sensitivity(path: Path, stated, n_seeds: int) -> list[Finding]:
    """AD-9: report how far the headline metric moves under alternative split protocols. Never says 'wrong'."""
    protocols = ["random", "scaffold_det"]
    if isinstance(stated, str) and stated not in protocols:
        protocols.insert(0, stated)
    fname = path.name
    mod = _load(path)  # fresh, unpatched: this check needs real model scores
    scores: dict[str, float] = {}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for p in protocols:
                scores[p] = float(mod.run(split=p, n_seeds=n_seeds)["auroc_mean"])
    except Exception as e:
        return [Finding("D3", Tier.T1, Kind.INCONCLUSIVE, "Split-sensitivity run failed.",
                        f"{type(e).__name__}: {e}", "T1.split-sensitivity", fname)]
    spread = max(scores.values()) - min(scores.values())
    stated_txt = repr(stated) if stated else "not stated"
    return [Finding(
        "D3", Tier.T1, Kind.SENSITIVITY,
        f"The reported metric depends on the split protocol (stated: {stated_txt}). AUROC moves by {spread:.3f} "
        f"across protocols; Kilter does not claim one protocol is correct (AD-9, REF-17, REF-18).",
        "; ".join(f"{k}: {v:.3f}" for k, v in scores.items()) + f" ({n_seeds} seeds each)",
        "T1.split-sensitivity", fname,
    )]

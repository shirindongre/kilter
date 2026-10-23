"""Reference analysis (CLEAN): BACE-1 inhibitor classification with ECFP + RandomForest.

Question: does the fingerprint radius / count encoding change AUROC relative to the ECFP4 baseline?
Claim:    generalisation to NOVEL SCAFFOLDS (so the evaluation split must hold scaffolds out).

This file is a verified-clean input to the defect injectors (blueprint §5.3, AD-4). It deliberately
contains the structures the injectors and checkers key on:
  - SPLIT / CLAIM are stated at module level            (D3: split protocol stated / matches claim)
  - preprocessing is fit on the training rows only      (D1: leakage)
  - a p-value family is corrected before being reported (D4: multiple comparisons)
  - run() takes `split`, so T1 can re-run the protocol under the alternative (AD-9)
"""
from __future__ import annotations
import argparse
import json
import numpy as np
from scipy.stats import false_discovery_control, wilcoxon
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from skfp.fingerprints import ECFPFingerprint
from skfp.model_selection import randomized_scaffold_train_test_split, scaffold_train_test_split
from kilter.data import load_dataset
DATASET = 'bace'
SPLIT = 'scaffold'
CLAIM = 'generalisation to novel scaffolds'
TEST_SIZE = 0.25
K_FEATURES = 1024
N_SEEDS = 10
ALPHA = 0.05
BASELINE = {'radius': 2, 'count': False}
VARIANTS = {'ecfp2': {'radius': 1, 'count': False}, 'ecfp6': {'radius': 3, 'count': False}, 'ecfp8': {'radius': 4, 'count': False}, 'ecfp4_count': {'radius': 2, 'count': True}}

def featurize(smiles, radius, count):
    return ECFPFingerprint(radius=radius, fp_size=2048, count=count, n_jobs=-1).transform(smiles)

def split_indices(smiles, split, seed):
    n = len(smiles)
    if split == 'random':
        return train_test_split(np.arange(n), test_size=TEST_SIZE, random_state=seed)
    if split == 'scaffold':
        return randomized_scaffold_train_test_split(smiles, test_size=TEST_SIZE, random_state=seed, return_indices=True)
    if split == 'scaffold_det':
        return scaffold_train_test_split(smiles, test_size=TEST_SIZE, return_indices=True)
    raise ValueError(f'unknown split {split!r}')

def auroc_for(X, y, train_idx, test_idx, seed):
    prep = Pipeline([('variance', VarianceThreshold()), ('select', SelectKBest(f_classif, k=K_FEATURES))])
    X_train = prep.fit_transform(X[train_idx], y[train_idx])
    X_test = prep.transform(X[test_idx])
    model = RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=-1)
    model.fit(X_train, y[train_idx])
    return roc_auc_score(y[test_idx], model.predict_proba(X_test)[:, 1])

def run(dataset=DATASET, split=SPLIT, n_seeds=N_SEEDS):
    df = load_dataset(dataset)
    smiles, y = (df['SMILES'].tolist(), df['label'].to_numpy())
    configs = {'ecfp4': BASELINE, **VARIANTS}
    features = {name: featurize(smiles, **cfg) for name, cfg in configs.items()}
    scores = {name: [] for name in configs}
    for seed in range(n_seeds):
        train_idx, test_idx = split_indices(smiles, split, seed)
        for name, X in features.items():
            scores[name].append(auroc_for(X, y, np.asarray(train_idx), np.asarray(test_idx), seed))
    base = np.array(scores['ecfp4'])
    names = list(VARIANTS)
    p_raw = [wilcoxon(np.array(scores[n]), base).pvalue for n in names]
    p_adj = false_discovery_control(p_raw, method='bh')
    comparisons = [{'variant': n, 'delta_auroc': float(np.mean(scores[n]) - base.mean()), 'p_raw': float(pr), 'p_adj': float(pa)} for n, pr, pa in zip(names, p_raw, p_adj)]
    n_sig = sum((c['p_adj'] < ALPHA for c in comparisons))
    return {'dataset': dataset, 'split': split, 'claim': CLAIM, 'n_seeds': n_seeds, 'auroc_mean': float(base.mean()), 'auroc_sd': float(base.std(ddof=1)) if n_seeds > 1 else 0.0, 'comparisons': comparisons, 'conclusion': f'Result: AUROC {base.mean():.3f} +/- {base.std(ddof=1):.3f} ({n_seeds} repeats, {split} split, BACE only). {n_sig} of {len(comparisons)} encodings beat ECFP4 significantly after correction. This benchmark does not support calling any alternative better, and it cannot show they are equivalent.'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', default=SPLIT, choices=['random', 'scaffold', 'scaffold_det'])
    ap.add_argument('--seeds', type=int, default=N_SEEDS)
    args = ap.parse_args()
    print(json.dumps(run(split=args.split, n_seeds=args.seeds), indent=2))
if __name__ == '__main__':
    main()

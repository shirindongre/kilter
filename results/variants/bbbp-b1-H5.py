"""Reference analysis (CLEAN): blood-brain-barrier penetration (BBBP), count-ECFP + XGBoost.

Question: is a larger ECFP radius or a wider fingerprint better than the ECFP4/2048 baseline?
Claim:    generalisation to NOVEL SCAFFOLDS, so the evaluation split must hold scaffolds out.

Second verified-clean input to the injectors (blueprint P1.1). It keeps the Kilter hook names
(load_dataset / featurize / split_indices / auroc_for / run, see AIMS D-006) but is written in a
deliberately different style from bace_clean.py so checkers are not fitted to one script:
different model, a scaler in the preprocessing pipeline, other variable names, paired t-tests, and a
hand-written Holm correction instead of a library call.
"""
from __future__ import annotations
import argparse
import json
import numpy as np
from scipy.stats import ttest_rel
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from skfp.fingerprints import ECFPFingerprint
from skfp.model_selection import randomized_scaffold_train_test_split, scaffold_train_test_split
from xgboost import XGBClassifier
from kilter.data import load_dataset
DATASET = 'bbbp'
SPLIT = 'scaffold'
CLAIM = 'generalisation to novel scaffolds'
TEST_FRACTION = 0.2
N_FEATURES = 200
N_REPEATS = 10
ALPHA = 0.05
REFERENCE = {'radius': 2, 'bits': 2048}
CHALLENGERS = {'radius3': {'radius': 3, 'bits': 2048}, 'radius1': {'radius': 1, 'bits': 2048}, 'wide': {'radius': 2, 'bits': 4096}}

def featurize(smiles, radius, bits):
    return ECFPFingerprint(radius=radius, fp_size=bits, count=True, n_jobs=-1).transform(smiles)

def holm_adjust(pvals):
    """Holm step-down adjustment of a p-value family."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(np.argsort(p)):
        running = max(running, (m - rank) * p[i])
        adjusted[i] = min(1.0, running)
    return adjusted.tolist()

def split_indices(smiles, split, seed):
    if split == 'random':
        return train_test_split(np.arange(len(smiles)), test_size=TEST_FRACTION, random_state=seed)
    if split == 'scaffold':
        return randomized_scaffold_train_test_split(smiles, test_size=TEST_FRACTION, random_state=seed, return_indices=True)
    if split == 'scaffold_det':
        return scaffold_train_test_split(smiles, test_size=TEST_FRACTION, return_indices=True)
    raise ValueError(f'unknown split {split!r}')

def auroc_for(X, y, tr_idx, te_idx, seed):
    prep = Pipeline([('variance', VarianceThreshold()), ('scale', StandardScaler()), ('select', SelectKBest(f_classif, k=N_FEATURES))])
    prep.fit(X[tr_idx], y[tr_idx])
    X_tr, X_te = (prep.transform(X[tr_idx]), prep.transform(X[te_idx]))
    clf = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.1, subsample=0.8, random_state=seed, n_jobs=-1, verbosity=0)
    clf.fit(X_tr, y[tr_idx])
    return roc_auc_score(y[te_idx], clf.predict_proba(X_te)[:, 1])

def run(dataset=DATASET, split=SPLIT, n_seeds=N_REPEATS):
    frame = load_dataset(dataset)
    smiles, y = (frame['SMILES'].tolist(), frame['label'].to_numpy())
    settings = {'ecfp4': REFERENCE, **CHALLENGERS}
    matrices = {name: featurize(smiles, **cfg) for name, cfg in settings.items()}
    auc = {name: [] for name in settings}
    for seed in range(n_seeds):
        tr_idx, te_idx = split_indices(smiles, split, seed)
        for name, X in matrices.items():
            auc[name].append(auroc_for(X, y, np.asarray(tr_idx), np.asarray(te_idx), seed))
    ref = np.array(auc['ecfp4'])
    names = list(CHALLENGERS)
    raw = [float(ttest_rel(np.array(auc[n]), ref).pvalue) for n in names]
    p_adj = holm_adjust(raw)
    comparisons = [{'variant': n, 'delta_auroc': float(np.mean(auc[n]) - ref.mean()), 'p_raw': r, 'p_adj': a} for n, r, a in zip(names, raw, p_adj)]
    n_sig = sum((c['p_adj'] < ALPHA for c in comparisons))
    return {'dataset': dataset, 'split': split, 'claim': CLAIM, 'n_seeds': n_seeds, 'auroc_mean': float(ref.mean()), 'auroc_sd': float(ref.std(ddof=1)) if n_seeds > 1 else 0.0, 'comparisons': comparisons, 'conclusion': f'These results show that count ECFP4 with XGBoost is the right default for blood-brain-barrier models.'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', default=SPLIT, choices=['random', 'scaffold', 'scaffold_det'])
    ap.add_argument('--seeds', type=int, default=N_REPEATS)
    args = ap.parse_args()
    print(json.dumps(run(split=args.split, n_seeds=args.seeds), indent=2))
if __name__ == '__main__':
    main()

from pathlib import Path

import pytest

from kilter.core.findings import Kind
from kilter.core.tiers.t0_static import run_t0

REFS = Path(__file__).resolve().parents[1] / "references"


@pytest.mark.parametrize("name", ["bace_clean.py", "bbbp_clean.py"])
def test_clean_references_have_no_findings(name):
    findings, checks = run_t0((REFS / name).read_text(encoding="utf-8"), name)
    assert findings == []
    assert len(checks) == 3  # a pass is never silent


def classes(src):
    return {(f.defect_class, f.kind) for f in run_t0(src, "x.py")[0]}


LEAK_FULL_FIT = """
from sklearn.preprocessing import StandardScaler
def go(X, y, train_idx, test_idx):
    sc = StandardScaler()
    sc.fit(X, y)
    return sc.transform(X[train_idx]), sc.transform(X[test_idx])
"""
LEAK_SKLEARN_ORDER = """
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
def go(X, y):
    X = StandardScaler().fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X, y)
"""
LEAK_ON_TEST = """
from sklearn.preprocessing import StandardScaler
def go(X, train_idx, test_idx):
    sc = StandardScaler().fit(X[test_idx])
"""
FINE_FIT = """
from sklearn.preprocessing import StandardScaler
def go(X, y, train_idx, test_idx):
    sc = StandardScaler()
    A = sc.fit_transform(X[train_idx])
    B = sc.transform(X[test_idx])
"""


def test_d1_variants():
    assert ("D1", Kind.DEFECT) in classes(LEAK_FULL_FIT)
    assert ("D1", Kind.DEFECT) in classes(LEAK_SKLEARN_ORDER)
    assert ("D1", Kind.DEFECT) in classes(LEAK_ON_TEST)
    assert not classes(FINE_FIT)


def test_d3_random_when_scaffold_claimed_and_unstated():
    base = 'CLAIM = "generalisation to novel scaffolds"\ndef split_indices(s, split, seed):\n    pass\n'
    assert ("D3", Kind.DEFECT) in classes('SPLIT = "random"\n' + base)
    assert not classes('SPLIT = "scaffold"\n' + base)
    assert not classes('SPLIT = "random"\nCLAIM = "overall accuracy"\ndef split_indices(s, split, seed):\n    pass\n')
    caller = "def run(smiles, split='scaffold'):\n    return split_indices(smiles, split, 0)\n"
    assert ("D3", Kind.UNREPORTED) in classes(base + caller)
    assert not classes(base.replace("def split_indices", "def helper"))  # nothing is split, nothing to state


D4_BAD = """
from scipy.stats import ttest_rel
def go(groups, base):
    return [ttest_rel(g, base).pvalue for g in groups]
"""
D4_GOOD = D4_BAD.replace("return [", "p = [").replace("]\n", "]\n    p = false_discovery_control(p)\n    return p\n", 1)
D4_UNUSED = D4_BAD.replace("return [", "p = [").replace("]\n", "]\n    q = holm_adjust(p)\n    return p\n", 1)


def test_d4_variants():
    assert ("D4", Kind.DEFECT) in classes(D4_BAD)
    assert not classes(D4_GOOD)
    assert ("D4", Kind.DEFECT) in classes(D4_UNUSED)
    assert not classes("from scipy.stats import ttest_rel\ndef go(a, b):\n    return ttest_rel(a, b).pvalue\n")  # one test


def test_unparseable_is_inconclusive_not_clean():
    findings, checks = run_t0("def broken(:\n", "x.py")
    assert findings[0].kind is Kind.INCONCLUSIVE and checks == []

import importlib.util
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1] / "references" / "bace_clean.py"


@pytest.fixture(scope="module")
def ref():
    spec = importlib.util.spec_from_file_location("bace_clean", REF)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stated_protocol_matches_claim(ref):
    # D3 contract: the claim is about novel scaffolds, so the stated split must hold scaffolds out.
    assert ref.SPLIT == "scaffold"
    assert "scaffold" in ref.CLAIM


@pytest.mark.parametrize("split", ["random", "scaffold", "scaffold_det"])
def test_clean_run_produces_sane_metrics(ref, split):
    res = ref.run(split=split, n_seeds=2)
    assert 0.7 < res["auroc_mean"] < 0.99
    assert len(res["comparisons"]) == len(ref.VARIANTS)
    # Every reported p-value family member carries an adjusted value >= its raw value (D4 contract).
    assert all(c["p_adj"] >= c["p_raw"] for c in res["comparisons"])


def test_scaffold_train_test_do_not_share_scaffolds(ref):
    from rdkit.Chem.Scaffolds.MurckoScaffold import MurckoScaffoldSmiles

    from kilter.data import load_dataset

    smiles = load_dataset("bace")["SMILES"].tolist()
    train, test = ref.split_indices(smiles, "scaffold", seed=0)
    scaf = lambda idx: {MurckoScaffoldSmiles(smiles[i]) for i in idx}
    assert not (scaf(train) & scaf(test))

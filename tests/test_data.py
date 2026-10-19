import pytest

from kilter.data import load_dataset


# Sizes are the MoleculeNet counts (REF-14); BACE doc string in scikit-fingerprints says 1513.
@pytest.mark.parametrize("name,n", [("bace", 1513), ("bbbp", 2039)])
def test_dataset_loads(name, n):
    df = load_dataset(name)
    assert {"SMILES", "label"} <= set(df.columns)
    assert len(df) >= n - 50  # BBBP has a few unparseable rows in some distributions
    assert set(df["label"].unique()) <= {0, 1}


def test_unknown_dataset_rejected():
    with pytest.raises(ValueError):
        load_dataset("tox21")

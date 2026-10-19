"""Dataset loading. Phase 1 scope is BACE and BBBP only (blueprint §5.1)."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from skfp.datasets.moleculenet import load_bace, load_bbbp

_LOADERS = {"bace": load_bace, "bbbp": load_bbbp}
DATASETS = tuple(_LOADERS)


def data_dir() -> Path:
    """Cache location. Override with KILTER_DATA_DIR; default is <repo>/data (gitignored)."""
    return Path(os.environ.get("KILTER_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def load_dataset(name: str) -> pd.DataFrame:
    """Return a DataFrame with columns SMILES, label (binary int)."""
    key = name.lower()
    if key not in _LOADERS:
        raise ValueError(f"unknown dataset {name!r}; Phase 1 supports {DATASETS}")
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return _LOADERS[key](data_dir=d, as_frame=True)

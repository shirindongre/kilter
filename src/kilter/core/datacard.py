"""Data card: the facts about the dataset the critic may rely on (AD-2 input). Computed, never taken from the analyst."""
from __future__ import annotations

from kilter.data import load_dataset

TASKS = {
    "bace": "Binary classification of human beta-secretase 1 (BACE-1) inhibitors; metric AUROC (MoleculeNet).",
    "bbbp": "Binary classification of blood-brain-barrier penetration; metric AUROC (MoleculeNet).",
}


def data_card(dataset: str) -> dict:
    df = load_dataset(dataset)
    return {
        "dataset": dataset,
        "task": TASKS.get(dataset, ""),
        "n_molecules": int(len(df)),
        "positive_rate": round(float(df["label"].mean()), 3),
    }

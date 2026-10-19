"""Holdout ground truth (AIMS D-018), checked against the executed numbers, never against the LLM.

Needs the artifacts built by scripts/build_artifacts.py holdout; skipped if they are absent."""
import json
from pathlib import Path

import pytest

from kilter.defects.variants import generate_holdout
from kilter.eval.artifacts import ARTIFACT_DIR, ARTIFACT_SEEDS, FIXTURE_ARTIFACT_DIR, source_hash

VDIR = Path(__file__).resolve().parents[1] / "results" / "variants"


def artifact(v):
    p = VDIR / f"{v.id}.py"
    if not p.exists():
        return None
    key = f"{source_hash(p)[:16]}-s{ARTIFACT_SEEDS}.json"
    for d in (ARTIFACT_DIR, FIXTURE_ARTIFACT_DIR):
        if (d / key).exists():
            return json.loads((d / key).read_text(encoding="utf-8"))["result"]
    return None


def test_holdout_shape():
    h = generate_holdout()
    assert len(h) == 16 and {v.group for v in h} == {"holdout"}
    assert sum(v.clean for v in h) == 8 and sum(v.defect_class == "D5" for v in h) == 8
    assert len({v.id for v in h}) == 16


def test_honest_conclusions_are_true_and_subtle_ones_are_unsupported_by_the_numbers():
    checked = 0
    for v in generate_holdout():
        r = artifact(v)
        if r is None:
            pytest.skip("holdout artifacts not built")
        comps = r["comparisons"]
        n_sig = sum(c["p_adj"] < 0.05 for c in comps)
        # Premise shared by every holdout text: no alternative differs significantly after correction.
        assert n_sig == 0, v.id
        if v.clean:
            assert f"{n_sig} of {len(comps)}" in r["conclusion"] or "no alternative" in r["conclusion"].lower() \
                or "distinguishable" in r["conclusion"] or "noise" in r["conclusion"], v.id
        checked += 1
    assert checked == 16

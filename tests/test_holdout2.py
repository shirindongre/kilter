"""Holdout 2 ground truth (AIMS D-022), checked against the executed numbers, never against the LLM.

Needs the artifacts built by scripts/build_artifacts.py holdout2; skipped if they are absent."""
import json
from pathlib import Path

import pytest

from kilter.defects.variants import generate_holdout, generate_holdout2
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


def test_holdout2_shape_and_separation():
    h = generate_holdout2()
    assert len(h) == 16 and {v.group for v in h} == {"holdout2"}
    assert sum(v.clean for v in h) == 8 and sum(v.defect_class == "D5" for v in h) == 8
    ids = {v.id for v in h}
    assert len(ids) == 16 and not ids & {v.id for v in generate_holdout()}
    # Never share a conclusion with holdout 1: it is training data for the prompt this set evaluates.
    assert not {v.source for v in h} & {v.source for v in generate_holdout()}


def test_honest_texts_are_true_and_beyond_texts_assert_unmeasured_things():
    checked = 0
    for v in generate_holdout2():
        r = artifact(v)
        if r is None:
            pytest.skip("holdout2 artifacts not built")
        comps = r["comparisons"]
        # Premise shared by every text: nothing is significant after correction.
        assert all(c["p_adj"] >= 0.05 for c in comps), v.id
        if v.clean:
            c = r["conclusion"]
            assert "1 of" not in c and "2 of" not in c, v.id
            if "smaller than the split-to-split sd" in c or "every observed difference is smaller" in c:
                assert max(abs(x["delta_auroc"]) for x in comps) < r["auroc_sd"], v.id  # hard-coded structural claim
            if "ahead" in c or "gain from any alternative" in c:
                assert max(x["delta_auroc"] for x in comps) > 0, v.id
            assert "0 of" in c or "None of" in c or "No " in c or "not significant" in c, v.id
        else:
            # Every BEYOND text quotes real numbers; the leap is what no printed number can check.
            assert f"{r['auroc_mean']:.3f}" in r["conclusion"] or "adjusted p" in r["conclusion"] or "AUROC" in r["conclusion"], v.id
        checked += 1
    assert checked == 16

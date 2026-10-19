"""DAY 1 GATE (blueprint §5.3): T0+T1 catch >= 80% of injected D1-D4 with 0 false positives on the 8 clean
variants, and no LLM has been called. This test IS the gate; the tracker's P1.9 turns green only when it passes."""
from collections import defaultdict
from pathlib import Path

import pytest

from kilter.core.audit import audit_script
from kilter.defects.variants import DEFECT_CLASSES, generate_variants, write_variants
from kilter.eval.score import detected, localised, tiers_catching


@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    out = tmp_path_factory.mktemp("variants")
    variants = [v for v in generate_variants() if v.defect_class != "D5"]  # D5 belongs to Day 2 (no sound check)
    write_variants(variants, out)
    return [(v, audit_script(Path(out) / f"{v.id}.py")) for v in variants]


def test_no_llm_dependency_is_importable_by_the_sound_tiers():
    """Fresh interpreter, so earlier tests in this session cannot mask an import (AD-1: T0/T1 never touch an LLM)."""
    import subprocess
    import sys

    code = ("import sys, kilter.core.audit; "
            "bad = [m for m in sys.modules if m.split('.')[0] in {'langgraph','google','groq','openai','anthropic'}]; "
            "assert not bad, bad")
    subprocess.run([sys.executable, "-c", code], check=True)


def test_zero_false_positives_on_clean_variants(scored):
    fps = [(v.id, [f.check for f in r.findings]) for v, r in scored if v.clean and detected(v, r)]
    assert fps == [], f"false positives: {fps}"


def test_overall_and_per_class_detection(scored):
    per = defaultdict(lambda: [0, 0])
    for v, r in scored:
        if v.clean:
            continue
        per[v.defect_class][1] += 1
        per[v.defect_class][0] += detected(v, r)
    report = {c: f"{k}/{n}" for c, (k, n) in sorted(per.items())}
    total, hit = sum(n for _, n in per.values()), sum(k for k, _ in per.values())
    print("\nDay 1 gate detection by class:", report, f"overall {hit}/{total}")
    assert hit / total >= 0.80
    for cls in DEFECT_CLASSES:  # the aggregate must not hide a class that is not detected at all
        assert per[cls][0] / per[cls][1] >= 0.80, f"{cls}: {report[cls]}"


def test_tier_attribution_matches_the_blueprint_hypothesis(scored):
    """§4 expected tiers: D1/D4 -> T0, D2 -> T1, D3 -> T0+T1. Recorded as evidence, asserted loosely."""
    seen = defaultdict(set)
    for v, r in scored:
        seen[v.defect_class] |= tiers_catching(v, r)
    print("\nTiers that caught each class:", {k: sorted(s) for k, s in seen.items() if k})
    assert seen["D1"] == {"T0"} and seen["D4"] == {"T0"}
    assert seen["D2"] == {"T1"}
    assert seen["D3"] == {"T0", "T1"}


def test_localisation(scored):
    """Secondary metric (§8.2): T1 findings have no line, so only line-bearing findings can localise."""
    loc = {c: [localised(v, r) for v, r in scored if v.defect_class == c] for c in ("D1", "D3", "D4")}
    print("\nLocalisation (within +/-2 lines):", {c: f"{sum(x)}/{len(x)}" for c, x in loc.items()})
    assert all(all(x) for x in loc.values())

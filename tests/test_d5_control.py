"""D5 is the control for AD-1 (blueprint section 4): it has no sound check, so T0+T1 must detect none of it.
If this test ever fails, D5 is no longer a clean test of whether T2 adds anything."""
from pathlib import Path

from kilter.core.audit import audit_script
from kilter.core.findings import Verdict
from kilter.defects.variants import generate_variants, write_variants
from kilter.eval.score import detected


def test_sound_tiers_detect_none_of_d5(tmp_path):
    d5 = [v for v in generate_variants() if v.defect_class == "D5"]
    assert len(d5) == 8
    write_variants(d5, tmp_path)
    results = [(v, audit_script(Path(tmp_path) / f"{v.id}.py")) for v in d5]
    assert [v.id for v, r in results if detected(v, r)] == []
    assert all(r.verdict is Verdict.IN_KILTER for _, r in results)  # sound tiers pass them: the gap T2 must fill

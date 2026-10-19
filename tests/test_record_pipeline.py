"""AD-10: determinism and provenance. Needs results/variants + a built artifact for bace-b0-clean (scripts/build_artifacts.py)."""
import json
from pathlib import Path

import pytest

from kilter.core import record as rec
from kilter.eval.artifacts import ARTIFACT_SEEDS, artifact_for, source_hash
from kilter.graph.pipeline import audit_full
from kilter.llm import load_config

VARIANT = Path(__file__).resolve().parents[1] / "results" / "variants" / "bace-b0-clean.py"
ART = Path(__file__).resolve().parents[1] / "results" / "artifacts" / f"{source_hash(VARIANT)[:16]}-s{ARTIFACT_SEEDS}.json" if VARIANT.exists() else None

needs_variant = pytest.mark.skipif(not VARIANT.exists(), reason="run scripts/build_artifacts.py first")
needs_artifact = pytest.mark.skipif(ART is None or not ART.exists(), reason="artifact not built yet")


@needs_variant
def test_t0_t1_reproduce_bit_identically_and_record_is_tamper_evident(tmp_path):
    _, r1 = audit_full(VARIANT, use_t2=False, runs_dir=tmp_path)
    _, r2 = audit_full(VARIANT, use_t2=False, runs_dir=tmp_path)
    assert r1.tiers_sha256() == r2.tiers_sha256()                       # AD-10: T0/T1 bit-identical
    assert r1.run_id != r2.run_id and r1.input_sha256 == r2.input_sha256

    saved = json.loads((tmp_path / f"{r1.run_id}.json").read_text(encoding="utf-8"))
    assert rec.verify(saved)
    assert saved["code_sha256"] == rec.code_hash() and saved["arm"] == "A4" and saved["tokens"]["calls"] == 0
    saved["verdict"] = "OUT OF KILTER"
    assert not rec.verify(saved)                                        # any edit is detected


@needs_variant
@needs_artifact
def test_full_arm_replays_offline_from_fixtures(tmp_path, monkeypatch):
    """Demo-path property (section 5.7): with recorded fixtures, A3 needs no network and no API key."""
    monkeypatch.setenv("KILTER_LLM_MODE", "replay")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    res, r = audit_full(VARIANT, use_t2=True, runs_dir=tmp_path)
    t = r.tokens()
    assert t["calls"] == 1 and t["cached_calls"] == 1 and t["input"] > 0
    assert "T2.critic" in res.checks_run
    assert r.model["reported"] == [load_config()["pinned_for_reported_results"]["model"]]

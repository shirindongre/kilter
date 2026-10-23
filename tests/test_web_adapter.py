"""The web adapter re-shapes verifier output; it must never change a verdict (FRONTEND-SPEC section 8).

These tests build findings by hand and run them through the real adjudicator, so the verdict logic under test is
the verifier's own. Hand-built findings are test inputs only: nothing here is a reported result.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

import adapter  # noqa: E402
from kilter.core import record as rec  # noqa: E402
from kilter.core.adjudicator import adjudicate  # noqa: E402
from kilter.core.findings import Finding, Kind, Tier  # noqa: E402

SRC = "\n".join(f"source line {i}" for i in range(1, 81))
T0_CHECKS = ["T0.leakage", "T0.split-protocol", "T0.multiple-comparisons"]
T1_CHECKS = ["T1.duplicates", "T1.scaffold-overlap"]


def F(cls, tier, kind, line=None, check="T0.leakage", conf=1.0, msg="what is wrong", ev="the evidence"):
    return Finding(cls, Tier(tier), kind, msg, ev, check, "demo.py", line, conf)


def build(findings, checks, arm="A3", sample=None):
    result = adjudicate("some/dir/demo.py", findings, checks)
    call = {"input_tokens": 100, "output_tokens": 20, "thinking_tokens": 0, "seconds": 1.5, "cached": True,
            "model_reported": "gemini-test", "purpose": "T2.critic"}
    tiers = {"T0": rec.TierRun("T0", 0.01, T0_CHECKS, []), "T1": rec.TierRun("T1", 0.02, T1_CHECKS, [])}
    if arm == "A3":
        tiers["T2"] = rec.TierRun("T2", 0.0, ["T2.critic"], [], [call])
    record = rec.RunRecord(
        run_id=f"demo__{arm}__abc", arm=arm, variant_id="demo", input_sha256="in" * 32, code_sha256="co" * 32,
        created_utc="2026-10-23T00:00:00+00:00", seed=None,
        model={"provider": "google", "requested": "m", "reported": ["gemini-test"]} if arm == "A3" else {"provider": None},
        versions={"python": "3.11"}, tiers=tiers, verdict=result.verdict.value, findings=[f.to_dict() for f in result.findings],
        config={"dataset": "bbbp", "llm_mode": "replay"})
    return adapter.to_view(result, record, SRC, sample=sample)


def by_id(view):
    return {c["id"]: c["result"] for c in view["checks"]}


def test_sound_defect_holds_mark_at_t0_and_groups_two_witnesses():
    v = build([F("D1", "T0", Kind.DEFECT, 61), F("D1", "T2", Kind.DEFECT, 61, "T2.critic", 1.0)],
              [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert (v["verdict"], v["held_at"], v["mark"]) == ("out_of_kilter", "t0", "t0")
    (f,) = v["findings"]
    assert f["kind"] == "defect" and [w["tier"] for w in f["witnesses"]] == ["t0", "t2"]
    assert f["excerpt"]["from"] == 58 and f["excerpt"]["to"] == 64 and f["excerpt"]["line"] == 61
    assert f["remedy"].startswith("Fit the preprocessing") and f["confidence"] == 1.0
    assert by_id(v)["T0.leakage"] == "fired" and by_id(v)["T0.split-protocol"] == "clear"


def test_critic_alone_is_a_query_held_at_t2():
    v = build([F("D5", "T2", Kind.DEFECT, 70, "T2.critic", 0.9)], [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert (v["verdict"], v["held_at"]) == ("out_of_kilter", "t2")
    assert v["findings"][0]["kind"] == "query" and "Only the critic" in v["statement"]


def test_clean_run_is_in_kilter_and_states_its_bounds():
    v = build([], [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert (v["verdict"], v["held_at"], v["mark"]) == ("in_kilter", None, "clear")
    assert set(by_id(v).values()) == {"clear", "no_objection"} and v["bounds"] and v["checks_ran"] == 6


def test_missing_hooks_escalates_and_marks_t1_checks_could_not_run():
    hooks = F("D2", "T1", Kind.INCONCLUSIVE, None, "T1.hooks", msg="Script does not expose the Kilter hooks", ev="missing: run")
    v = build([hooks], T0_CHECKS, arm="A4")
    assert (v["verdict"], v["held_at"], v["mark"], v["unresolved_tier"]) == ("escalate", None, "esc", "t1")
    assert by_id(v)["T1.duplicates"] == "could_not_run" and by_id(v)["T0.leakage"] == "clear"
    (b,) = v["blockers"]
    assert b["tier"] == "t1" and b["command"] == "kilter audit demo.py --data bbbp" and b["decision_for_human"]
    assert v["checks_ran"] == 3 and v["findings"] == []


def test_hesitant_critic_escalates_without_convicting():
    v = build([F("D5", "T2", Kind.DEFECT, 70, "T2.critic", 0.55)], [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert v["verdict"] == "escalate" and v["findings"] == [] and by_id(v)["T2.critic"] == "query"
    assert v["blockers"][0]["title"].startswith("The critic suspects")


def test_low_confidence_critic_note_is_not_a_finding():
    v = build([F("D5", "T2", Kind.DEFECT, 70, "T2.critic", 0.2)], [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert v["verdict"] == "in_kilter" and v["findings"] == [] and v["notes"][0]["tier"] == "t2"
    assert by_id(v)["T2.critic"] == "no_objection"


def test_sensitivity_is_parsed_from_the_fixed_format_evidence():
    stated = F("D3", "T1", Kind.SENSITIVITY, None, "T1.split-sensitivity",
               msg="The reported metric depends on the split protocol (stated: 'scaffold'). AUROC moves by 0.111",
               ev="scaffold: 0.875; random: 0.893; scaffold_det: 0.782 (3 seeds each)")
    v = build([stated], [*T0_CHECKS, *T1_CHECKS, "T1.split-sensitivity"], arm="A4")
    (s,) = v["sensitivity"]
    assert s["seeds"] == 3 and s["as_written"]["label"] == "scaffold" and s["alternative"]["label"] == "scaffold_det"
    assert abs(s["delta"] - 0.111) < 1e-9 and "11.1 points" in s["headline"] and v["verdict"] == "in_kilter"
    unstated = F("D3", "T1", Kind.SENSITIVITY, None, "T1.split-sensitivity",
                 msg="depends on the split protocol (stated: not stated).", ev="random: 0.893; scaffold_det: 0.782 (3 seeds each)")
    (u,) = build([unstated], [*T0_CHECKS, *T1_CHECKS, "T1.split-sensitivity"], arm="A4")["sensitivity"]
    assert u["stated"] is False and "nobody wrote down" in u["headline"]


def test_ground_truth_outcomes():
    sample = lambda cls, line=None: {"id": "s", "kind": "variant", "planted_class": cls, "site_line": line}  # noqa: E731
    checks = [*T0_CHECKS, *T1_CHECKS]
    d3 = F("D3", "T0", Kind.DEFECT, 12, "T0.split-protocol")
    truth = lambda v: v["sample"]["truth"]  # noqa: E731
    assert truth(build([d3], checks, "A4", sample("D3", 12)))["outcome"] == "caught"
    assert truth(build([d3], checks, "A4", sample("D3", 12)))["site_match"] is True
    assert truth(build([d3], checks, "A4", sample("D1", 12)))["outcome"] == "wrong_class"
    assert truth(build([], checks, "A4", sample("D3", 12)))["outcome"] == "missed"
    assert truth(build([d3], checks, "A4", sample(None)))["outcome"] == "false_alarm"
    assert truth(build([], checks, "A4", sample(None)))["outcome"] == "clean_ok"


def test_digest_verifies_and_cost_is_measured_or_absent():
    v = build([], [*T0_CHECKS, *T1_CHECKS, "T2.critic"])
    assert v["provenance"]["digest_ok"] is True and v["cost"]["tokens_in"] == 100 and v["cost"]["usd_equivalent"] is None
    a4 = build([], [*T0_CHECKS, *T1_CHECKS], arm="A4")
    assert a4["cost"]["calls"] == 0 and a4["cost"]["model"] is None


# --- stored evaluation records (fleet view, D-025) ---------------------------------------------------

def stored(findings, checks, arm="A4", source=SRC.encode(), dataset="bbbp"):
    """A record dict as the evaluation would have saved it, built through the real adjudicator and RunRecord."""
    result = adjudicate("some/dir/demo.py", findings, checks)
    tiers = {"T0": rec.TierRun("T0", 0.01, T0_CHECKS, []), "T1": rec.TierRun("T1", 0.02, T1_CHECKS, [])}
    r = rec.RunRecord(
        run_id=f"demo__{arm}__abc", arm=arm, variant_id="demo", input_sha256=rec.sha256_bytes(source + dataset.encode()),
        code_sha256="co" * 32, created_utc="2026-10-23T00:00:00+00:00", seed=None, model={"provider": None},
        versions={"python": "3.11"}, tiers=tiers, verdict=result.verdict.value, findings=[f.to_dict() for f in result.findings],
        config={"dataset": dataset, "llm_mode": "replay"})
    return r.to_dict()


def test_stored_cell_reads_outcome_and_depth_from_stored_findings():
    checks = [*T0_CHECKS, *T1_CHECKS]
    def cell(findings, cls, line=None):
        d = stored(findings, checks)
        return adapter.stored_cell(adapter.result_from_record(d), d["verdict"], cls, line)

    d3 = F("D3", "T0", Kind.DEFECT, 12, "T0.split-protocol")
    c = cell([d3], "D3", 12)
    assert (c["verdict"], c["held_at"], c["convicted"], c["outcome"], c["site_match"], c["consistent"]) == \
        ("out_of_kilter", "t0", ["D3"], "caught", True, True)
    assert cell([d3], "D1")["outcome"] == "wrong_class" and cell([], "D3")["outcome"] == "missed"
    assert cell([d3], None)["outcome"] == "false_alarm" and cell([], None)["outcome"] == "clean_ok"
    critic_only = cell([F("D5", "T2", Kind.DEFECT, 70, "T2.critic", 0.95)], "D5", 70)
    assert (critic_only["held_at"], critic_only["outcome"]) == ("t2", "caught")
    hesitant = cell([F("D5", "T2", Kind.DEFECT, 70, "T2.critic", 0.55)], "D5", 70)
    assert (hesitant["verdict"], hesitant["held_at"], hesitant["outcome"]) == ("escalate", None, "escalated")
    two = cell([d3, F("D2", "T1", Kind.DEFECT, None, "T1.duplicates")], "D3", 12)
    assert two["convicted"] == ["D2", "D3"] and two["held_at"] == "t0"


def test_stored_cell_flags_a_stored_verdict_the_findings_do_not_support():
    d = stored([F("D3", "T0", Kind.DEFECT, 12, "T0.split-protocol")], [*T0_CHECKS, *T1_CHECKS])
    result = adapter.result_from_record(d)
    assert adapter.stored_cell(result, "IN KILTER", "D3", 12)["consistent"] is False


def test_view_from_stored_keeps_the_stored_digest_and_checks_the_script_bytes():
    d = stored([F("D1", "T0", Kind.DEFECT, 61)], [*T0_CHECKS, *T1_CHECKS])
    v = adapter.view_from_stored(d, SRC.encode(), sample={"id": "demo", "kind": "variant", "planted_class": "D1", "site_line": 61})
    assert v["stored"] is True and (v["verdict"], v["held_at"]) == ("out_of_kilter", "t0")
    assert v["provenance"]["record_sha256"] == d["record_sha256"] and v["provenance"]["digest_ok"] is True
    assert v["provenance"]["source_matches"] is True and v["sample"]["truth"]["outcome"] == "caught"
    assert adapter.view_from_stored(d, b"another script", sample=None)["provenance"]["source_matches"] is False
    edited = dict(d, verdict="IN KILTER")
    assert adapter.view_from_stored(edited, SRC.encode())["provenance"]["digest_ok"] is False


def test_rebuilt_record_reproduces_the_stored_digest():
    d = stored([F("D1", "T0", Kind.DEFECT, 61)], [*T0_CHECKS, *T1_CHECKS])
    assert adapter.record_from_dict(d).to_dict() == d


def test_fleet_counting_and_totals():
    import fleet
    cells = [{"outcome": "caught", "convicted": ["D2", "D3"], "verdict": "out_of_kilter"},
             {"outcome": "missed", "convicted": [], "verdict": "in_kilter"},
             {"outcome": "escalated", "convicted": [], "verdict": "escalate"}]
    c = fleet._count(cells)
    assert c["n"] == 3 and c["outcomes"] == {"caught": 1, "missed": 1, "escalated": 1}
    assert c["predicted"] == {"D2": 1, "D3": 1, "pass": 1, "escalate": 1} and c["multi"] == 1
    t = fleet._totals({"D5": c, "clean": {"n": 2, "outcomes": {"false_alarm": 1, "clean_ok": 1}}}, [0.1, 0.9], None)
    assert (t["defective"], t["caught"], t["missed"], t["escalated"], t["clean"], t["false_alarm"]) == (3, 1, 1, 1, 2, 1)
    assert t["detect_ci"] == [0.1, 0.9] and t["fp_ci"] is None
    assert fleet._hits([{"outcome": "false_alarm"}, {"outcome": "clean_ok"}], clean=True) == 1


results_present = (Path(__file__).resolve().parents[1] / "results" / "runs" / "A4").is_dir()


@pytest.mark.skipif(not results_present, reason="results/ (the evaluation's records) is not on this machine")
def test_fleet_reads_every_variant_and_its_counts_agree_with_the_evaluations_summaries():
    import fleet
    f = fleet.load()
    p = f.payload
    assert len(p["variants"]) == 80 and {s["id"]: s["n"] for s in p["sets"]} == {"main": 48, "holdout": 16, "holdout2": 16}
    assert p["reconciliation"]["disagree"] == [] and p["reconciliation"]["checked"] > 0
    assert p["problems"] == [] and p["provenance"]["digests_ok"] == p["provenance"]["records"]
    assert all(c["consistent"] for v in p["variants"] for c in v["cells"].values())
    for run_id in list(f._runs)[:6]:
        saved = f.saved(run_id)
        assert saved["view"]["stored"] and saved["view"]["provenance"]["source_matches"] and saved["view"]["provenance"]["digest_ok"]
    assert f.saved("not-a-run") is None

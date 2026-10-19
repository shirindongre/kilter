from kilter.core.adjudicator import adjudicate
from kilter.core.findings import Finding, Kind, Tier, Verdict


def t2(conf, cls="D5", kind=Kind.DEFECT):
    return Finding(cls, Tier.T2, kind, "overclaim", "ev", "T2.critic", "x.py", None, conf)


def t0(kind=Kind.DEFECT):
    return Finding("D1", Tier.T0, kind, "m", "e", "T0.leakage", "x.py", 5)


def verdict(findings):
    return adjudicate("x.py", findings, ["T0.leakage"]).verdict


def test_nothing_found_is_in_kilter():
    assert verdict([]) is Verdict.IN_KILTER


def test_sound_tier_decides_alone():
    assert verdict([t0()]) is Verdict.OUT_OF_KILTER


def test_t2_must_clear_the_bar_to_convict():
    assert verdict([t2(0.9)]) is Verdict.OUT_OF_KILTER
    assert verdict([t2(0.7)]) is Verdict.OUT_OF_KILTER
    assert verdict([t2(0.55)]) is Verdict.ESCALATE      # suspicion without confidence asks a human
    assert verdict([t2(0.2)]) is Verdict.IN_KILTER      # low confidence is kept as a note only


def test_t2_abstention_escalates_but_never_overrides_a_sound_conviction():
    unsure = t2(0.0, "OTHER", Kind.INCONCLUSIVE)
    assert verdict([unsure]) is Verdict.ESCALATE
    assert verdict([unsure, t0()]) is Verdict.OUT_OF_KILTER


def test_thresholds_are_sweepable_for_the_calibration_curve():
    f = [t2(0.55)]
    assert adjudicate("x", f, [], convict_at=0.5).verdict is Verdict.OUT_OF_KILTER
    assert adjudicate("x", f, [], convict_at=0.9, escalate_at=0.6).verdict is Verdict.IN_KILTER


def test_low_confidence_t2_is_kept_as_information():
    r = adjudicate("x", [t2(0.2)], [])
    assert r.findings[0].kind is Kind.SENSITIVITY and "low-confidence" in r.findings[0].message

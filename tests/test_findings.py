from kilter.core.findings import AuditResult, Finding, Kind, Tier, Verdict


def f(kind, cls="D1", line=3):
    return Finding(cls, Tier.T0, kind, "m", "e", "T0.x", file="a.py", line=line)


def test_verdict_precedence():
    assert AuditResult("a.py").verdict is Verdict.IN_KILTER
    assert AuditResult("a.py", [f(Kind.SENSITIVITY)]).verdict is Verdict.IN_KILTER  # informational only
    assert AuditResult("a.py", [f(Kind.INCONCLUSIVE)]).verdict is Verdict.ESCALATE
    assert AuditResult("a.py", [f(Kind.INCONCLUSIVE), f(Kind.DEFECT)]).verdict is Verdict.OUT_OF_KILTER
    assert AuditResult("a.py", [f(Kind.UNREPORTED, "D3")]).verdict is Verdict.OUT_OF_KILTER  # AD-9 flags unreported


def test_site_and_serialisation():
    x = f(Kind.DEFECT)
    assert x.site == "a.py:3"
    d = AuditResult("a.py", [x], ["T0.leakage"]).to_dict()
    assert d["verdict"] == "OUT OF KILTER" and d["findings"][0]["tier"] == "T0"
    assert d["findings"][0]["site"] == "a.py:3"

"""T2 variant: a critic prompt aimed at conclusions that reach BEYOND the data (AIMS D-022).

The frozen prompt (t2_critic.SYSTEM, D-015) checks claims against the printed numbers and misses claims that no
printed number can confirm or refute (L-010). This variant is a SEPARATE, named prompt: the frozen one is imported
and left untouched, and only the three sentences below are replaced, so the diff between the two prompts is exactly
what the experiment tests. The text was written from the class definition and the gap described in L-010 only;
before the first call it was diffed against defects/holdout2.py for shared vocabulary (M-003) and against holdout 1.

Evaluated once on holdout 2 (authored before this prompt existed) next to the frozen prompt. It is not wired into
the audit graph: A3 and every reported Phase 1 number still use the frozen prompt.
"""
from __future__ import annotations

from dataclasses import asdict

from kilter import llm
from kilter.core import record as rec
from kilter.core.findings import Finding, Kind, Tier
from kilter.core.tiers import t2_critic
from kilter.core.tiers.t2_critic import CHECK_ID, CriticReport, T2Output, build_prompt

_D5 = "D5 the written conclusion claims more than the computed numbers support."
_COMPARE = "- Compare every quantitative or comparative statement in the conclusion with the numbers in the result.\n"
_HEDGED = "- A correct, appropriately hedged conclusion is NOT an issue. Do not flag style"

_D5_NEW = ("D5 the written conclusion claims more than the executed analysis supports: it misstates or over-reads the "
           "computed numbers, or it asserts something the analysis never measured.")
_SCOPE_RULE = (
    _COMPARE
    + "- Then take every remaining statement in the conclusion and ask what in the code, result or data card would "
      "have to be true for it to hold. A statement about data, populations, tasks, methods or settings the analysis "
      "did not use; about a cause or mechanism the analysis did not vary; about work outside this analysis; or about "
      "whether the result is good enough to rely on or use, needs its own evidence in what you were given. A good "
      "score on the evaluation that was run is not evidence for any of these. If that evidence is absent, report D5, "
      "name the unsupported statement and say what is missing.\n"
)
_HEDGED_NEW = ("- A conclusion that reports what was measured, and recommends a choice only within what was measured, "
               "is NOT an issue, however firmly it is worded. Do not flag style")

assert all(s in t2_critic.SYSTEM for s in (_D5, _COMPARE, _HEDGED)), "frozen T2 SYSTEM changed; update t2_scope"
SYSTEM_SCOPE = t2_critic.SYSTEM.replace(_D5, _D5_NEW).replace(_COMPARE, _SCOPE_RULE).replace(_HEDGED, _HEDGED_NEW)
PROMPT_SHA256 = rec.sha256_bytes(SYSTEM_SCOPE.encode())


def run_t2_scope(source: str, artifact: dict, card: dict, prior: list[Finding] | None, checks: list[str] | None,
                 filename: str = "<script>") -> T2Output:
    """Same input, schema and parsing as t2_critic.run_t2; only the system prompt differs."""
    resp = llm.generate(build_prompt(source, artifact, card, prior, checks), system=SYSTEM_SCOPE,
                        response_schema=CriticReport, max_output_tokens=2048)
    call = {k: v for k, v in asdict(resp).items() if k != "text"} | {"purpose": "T2.critic.scope"}
    try:
        report = CriticReport.model_validate_json(resp.text)
    except Exception as e:  # unparseable output is a result (ESCALATE), not a crash
        bad = Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "The critic returned output that could not be parsed.",
                      f"{type(e).__name__}", CHECK_ID, filename)
        return T2Output([bad], None, call, resp.text)
    findings = [Finding(f.defect_class, Tier.T2, Kind.DEFECT, f.claim, f.evidence, CHECK_ID, filename, f.line,
                        max(0.0, min(1.0, f.confidence))) for f in report.findings]
    if report.assessment == "unsure" and not findings:
        findings = [Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "The critic could not decide.", report.notes,
                            CHECK_ID, filename)]
    return T2Output(findings, report, call, resp.text)

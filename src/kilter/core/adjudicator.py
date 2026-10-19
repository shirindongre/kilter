"""Adjudicator: turns tier outputs into IN KILTER / OUT OF KILTER / ESCALATE (AD-7).

Sound tiers decide on their own. The unsound T2 tier must clear a confidence bar to convict, and sits in a band
where it can only ask a human to look. Both thresholds are `[my judgment]`; raw T2 confidences are kept in the
run record so the abstention-calibration curve (section 8.2) can be recomputed at any threshold.
"""
from __future__ import annotations

from dataclasses import replace

from kilter.core.findings import AuditResult, Finding, Kind, Tier

CONVICT_AT = 0.70     # T2 confidence at or above which T2 alone may declare OUT OF KILTER
ESCALATE_AT = 0.40    # between this and CONVICT_AT: ESCALATE (a human should look); below: informational


def adjudicate(
    target: str,
    findings: list[Finding],
    checks_run: list[str],
    *,
    convict_at: float = CONVICT_AT,
    escalate_at: float = ESCALATE_AT,
) -> AuditResult:
    final: list[Finding] = []
    for f in findings:
        if f.tier is not Tier.T2 or f.kind is not Kind.DEFECT:
            final.append(f)  # T0/T1 findings and T2 abstentions pass through untouched
        elif f.confidence >= convict_at:
            final.append(f)
        elif f.confidence >= escalate_at:
            final.append(replace(f, kind=Kind.INCONCLUSIVE,
                                 message=f"T2 suspects, but not confidently ({f.confidence:.2f}): {f.message}"))
        else:
            final.append(replace(f, kind=Kind.SENSITIVITY, message=f"T2 low-confidence note ({f.confidence:.2f}): {f.message}"))
    return AuditResult(target=target, findings=final, checks_run=checks_run)

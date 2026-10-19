"""Score an audit against a variant's planted ground truth (blueprint §8.2: detection, FPR, localisation)."""
from __future__ import annotations

from kilter.core.findings import AuditResult, Kind, Verdict
from kilter.defects.variants import Variant

LINE_TOLERANCE = 2  # a finding within +/-2 lines of the planted site counts as localised


def detected(variant: Variant, result: AuditResult) -> bool:
    """Defective variant: a finding of the planted class. Clean variant: True means a false positive."""
    if variant.clean:
        return result.verdict is Verdict.OUT_OF_KILTER
    return bool(result.of_class(variant.defect_class))


def localised(variant: Variant, result: AuditResult) -> bool:
    if variant.clean or variant.site_line is None:
        return False
    return any(f.line is not None and abs(f.line - variant.site_line) <= LINE_TOLERANCE
               for f in result.of_class(variant.defect_class))


def tiers_catching(variant: Variant, result: AuditResult) -> set[str]:
    return {f.tier.value for f in result.of_class(variant.defect_class)} if not variant.clean else set()

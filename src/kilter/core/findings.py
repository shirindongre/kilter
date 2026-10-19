"""What a finding is, and what an audit returns (AD-7). Stable on purpose: §5.7's verdict screen renders it."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Tier(str, Enum):
    T0 = "T0"  # static analysis (sound)
    T1 = "T1"  # runtime assertion (sound)
    T2 = "T2"  # LLM critic (unsound, last)


class Kind(str, Enum):
    DEFECT = "defect"              # a check fired: something is wrong
    UNREPORTED = "unreported"      # methodology not stated; AD-9 flags this, never asserts a single correct method
    SENSITIVITY = "sensitivity"    # informational: how far the result moves under an alternative choice
    INCONCLUSIVE = "inconclusive"  # the check could not decide; drives ESCALATE


class Verdict(str, Enum):
    IN_KILTER = "IN KILTER"
    OUT_OF_KILTER = "OUT OF KILTER"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class Finding:
    defect_class: str          # "D1".."D10", see defects/taxonomy.yaml
    tier: Tier
    kind: Kind
    message: str
    evidence: str
    check: str                 # id of the check that produced it, e.g. "T0.leakage"
    file: str | None = None
    line: int | None = None
    confidence: float = 1.0    # deterministic tiers report 1.0 when a rule fires; T2 will grade

    @property
    def site(self) -> str | None:
        if self.file is None:
            return None
        return f"{self.file}:{self.line}" if self.line else self.file

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"], d["kind"], d["site"] = self.tier.value, self.kind.value, self.site
        return d


@dataclass
class AuditResult:
    target: str
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)  # so an IN KILTER is never a silent pass

    @property
    def verdict(self) -> Verdict:
        if any(f.kind in (Kind.DEFECT, Kind.UNREPORTED) for f in self.findings):
            return Verdict.OUT_OF_KILTER
        if any(f.kind is Kind.INCONCLUSIVE for f in self.findings):
            return Verdict.ESCALATE
        return Verdict.IN_KILTER

    def of_class(self, defect_class: str) -> list[Finding]:
        return [f for f in self.findings if f.defect_class == defect_class and f.kind in (Kind.DEFECT, Kind.UNREPORTED)]

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "verdict": self.verdict.value,
            "checks_run": self.checks_run,
            "findings": [f.to_dict() for f in self.findings],
        }

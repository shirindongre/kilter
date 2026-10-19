"""Run the sound tiers over one script. T2 (LLM critic) and the full adjudicator arrive on Day 2."""
from __future__ import annotations

from pathlib import Path

from kilter.core.findings import AuditResult
from kilter.core.tiers.t0_static import run_t0
from kilter.core.tiers.t1_runtime import run_t1


def audit_script(path: str | Path, *, run_runtime: bool = True, sensitivity: bool = False) -> AuditResult:
    path = Path(path)
    f0, c0 = run_t0(path.read_text(encoding="utf-8"), path.name)
    findings, checks = list(f0), list(c0)
    if run_runtime:
        f1, c1 = run_t1(path, sensitivity=sensitivity)
        findings += f1
        checks += c1
    return AuditResult(target=str(path), findings=findings, checks_run=checks)

"""The evaluation arms (blueprint 8.1). Phase 1 runs A0, A1, A3, A4; A2 is deferred to Phase 2.

  A0  no verification: the analysis is accepted as-is (the floor)
  A1  one LLM instance reviews, then critiques its own review in the SAME conversation (what everyone builds)
  A3  T0 + T1 + T2: the full tiered verifier
  A4  T0 + T1 only (the honest control: if A4 ~ A3 the LLM tier is not earning its cost)

Token accounting (AD-3): every arm's run record carries input / output / thinking tokens and wall-clock. A1 makes
two calls and A3 one, so A3 spends LESS than A1; comparisons are therefore at equal-or-lower cost for A3, and
A0/A4 report their unused budget as a saving rather than hiding it.
"""
from __future__ import annotations

import ast
import time
from dataclasses import asdict
from pathlib import Path

from kilter import llm
from kilter.core import record as rec
from kilter.core.adjudicator import adjudicate
from kilter.core.astutil import module_constants
from kilter.core.datacard import data_card
from kilter.core.findings import AuditResult, Finding, Kind, Tier
from kilter.core.tiers import t2_critic
from kilter.core.tiers.t2_critic import CriticReport, build_prompt
from kilter.eval.artifacts import artifact_for
from kilter.graph.pipeline import RUNS_DIR, audit_full, make_record

ARMS = ("A0", "A1", "A3", "A4")

# Same role and class definitions as T2, minus everything about automated checks (A1 has none).
_INPUTS = ("You are given: the analysis code (with line numbers), the result it produced when executed, a data card, "
           "and the output of automated checks that already ran.")
_RULE = ("- Automated checks are reliable when they fire. Do not repeat what they already reported unless you can add to it. "
         "Their silence does not prove the analysis is valid, so still look for issues they cannot see.\n")
# Fail loudly if T2's prompt text changes, rather than silently running A1 on a mismatched prompt.
assert _INPUTS in t2_critic.SYSTEM and _RULE in t2_critic.SYSTEM, "T2 SYSTEM changed; update A1_SYSTEM"
A1_SYSTEM = t2_critic.SYSTEM.replace(
    _INPUTS, "You are given: the analysis code (with line numbers), the result it produced when executed, and a data card."
).replace(_RULE, "")

SELF_CRITIQUE = (
    "Now critique your own review above. Which of your findings are wrong (not actually a problem), and what did you "
    "miss? Re-examine the code and the numbers, then return your FINAL review in the same JSON format."
)


def _findings(report: CriticReport, fname: str, abstain_note: str) -> list[Finding]:
    out = [Finding(f.defect_class, Tier.T2, Kind.DEFECT, f.claim, f.evidence, "A1.self-critique", fname, f.line,
                   max(0.0, min(1.0, f.confidence))) for f in report.findings]
    if report.assessment == "unsure" and not out:
        out = [Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "The model could not decide.", abstain_note, "A1.self-critique", fname)]
    return out


def run_a1(path: Path, variant_id: str, runs_dir: Path = RUNS_DIR) -> tuple[AuditResult, rec.RunRecord]:
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    ds = module_constants(ast.parse(source)).get("DATASET", (None, 0))[0]
    card, art = data_card(ds), artifact_for(path)
    t0 = time.perf_counter()
    first_prompt = build_prompt(source, art, card, None, None)
    kw = dict(system=A1_SYSTEM, response_schema=CriticReport, max_output_tokens=2048)
    r1 = llm.generate(first_prompt, **kw)
    r2 = llm.generate(SELF_CRITIQUE, history=[(first_prompt, r1.text)], **kw)
    calls = [{k: v for k, v in asdict(r).items() if k != "text"} | {"purpose": f"A1.turn{i}"} for i, r in enumerate((r1, r2), 1)]
    try:
        findings = _findings(CriticReport.model_validate_json(r2.text), path.name, "")
    except Exception as e:
        findings = [Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "Unparseable final review.", type(e).__name__, "A1.self-critique", path.name)]
    result = adjudicate(str(path), findings, ["A1.self-critique"])
    tiers = {"A1": rec.TierRun("A1", time.perf_counter() - t0, ["A1.self-critique"], [f.to_dict() for f in findings], calls)}
    r = make_record(path, ds, "A1", variant_id, tiers, result, use_t2=True)
    r.save(runs_dir)
    return result, r


def run_a0(path: Path, variant_id: str, runs_dir: Path = RUNS_DIR) -> tuple[AuditResult, rec.RunRecord]:
    path = Path(path)
    ds = module_constants(ast.parse(path.read_text(encoding="utf-8"))).get("DATASET", (None, 0))[0]
    result = AuditResult(str(path), [], ["A0.accept-as-is"])
    r = make_record(path, ds, "A0", variant_id, {"A0": rec.TierRun("A0", 0.0, ["A0.accept-as-is"], [])}, result, use_t2=False)
    r.save(runs_dir)
    return result, r


def run_arm(arm: str, path: Path, variant_id: str, runs_dir: Path) -> tuple[AuditResult, rec.RunRecord]:
    if arm == "A0":
        return run_a0(path, variant_id, runs_dir)
    if arm == "A1":
        return run_a1(path, variant_id, runs_dir)
    if arm in ("A3", "A4"):
        return audit_full(path, use_t2=(arm == "A3"), variant_id=variant_id, runs_dir=runs_dir)
    raise ValueError(f"unknown arm {arm!r}; Phase 1 arms are {ARMS}")

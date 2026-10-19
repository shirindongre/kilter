"""T2: the LLM critic (AD-1, AD-2). Unsound, last, and isolated from the author.

The critic sees ONLY: the analysis code, the executed result, the data card, and what T0/T1 reported.
It never sees an analyst prompt, chain of thought or intermediate reasoning (none exist in audit mode, AD-8,
and the interface makes it impossible to pass them). Separate conversation, one structured call.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, Field

from kilter import llm
from kilter.core.findings import Finding, Kind, Tier

CHECK_ID = "T2.critic"


class CriticFinding(BaseModel):
    defect_class: Literal["D1", "D2", "D3", "D4", "D5", "OTHER"]
    line: int | None = Field(None, description="1-indexed line of the code the issue lives at, if it is in the code")
    claim: str = Field(description="One sentence: what is wrong")
    evidence: str = Field(description="The specific code or numbers that show it")
    confidence: float = Field(description="0 to 1: probability this is a genuine statistical-validity problem")


class CriticReport(BaseModel):
    assessment: Literal["no_issue", "issue", "unsure"]
    findings: list[CriticFinding]
    notes: str = Field(description="One or two sentences on what you checked")


SYSTEM = """You are an independent reviewer of computational analyses in cheminformatics. You check whether an \
analysis is statistically valid and whether its written conclusion is supported by its computed numbers. You did \
not write the analysis and you have no access to whoever did.

You are given: the analysis code (with line numbers), the result it produced when executed, a data card, and the \
output of automated checks that already ran.

Issue classes:
D1 test data leaks into preprocessing or model fitting (scaler/selector/imputer fit on all rows).
D2 identical or near-identical molecules in both train and test.
D3 the train/test split protocol is unstated, or does not match what the analysis claims to show.
D4 many significance tests are run and the p-values are reported without multiple-comparison correction.
D5 the written conclusion claims more than the computed numbers support.
OTHER any other statistical-validity problem.

Rules:
- Judge only what the code, results and data card show. Do not speculate about intent.
- Compare every quantitative or comparative statement in the conclusion with the numbers in the result.
- Automated checks are reliable when they fire. Do not repeat what they already reported unless you can add to it. \
Their silence does not prove the analysis is valid, so still look for issues they cannot see.
- A correct, appropriately hedged conclusion is NOT an issue. Do not flag style, wording preferences or \
hypothetical improvements.
- confidence is your honest probability that the issue is real. Use "unsure" only when you genuinely cannot decide.
- Return JSON matching the schema. Use an empty findings list when there is no issue."""


def numbered(source: str) -> str:
    return "\n".join(f"{i:4d} | {line}" for i, line in enumerate(source.splitlines(), start=1))


def _checks_summary(findings: list[Finding], checks: list[str]) -> str:
    if not checks:
        return "No automated checks ran."
    lines = [f"Checks run: {', '.join(checks)}."]
    reported = [f for f in findings if f.kind in (Kind.DEFECT, Kind.UNREPORTED, Kind.SENSITIVITY)]
    if not reported:
        lines.append("They reported nothing.")
    for f in reported:
        lines.append(f"- [{f.tier.value}] {f.defect_class} ({f.kind.value}){f' line {f.line}' if f.line else ''}: {f.message} "
                     f"Evidence: {f.evidence}")
    return "\n".join(lines)


def build_prompt(source: str, artifact: dict, card: dict, prior: list[Finding] | None, checks: list[str] | None) -> str:
    result = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in artifact["result"].items()}
    parts = [
        "## Data card\n" + json.dumps(card, indent=2),
        f"## Analysis code\n{numbered(source)}",
        f"## Executed result (run with {artifact['n_seeds']} seeds)\n" + json.dumps(result, indent=2),
    ]
    if checks is not None:
        parts.append("## Automated checks\n" + _checks_summary(prior or [], checks))
    parts.append("Review this analysis.")
    return "\n\n".join(parts)


@dataclass
class T2Output:
    findings: list[Finding]
    report: CriticReport | None
    call: dict            # token/latency accounting for the record
    raw_text: str


def run_t2(
    source: str,
    artifact: dict,
    card: dict,
    prior: list[Finding] | None,
    checks: list[str] | None,
    filename: str = "<script>",
) -> T2Output:
    """`prior`/`checks` are T0/T1 output; pass None for both to run the critic alone (the A2 ablation)."""
    resp = llm.generate(
        build_prompt(source, artifact, card, prior, checks),
        system=SYSTEM,
        response_schema=CriticReport,
        max_output_tokens=2048,
    )
    call = {k: v for k, v in asdict(resp).items() if k != "text"} | {"purpose": "T2.critic"}
    try:
        report = CriticReport.model_validate_json(resp.text)
    except Exception as e:  # malformed or truncated JSON is a result, not a crash: it becomes ESCALATE
        bad = Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "The critic returned output that could not be parsed.",
                      f"{type(e).__name__}", CHECK_ID, filename)
        return T2Output([bad], None, call, resp.text)

    findings = [
        Finding(f.defect_class, Tier.T2, Kind.DEFECT, f.claim, f.evidence, CHECK_ID, filename, f.line,
                max(0.0, min(1.0, f.confidence)))
        for f in report.findings
    ]
    if report.assessment == "unsure" and not findings:
        findings = [Finding("OTHER", Tier.T2, Kind.INCONCLUSIVE, "The critic could not decide.", report.notes, CHECK_ID, filename)]
    return T2Output(findings, report, call, resp.text)

"""The product surface (blueprint 5.7): the verdict screen and the handable report.md.

The screen is deterministic by design: no run ids, timestamps or wall-clock for the deterministic tiers, so the
cached demo prints the same bytes every time. LLM seconds and tokens come from the recorded call.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kilter.core import record as rec
from kilter.core.findings import AuditResult, Finding, Kind, Tier, Verdict

TAXONOMY = yaml.safe_load((Path(__file__).parent / "defects" / "taxonomy.yaml").read_text(encoding="utf-8"))
TIER_LABEL = {"T0": "T0 static", "T1": "T1 runtime", "T2": "T2 critic"}
STYLE = {Verdict.IN_KILTER: "bold white on green4", Verdict.OUT_OF_KILTER: "bold white on red3",
         Verdict.ESCALATE: "bold black on dark_orange"}
TAGLINE = {
    Verdict.IN_KILTER: "No defect found by any tier that ran.",
    Verdict.OUT_OF_KILTER: "At least one tier found a defect.",
    Verdict.ESCALATE: "Not enough evidence to decide. A human should look.",
}
MARK = {Kind.DEFECT: ("x", "red"), Kind.UNREPORTED: ("?", "dark_orange"), Kind.INCONCLUSIVE: ("~", "dark_orange"),
        Kind.SENSITIVITY: ("i", "cyan")}


def class_name(code: str) -> str:
    return TAXONOMY.get(code, {}).get("name", "Other statistical-validity issue")


def _group(findings: list[Finding]) -> list[tuple[Finding, list[Finding]]]:
    """Collapse findings of the same class and kind raised by several tiers into one block (lowest tier leads),
    so independent agreement between a sound tier and the critic reads as one finding with two witnesses."""
    groups: dict[tuple[str, Kind], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.defect_class, f.kind), []).append(f)
    return [(sorted(g, key=lambda x: x.tier.value)[0], sorted(g, key=lambda x: x.tier.value)) for g in groups.values()]


def _finding_block(f: Finding, witnesses: list[Finding] | None = None) -> Text:
    witnesses = witnesses or [f]
    mark, colour = MARK[f.kind]
    t = Text()
    t.append(f" {mark} ", style=f"bold {colour}")
    t.append(f"{f.defect_class}  ", style="bold")
    t.append(class_name(f.defect_class))
    t.append(f"\n     caught by ", style="dim")
    for w in witnesses:
        t.append(f" {TIER_LABEL[w.tier.value]} ", style="bold black on grey70")
        t.append(" ")
    site = next((w.site for w in witnesses if w.site), None)
    if site:
        t.append(f" {site}", style="bold")
    t2 = next((w for w in witnesses if w.tier is Tier.T2 and w.kind in (Kind.DEFECT, Kind.INCONCLUSIVE)), None)
    if t2 is not None:
        t.append(f"  critic confidence {t2.confidence:.2f}", style="dim")
    t.append(f"\n     {f.message}", style="")
    t.append(f"\n     evidence: {f.evidence}", style="dim")
    return t


def _cost_line(record: rec.RunRecord) -> str:
    tk = record.tokens()
    if not tk["calls"]:
        return "no LLM call: deterministic tiers only, 0 tokens"
    secs = sum(c["seconds"] for t in record.tiers.values() for c in t.llm_calls)
    cached = " (replayed from recorded call)" if tk["cached_calls"] == tk["calls"] else ""
    return (f"{tk['input']:,} in / {tk['output_billed']:,} out tokens . {secs:.1f}s LLM time . "
            f"free tier, list price not configured{cached}")


def render_screen(result: AuditResult, record: rec.RunRecord, console: Console | None = None) -> None:
    console = console or Console()
    v = result.verdict
    banner = Panel(Text(f"  {v.value}  ", style=STYLE[v], justify="center"), subtitle=TAGLINE[v], border_style=STYLE[v].split()[-1],
                   padding=(1, 2))
    head = Table.grid(padding=(0, 2))
    head.add_row(Text("script", style="dim"), Text(Path(result.target).name, style="bold"))
    head.add_row(Text("arm", style="dim"), Text({"A3": "A3  T0 + T1 + T2", "A4": "A4  T0 + T1 only"}.get(record.arm, record.arm)))
    shown = [f for f in result.findings if f.kind is not Kind.SENSITIVITY or f.tier is not Tier.T2]
    body: list = [banner, head, Text("")]
    if shown:
        body += [_finding_block(lead, ws) for lead, ws in _group(shown)]
        body.append(Text(""))
    body.append(Text("checks run   " + " . ".join(c.split(".", 1)[1] for c in result.checks_run), style="dim"))
    body.append(Text("cost         " + _cost_line(record), style="dim"))
    console.print(Group(*body))


def render_markdown(result: AuditResult, record: rec.RunRecord) -> str:
    """The artifact that exists after the terminal closes."""
    v = result.verdict
    lines = [f"# Kilter audit: {v.value}", "", f"**Script:** `{Path(result.target).name}`  ",
             f"**Arm:** {record.arm}  ", f"**Run:** `{record.run_id}`  ", f"**Time (UTC):** {record.created_utc}  ",
             f"**Verifier code hash:** `{record.code_sha256[:16]}`  ",
             f"**Record digest:** `{rec.sha256_bytes(rec.canonical(record.to_dict()).encode())[:16]}`", "",
             f"> {TAGLINE[v]}", ""]
    if result.findings:
        lines += ["## Findings", ""]
        for f, ws in _group(result.findings):
            lines += [f"### {f.defect_class} - {class_name(f.defect_class)}",
                      f"- **Kind:** {f.kind.value}", f"- **Caught by:** {', '.join(TIER_LABEL[w.tier.value] for w in ws)}",
                      f"- **Site:** `{f.site or 'n/a'}`" + (f"  \n- **Confidence:** {f.confidence:.2f}" if f.tier is Tier.T2 else ""),
                      f"- **What:** {f.message}", f"- **Evidence:** {f.evidence}", ""]
    else:
        lines += ["## Findings", "", "None.", ""]
    lines += ["## What was checked", "", *[f"- `{c}`" for c in result.checks_run], ""]
    tk = record.tokens()
    lines += ["## Cost", "", f"- LLM calls: {tk['calls']} ({tk['cached_calls']} replayed)",
              f"- Tokens: {tk['input']:,} input, {tk['output_billed']:,} output (including hidden reasoning)", ""]
    if record.model.get("reported"):
        lines += [f"- Model: {', '.join(record.model['reported'])} (requested {record.model['requested']})", ""]
    lines += ["## Limits", "",
              "Kilter audits an analysis; it does not write one. Deterministic tiers (T0, T1) are sound for the patterns "
              "they check; the T2 critic is an LLM and can be wrong. A pass means the listed checks found nothing, not "
              "that the analysis is correct.", ""]
    return "\n".join(lines)

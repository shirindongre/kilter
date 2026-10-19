from __future__ import annotations

from pathlib import Path

import typer

from kilter import __version__

app = typer.Typer(help="Kilter: is your analysis in kilter?", no_args_is_help=True, add_completion=False)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"kilter {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True, help="Show version."),
) -> None:
    """Audit an analysis script and report IN KILTER / OUT OF KILTER / ESCALATE."""


@app.command()
def audit(
    script: Path,
    data: str = typer.Option(..., help="Dataset name, e.g. bace or bbbp."),
    sensitivity: bool = typer.Option(False, "--sensitivity", help="Also re-run under other split protocols (slow, AD-9)."),
    as_json: bool = typer.Option(False, "--json", help="Emit the audit as JSON."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Deterministic tiers only (T0+T1, arm A4): no API key, no network."),
    report: Path = typer.Option(None, "--report", help="Also write a report.md here."),
) -> None:
    """Audit SCRIPT against a dataset (audit mode only, AD-8). Exit code: 0 in kilter, 1 out of kilter, 2 escalate.

    By default the LLM critic (T2) runs too; it needs GOOGLE_API_KEY in .env and executes the script once to read its results.
    """
    import json
    import tempfile
    import warnings
    from pathlib import Path as P

    from kilter.core.findings import Verdict
    from kilter.data import DATASETS
    from kilter.graph.pipeline import audit_full
    from kilter.report import render_markdown, render_screen

    warnings.filterwarnings("ignore")
    if data.lower() not in DATASETS:
        typer.echo(f"unknown dataset {data!r}; Phase 1 supports {', '.join(DATASETS)}", err=True)
        raise typer.Exit(code=2)
    with tempfile.TemporaryDirectory() as tmp:
        result, record = audit_full(script, use_t2=not no_llm, sensitivity=sensitivity, runs_dir=P(tmp))
    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        render_screen(result, record)
    if report:
        report.write_text(render_markdown(result, record), encoding="utf-8")
        typer.echo(f"report written to {report}", err=True)
    raise typer.Exit(code={Verdict.IN_KILTER: 0, Verdict.OUT_OF_KILTER: 1, Verdict.ESCALATE: 2}[result.verdict])


@app.command()
def demo() -> None:
    """Run the cached, offline, deterministic demo (§5.7): no network, no API key, identical output every time."""
    import os
    import tempfile
    import warnings
    from pathlib import Path as P

    os.environ["KILTER_LLM_MODE"] = "replay"  # recorded LLM responses only; a missing fixture is an error, never a live call
    warnings.filterwarnings("ignore")
    from rich.console import Console
    from rich.rule import Rule

    from kilter.graph.pipeline import audit_full
    from kilter.llm import FixtureMissing
    from kilter.report import render_screen

    root = P(__file__).resolve().parents[2] / "demo"
    steps = [
        ("1  A clean analysis", root / "1_clean_bace.py"),
        ("2  Test data leaks into preprocessing: found by static analysis, confirmed by the critic", root / "2_leakage_bbbp.py"),
        ("3  The numbers are fine but the conclusion is not: only the critic can see this", root / "3_overclaim_bace.py"),
    ]
    console = Console(width=100)
    console.print(Rule("Kilter: is your analysis in kilter?"))
    with tempfile.TemporaryDirectory() as tmp:
        for title, script in steps:
            console.print(Rule(title, style="dim"))
            try:
                result, record = audit_full(script, use_t2=True, variant_id=script.stem, runs_dir=P(tmp))
            except FixtureMissing as e:
                typer.echo(f"demo fixture missing: {e}", err=True)
                raise typer.Exit(code=2)
            except Exception as e:  # most likely the BACE/BBBP data has never been downloaded on this machine
                typer.echo(f"demo could not run ({type(e).__name__}: {e}). The datasets must be cached once: "
                           "python -c \"from kilter.data import load_dataset as l; l('bace'); l('bbbp')\"", err=True)
                raise typer.Exit(code=2)
            render_screen(result, record, console)
    console.print(Rule("Kilter audits analyses; it does not write them.", style="dim"))

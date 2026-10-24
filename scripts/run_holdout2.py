"""Evaluate the frozen T2 prompt and the scope prompt (core/tiers/t2_scope.py) on holdout 2 (AIMS D-022). Resumable.

usage: python scripts/run_holdout2.py            # KILTER_LLM_MODE=record by default: read-through cache, writes new responses
T0+T1 run once per variant (shared); then each prompt gets the same T2 input (A3's input) and one call at temperature 0.
Per-variant results: results/holdout2/<prompt>/<id>.json. Summary + statistics: results/holdout2_summary.json.
A provider stop (e.g. daily quota) ends the run cleanly; rerun to continue from the fixtures.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from kilter.core import record as rec
from kilter.core.adjudicator import adjudicate
from kilter.core.astutil import module_constants
from kilter.core.datacard import data_card
from kilter.core.tiers import t2_critic, t2_scope
from evalutil import keep_evaluated
from kilter.defects.variants import generate_holdout2
from kilter.eval.artifacts import artifact_for
from kilter.eval.metrics import clopper_pearson, hit, paired_exact
from kilter.graph.pipeline import audit_full

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "holdout2"
PROMPTS = {"frozen": (t2_critic.run_t2, rec.sha256_bytes(t2_critic.SYSTEM.encode())),
           "scope": (t2_scope.run_t2_scope, t2_scope.PROMPT_SHA256)}


def audit(prompt: str, v, path: Path, t01) -> dict:
    f = OUT / prompt / f"{v.id}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    run, sha = PROMPTS[prompt]
    source = path.read_text(encoding="utf-8")
    ds = module_constants(ast.parse(source))["DATASET"][0]
    out = run(source, artifact_for(path), data_card(ds), t01.findings, t01.checks_run, path.name)
    result = adjudicate(str(path), t01.findings + out.findings, t01.checks_run + ["T2.critic"])
    row = {"variant": v.id, "truth": v.defect_class, "prompt": prompt, "prompt_sha256": sha, "verdict": result.verdict.value,
           "findings": [x.to_dict() for x in result.findings], "t2_raw": [x.to_dict() for x in out.findings],
           "assessment": out.report.assessment if out.report else None, "notes": out.report.notes if out.report else None,
           "call": out.call, "code_sha256": rec.code_hash()}
    row["detected"] = hit(v, row["verdict"], row["findings"])
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def summarize(variants, rows: dict[str, dict[str, dict]]) -> dict:
    s: dict = {"prompt_sha256": {p: PROMPTS[p][1] for p in PROMPTS}, "arms": {}}
    for p in PROMPTS:
        for label, clean in (("detect_B5", False), ("fp_HC2", True)):
            vs = [v for v in variants if v.clean == clean]
            k = sum(rows[p][v.id]["detected"] for v in vs)
            lo, hi = clopper_pearson(k, len(vs))
            s["arms"].setdefault(p, {})[label] = {"k": k, "n": len(vs), "lo": lo, "hi": hi,
                                                  "hits": [v.id for v in vs if rows[p][v.id]["detected"]]}
        calls = [rows[p][v.id]["call"] for v in variants]
        s["arms"][p]["tokens"] = {"input": sum(c["input_tokens"] for c in calls),
                                  "output_billed": sum(c["output_tokens"] + c["thinking_tokens"] for c in calls),
                                  "seconds": round(sum(c["seconds"] for c in calls), 1)}
    fr = {v.id: {"verdict": rows["frozen"][v.id]["verdict"], "findings": rows["frozen"][v.id]["findings"]} for v in variants}
    sc = {v.id: {"verdict": rows["scope"][v.id]["verdict"], "findings": rows["scope"][v.id]["findings"]} for v in variants}
    s["paired_scope_vs_frozen"] = {"detect_B5": paired_exact(variants, sc, fr, "D5"), "fp_HC2": paired_exact(variants, sc, fr, None)}
    return s


def main() -> None:
    variants = generate_holdout2()
    vdir = ROOT / "results" / "variants"
    keep_evaluated(variants, vdir)
    rows: dict[str, dict[str, dict]] = {p: {} for p in PROMPTS}
    try:
        for i, v in enumerate(variants, 1):
            path = vdir / f"{v.id}.py"
            t01, _ = audit_full(path, use_t2=False, variant_id=v.id, runs_dir=ROOT / "results" / "_scratch_runs")
            for p in PROMPTS:
                r = audit(p, v, path, t01)
                rows[p][v.id] = r
                mark = ("FP " if r["detected"] else "ok ") if v.clean else ("hit" if r["detected"] else "MISS")
                print(f"[{i:2d}/16] {v.id:14s} {p:6s} {mark} {r['verdict']}", flush=True)
    except Exception as e:  # quota/provider stop: keep what is cached, say exactly where we stopped
        print(f"STOPPED at {type(e).__name__}: {str(e)[:300]}\nrerun to resume (finished results are on disk)", flush=True)
        return
    s = summarize(variants, rows)
    (ROOT / "results" / "holdout2_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    sys.exit(main())

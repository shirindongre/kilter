"""Turn the run records into the Phase 1 results: tables with exact CIs, paired tests, cost, phase1.json.

The main set and the holdout are reported separately (AIMS D-018). Everything is read from results/runs/*.
"""
from __future__ import annotations

import json
from pathlib import Path

from kilter.defects.variants import Variant, generate_holdout, generate_variants
from kilter.eval import exploratory
from kilter.eval import metrics as m

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "results" / "runs"
ARMS = ("A0", "A1", "A3", "A4")
SETS = {"main": ("", generate_variants), "holdout": ("_holdout", generate_holdout)}
ALL = ("D1", "D2", "D3", "D4", "D5")


def load(which: str) -> tuple[list[Variant], dict[str, dict[str, dict]]]:
    suffix, gen = SETS[which]
    variants = gen()
    records = {arm: m.load_records(RUNS / f"{arm}{suffix}") for arm in ARMS}
    for arm, recs in records.items():
        missing = [v.id for v in variants if v.id not in recs]
        if missing:
            raise FileNotFoundError(f"{which}/{arm}: no run record for {missing[:3]}... run scripts/run_eval.py")
    return variants, records


def code_hashes(records: dict[str, dict[str, dict]]) -> set[str]:
    return {r["code_sha256"] for arm in records.values() for r in arm.values()}


def summarize(which: str) -> dict:
    variants, records = load(which)
    classes = [c for c in ALL if any(v.defect_class == c for v in variants)]
    out: dict = {"set": which, "n_variants": len(variants), "code_hashes": sorted(code_hashes(records)),
                 "models": sorted({x for a in records.values() for r in a.values() for x in (r["model"].get("reported") or [])}),
                 "prompt_sha256": sorted({r["config"].get("t2_prompt_sha256") for a in ("A1", "A3") for r in records[a].values()}),
                 "arms": {}}
    for arm in ARMS:
        defective = [v for v in variants if not v.clean]
        det = sum(m.hit(v, records[arm][v.id]["verdict"], records[arm][v.id]["findings"]) for v in defective)
        lo, hi = m.clopper_pearson(det, len(defective))
        out["arms"][arm] = {
            "per_class": m.per_class(variants, records[arm]),
            "overall_detection": {"k": det, "n": len(defective), "rate": det / len(defective), "lo": lo, "hi": hi},
            "escalations": m.escalations(variants, records[arm]),
            "cost": m.cost(records[arm]),
        }
    out["paired"] = {
        f"{a}_vs_{b}": {c: m.paired_exact(variants, records[a], records[b], c) for c in [*classes, None]}
        for a, b in (("A3", "A4"), ("A3", "A1"))
    }
    out["abstention"] = {arm: m.abstention_sweep(variants, records[arm]) for arm in ("A1", "A3")}
    out["t2_confidence"] = {arm: sorted(m.with_confidences(records[arm])) for arm in ("A1", "A3")}
    # EXPLORATORY (not a pre-registered arm): the LLM-alone single pass, i.e. A1's first response before self-critique.
    out["exploratory"] = {"critic_alone_first_pass": exploratory.a1_turn1_per_class(variants)}
    return out


def fmt(c: dict) -> str:
    return f"{c['k']}/{c['n']} ({100 * c['lo']:.0f}-{100 * c['hi']:.0f}%)"


def table(res: dict) -> str:
    cols = [c for c in (*ALL, "clean") if c in res["arms"]["A3"]["per_class"]]
    head = "| arm | " + " | ".join("false positives" if c == "clean" else c for c in cols) + " | all defects |"
    rows = [head, "|" + "---|" * (len(cols) + 2)]
    for arm in ARMS:
        a = res["arms"][arm]
        rows.append(f"| {arm} | " + " | ".join(fmt(a["per_class"][c]) for c in cols) + f" | {fmt(a['overall_detection'])} |")
    return "\n".join(rows)


def cost_table(res: dict) -> str:
    rows = ["| arm | LLM calls / audit | input tokens / audit | output tokens / audit (billed) | seconds / audit |", "|---|---|---|---|---|"]
    for arm in ARMS:
        c = res["arms"][arm]["cost"]
        rows.append(f"| {arm} | {c['calls_total'] / c['audits']:.1f} | {c['input_tokens_mean']:,.0f} | "
                    f"{c['output_tokens_billed_mean']:,.0f} | {c['seconds_mean']:.1f} |")
    return "\n".join(rows)


def exploratory_table(res: dict) -> str:
    one = res["exploratory"]["critic_alone_first_pass"]
    cols = [c for c in (*ALL, "clean") if c in one]
    rows = ["| | " + " | ".join("false positives" if c == "clean" else c for c in cols) + " |", "|" + "---|" * (len(cols) + 1)]
    rows.append("| critic alone, first pass (no tiers, no self-critique) | " + " | ".join(fmt(one[c]) for c in cols) + " |")
    a1 = res["arms"]["A1"]["per_class"]
    rows.append("| A1 = same critic after a self-critique turn | " + " | ".join(fmt(a1[c]) for c in cols) + " |")
    return "\n".join(rows)


def build_all() -> dict:
    results = {w: summarize(w) for w in SETS}
    (ROOT / "results" / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    all_records = []
    for which, (suffix, _) in SETS.items():
        for arm in ARMS:
            for f in sorted((RUNS / f"{arm}{suffix}").glob("*.json")):
                d = json.loads(f.read_text(encoding="utf-8"))
                d["set"] = which
                all_records.append(d)
    (ROOT / "results" / "phase1.json").write_text(json.dumps(all_records, indent=1, default=str), encoding="utf-8")
    md = []
    for which, res in results.items():
        md += [f"## {which} set ({res['n_variants']} variants)", "", table(res), "", cost_table(res), "",
               "Exploratory (not a pre-registered arm): did the self-critique turn help?", "", exploratory_table(res), ""]
    (ROOT / "results" / "results_table.md").write_text("\n".join(md), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = build_all()
    for which, res in r.items():
        print(f"\n== {which} ==\n{table(res)}\n\n{cost_table(res)}\n\n{exploratory_table(res)}")

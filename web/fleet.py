"""Fleet view: every evaluated variant, both arms, read from the stored evaluation in `results/` (AIMS D-025).

Nothing here audits anything. Verdicts, findings and token counts come from the saved run records. The only
derivations are the ones `adapter` documents (held_at, outcome against the planted class) and plain counting for the
confusion tables. Each count is then reconciled against the evaluation's own summary files, and any disagreement is
returned to the UI rather than hidden.

Layout it expects (as written by scripts/run_eval.py and scripts/run_holdout2.py):
  results/runs/{A4,A3}[_holdout]/*.json      run records (main set, holdout 1)
  results/holdout2/{frozen,scope}/*.json     one T2-prompt row each (holdout 2; not full run records)
  results/_scratch_runs/*.json               holdout 2's T0+T1 runs (the A4 arm there), kept only if the code hash matches
  results/variants/*.py                      the exact bytes the evaluation audited
  results/{summary,holdout2_summary}.json    the evaluation's own numbers, used for the reconciliation
"""
from __future__ import annotations

import json
import platform
from collections import Counter
from pathlib import Path

import adapter
import catalog
from kilter.core import record as rec
from kilter.core.findings import AuditResult
from kilter.eval.metrics import finding_from_dict
from kilter.defects.variants import generate_holdout, generate_holdout2, generate_variants
from kilter.report import render_markdown

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

CLASSES = ("D1", "D2", "D3", "D4", "D5")
ARMS = ("A4", "A3")
OUTCOMES = ("caught", "wrong_class", "missed", "escalated", "false_alarm", "clean_ok")

SHORT_NAME = {"D1": "Leakage", "D2": "Duplicates", "D3": "Split protocol", "D4": "Multiple comparisons", "D5": "Overclaim"}

# Holdout columns carry the authored name of the kind of script, because "D5" alone hides the difference between
# a subtle overclaim (holdout 1), a claim beyond the data (holdout 2) and the main set's blunt one.
COLUMN_LABEL = {
    "H5": ("D5", "Subtle overclaim"), "HC": (None, "Clean, decisive default"),
    "B5": ("D5", "Beyond the data"), "HC2": (None, "Clean, honest and confident"),
}

SETS = (
    dict(id="main", label="Main", suffix="", gen=generate_variants,
         about="48 scripts: 8 bases x (5 planted defect classes + 1 clean)."),
    dict(id="holdout", label="Holdout 1", suffix="_holdout", gen=generate_holdout,
         about="16 scripts authored after the main results: 8 subtle D5 overclaims and 8 clean scripts with a decisive default."),
    dict(id="holdout2", label="Holdout 2", suffix=None, gen=generate_holdout2,
         about="16 fresh scripts: 8 claims beyond the data and 8 honest, confident clean ones. The evaluation ran T0+T1 and the "
               "critic prompts only here, so there is no A1 or A0 and A3 is a prompt row, not a full run record."),
)


def _load_dir(directory: Path, problems: list[str]) -> dict[str, dict]:
    """variant_id -> record dict. Two records for one variant is reported and the later one kept."""
    out: dict[str, dict] = {}
    for f in sorted(directory.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        vid = d["variant_id"]
        if vid in out:
            problems.append(f"{directory.name}: more than one record for {vid}; kept the later one")
            if d["created_utc"] < out[vid]["created_utc"]:
                continue
        out[vid] = d
    return out


def _tokens(record: dict) -> dict:
    t = record["tokens"]
    return {"tokens_in": t["input"], "tokens_out": t["output_billed"], "calls": t["calls"],
            "seconds": record["seconds_total"]}


def _row_tokens(row: dict) -> dict:
    c = row["call"]
    return {"tokens_in": c["input_tokens"], "tokens_out": c["output_tokens"] + c["thinking_tokens"], "calls": 1,
            "seconds": round(c["seconds"], 1)}


def _cell(arm: str, d: dict, v, *, row: bool, source: str) -> dict:
    result = AuditResult(v.id + ".py", [finding_from_dict(f) for f in d["findings"]], []) if row else adapter.result_from_record(d)
    cell = adapter.stored_cell(result, d["verdict"], v.defect_class, v.site_line)
    cell |= (_row_tokens(d) if row else _tokens(d))
    cell |= {"arm": arm, "run_id": None if row else d["run_id"], "digest_ok": None if row else rec.verify(d), "source": source}
    return cell


def _count(cells: list[dict]) -> dict:
    """Outcome counts and what the arm convicted, for the variants of one planted class (or clean)."""
    outcomes = Counter(c["outcome"] for c in cells)
    predicted: Counter = Counter()
    for c in cells:
        for cls in c["convicted"]:
            predicted[cls] += 1
        if not c["convicted"]:
            predicted["escalate" if c["verdict"] == "escalate" else "pass"] += 1
    return {"n": len(cells), "outcomes": {o: outcomes.get(o, 0) for o in OUTCOMES if outcomes.get(o)},
            "predicted": dict(predicted), "multi": sum(len(c["convicted"]) > 1 for c in cells)}


def _intervals(reported_set: dict, arm: str) -> tuple[list[float] | None, list[float] | None]:
    """The evaluation's own exact 95% intervals for detection and for false alarms, or None where it wrote none."""
    r = reported_set.get(arm)
    if not r:
        return None, None
    if "per_class" in r:
        o, c = r["overall"], r["per_class"].get("clean")
        return [o["lo"], o["hi"]], ([c["lo"], c["hi"]] if c else None)
    return [r["detect_B5"]["lo"], r["detect_B5"]["hi"]], [r["fp_HC2"]["lo"], r["fp_HC2"]["hi"]]


def _totals(conf: dict, detect_ci, fp_ci) -> dict:
    defective = [v for k, v in conf.items() if k != "clean"]
    clean = conf.get("clean", {"n": 0, "outcomes": {}})
    count = lambda o: sum(v["outcomes"].get(o, 0) for v in defective)  # noqa: E731
    return {"defective": sum(v["n"] for v in defective), "caught": count("caught"), "wrong_class": count("wrong_class"),
            "missed": count("missed"), "escalated": count("escalated"), "clean": clean["n"],
            "false_alarm": clean["outcomes"].get("false_alarm", 0), "clean_escalated": clean["outcomes"].get("escalated", 0),
            "detect_ci": detect_ci, "fp_ci": fp_ci}


def _hits(cells: list[dict], clean: bool) -> int:
    """The evaluation's own detection count: a conviction naming the planted class, or for clean a false alarm."""
    return sum(c["outcome"] == ("false_alarm" if clean else "caught") for c in cells)


class Fleet:
    def __init__(self, results: Path = RESULTS) -> None:
        self.results = results
        self.problems: list[str] = []
        self._runs: dict[str, tuple[dict, object]] = {}   # run_id -> (stored record, Variant)
        self._variants = {v.id: v for s in SETS for v in s["gen"]()}
        self.payload = self._build()

    # -- loading -------------------------------------------------------------------------------

    def _read(self, name: str) -> dict | None:
        f = self.results / name
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def _build(self) -> dict:
        R, probs = self.results, self.problems
        summary, summary2 = self._read("summary.json"), self._read("holdout2_summary.json")
        loaded: dict[str, dict[str, dict[str, dict]]] = {}
        for s in SETS[:2]:
            loaded[s["id"]] = {arm: _load_dir(R / "runs" / f"{arm}{s['suffix']}", probs) for arm in ARMS}
        hashes = sorted({d["code_sha256"] for arms in loaded.values() for recs in arms.values() for d in recs.values()})
        if len(hashes) > 1:
            probs.append(f"the evaluation records carry {len(hashes)} different code hashes: {', '.join(h[:12] for h in hashes)}")
        loaded["holdout2"] = self._load_holdout2(hashes, probs)

        variants, cells_by_set = [], {}
        for s in SETS:
            cells_by_set[s["id"]] = {arm: [] for arm in ("A4", "A3", "scope")}
            for v in s["gen"]():
                base, col = v.id.rsplit("-", 1)
                entry = {"id": v.id, "set": s["id"], "row": base, "col": col, "planted_class": v.defect_class,
                         "site_line": v.site_line, "description": v.description, "cells": {}}
                for arm in ("A4", "A3", "scope"):
                    d = loaded[s["id"]].get(arm, {}).get(v.id)
                    if d is None:
                        continue
                    row = s["id"] == "holdout2" and arm != "A4"
                    cell = _cell(arm, d, v, row=row, source=self._source_of(s["id"], arm))
                    entry["cells"][arm] = cell
                    cells_by_set[s["id"]][arm].append((v, cell))
                    if cell["run_id"]:
                        self._runs[cell["run_id"]] = (d, v)
                    if not cell["consistent"]:
                        probs.append(f"{v.id} {arm}: the stored findings do not adjudicate to the stored verdict")
                    if cell["digest_ok"] is False:
                        probs.append(f"{v.id} {arm}: the run record's digest does not match its body")
                variants.append(entry)

        reported = self._reported(summary, summary2)
        sets_out = []
        for s in SETS:
            ids = [v for v in variants if v["set"] == s["id"]]
            cols = sorted({v["col"] for v in ids}, key=lambda c: (c.startswith("HC") or c == "clean", c))
            arms = [a for a in ("A4", "A3", "scope") if cells_by_set[s["id"]][a]]
            confusion = {}
            for arm in arms:
                by_class: dict[str, list[dict]] = {}
                for v, cell in cells_by_set[s["id"]][arm]:
                    by_class.setdefault(v.defect_class or "clean", []).append(cell)
                confusion[arm] = {k: _count(c) for k, c in sorted(by_class.items(), key=lambda kv: (kv[0] == "clean", kv[0]))}
            totals = {arm: _totals(confusion[arm], *_intervals(reported.get(s["id"], {}), arm)) for arm in arms}
            sets_out.append({"id": s["id"], "label": s["label"], "about": s["about"], "n": len(ids), "arms": arms,
                             "columns": [self._column(s["id"], c) for c in cols], "confusion": confusion, "totals": totals})

        reconciliation = self._reconcile(summary, summary2, cells_by_set)
        return {
            "available": True, "sets": sets_out, "variants": variants,
            "provenance": self._provenance(loaded, hashes),
            "reported": reported,
            "reconciliation": reconciliation, "problems": probs,
        }

    def _load_holdout2(self, hashes: list[str], probs: list[str]) -> dict[str, dict[str, dict]]:
        R = self.results
        out: dict[str, dict[str, dict]] = {"A3": {}, "scope": {}, "A4": {}}
        for prompt, arm in (("frozen", "A3"), ("scope", "scope")):
            for f in sorted((R / "holdout2" / prompt).glob("*.json")):
                d = json.loads(f.read_text(encoding="utf-8"))
                out[arm][d["variant"]] = d
        ids = {v.id for v in generate_holdout2()}
        # The T0+T1 half of holdout 2 was run once per variant into _scratch_runs, which also holds older, superseded
        # runs. Only records of the evaluation's own code hash count.
        for f in sorted((R / "_scratch_runs").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d["variant_id"] in ids and d["arm"] == "A4" and d["code_sha256"] in hashes:
                if d["variant_id"] in out["A4"]:
                    probs.append(f"_scratch_runs: more than one A4 record for {d['variant_id']}; kept the later one")
                    if d["created_utc"] < out["A4"][d["variant_id"]]["created_utc"]:
                        continue
                out["A4"][d["variant_id"]] = d
        return out

    @staticmethod
    def _source_of(set_id: str, arm: str) -> str:
        if set_id != "holdout2":
            return "run record"
        return "T0+T1 run record (results/_scratch_runs)" if arm == "A4" else "critic-prompt row (results/holdout2)"

    @staticmethod
    def _column(set_id: str, col: str) -> dict:
        if col in COLUMN_LABEL:
            cls, name = COLUMN_LABEL[col]
            return {"id": col, "class": cls, "name": name, "long": name}
        if col == "clean":
            return {"id": col, "class": None, "name": "Clean", "long": "Clean: nothing planted"}
        return {"id": col, "class": col, "name": SHORT_NAME[col], "long": catalog.class_name(col)}

    # -- provenance and reconciliation -----------------------------------------------------------

    def _provenance(self, loaded: dict, hashes: list[str]) -> dict:
        records = [d for arms in loaded.values() for recs in arms.values() for d in recs.values() if "record_sha256" in d]
        return {
            "records": len(records), "digests_ok": sum(rec.verify(d) for d in records),
            "code_sha256": hashes, "tree_code_sha256": rec.code_hash(),
            "python": sorted({d["versions"]["python"] for d in records}), "running_python": platform.python_version(),
            "models": sorted({m for d in records for m in (d["model"].get("reported") or [])}),
            "prompt_sha256": sorted({d["config"].get("t2_prompt_sha256") for d in records if d["config"].get("t2_prompt_sha256")}),
        }

    @staticmethod
    def _reported(summary: dict | None, summary2: dict | None) -> dict:
        """The evaluation's own figures, passed through unchanged, so the page can print them beside the derived ones."""
        out: dict = {}
        if summary:
            for sid in ("main", "holdout"):
                out[sid] = {arm: {"per_class": a["per_class"], "overall": a["overall_detection"], "cost": a["cost"],
                                  "escalations": a["escalations"]} for arm, a in summary[sid]["arms"].items() if arm in ARMS}
                out[sid]["paired"] = summary[sid]["paired"].get("A3_vs_A4")
        if summary2:
            out["holdout2"] = {"A3": summary2["arms"]["frozen"], "scope": summary2["arms"]["scope"],
                               "paired": summary2["paired_scope_vs_frozen"]}
        return out

    def _reconcile(self, summary: dict | None, summary2: dict | None, cells: dict) -> dict:
        checks: list[dict] = []

        def add(where: str, derived: str, reported: str, source: str) -> None:
            checks.append({"where": where, "derived": derived, "reported": reported, "source": source, "ok": derived == reported})

        if summary:
            for sid in ("main", "holdout"):
                for arm in ARMS:
                    per = summary[sid]["arms"][arm]["per_class"]
                    by_class: dict[str, list[dict]] = {}
                    for v, c in cells[sid][arm]:
                        by_class.setdefault(v.defect_class or "clean", []).append(c)
                    for key, rep in per.items():
                        mine = by_class.get(key, [])
                        add(f"{sid} {arm} {key}", f"{_hits(mine, key == 'clean')}/{len(mine)}", f"{rep['k']}/{rep['n']}", "summary.json")
        if summary2:
            for arm, prompt in (("A3", "frozen"), ("scope", "scope")):
                mine = cells["holdout2"][arm]
                for label, clean in (("detect_B5", False), ("fp_HC2", True)):
                    sel = [c for v, c in mine if (v.defect_class is None) == clean]
                    rep = summary2["arms"][prompt][label]
                    add(f"holdout2 {arm} {label}", f"{_hits(sel, clean)}/{len(sel)}", f"{rep['k']}/{rep['n']}", "holdout2_summary.json")
                    hits = sorted(v.id for v, c in mine if (v.defect_class is None) == clean and c["outcome"] == ("false_alarm" if clean else "caught"))
                    add(f"holdout2 {arm} {label} (ids)", ",".join(hits) or "none", ",".join(sorted(rep["hits"])) or "none", "holdout2_summary.json")
        # Per-variant: the evaluation also wrote one line per variant and arm (A4_summary.json etc.).
        for arm in ARMS:
            for sid, suffix in (("main", ""), ("holdout", "_holdout")):
                lines = self._read(f"{arm}{suffix}_summary.json")
                if lines is None:
                    continue
                theirs = {r["variant"]: r for r in lines}
                bad = [v.id for v, c in cells[sid][arm]
                       if v.id not in theirs or theirs[v.id]["verdict"].replace(" ", "_").lower() != c["verdict"]
                       or theirs[v.id]["detected"] != (c["outcome"] in ("caught", "false_alarm"))]
                add(f"{sid} {arm} per-variant verdict and detected flag", f"{len(bad)} differ", "0 differ", f"{arm}{suffix}_summary.json")
        return {"checked": len(checks), "agree": sum(c["ok"] for c in checks),
                "disagree": [c for c in checks if not c["ok"]], "checks": checks}

    # -- click-through ---------------------------------------------------------------------------

    def has(self, run_id: str) -> bool:
        return run_id in self._runs

    def saved(self, run_id: str) -> dict | None:
        """{view, record, report_md} in the shape the run screen takes, built from the stored record. None if the
        script the record audited is not in results/variants."""
        if run_id not in self._runs:
            return None
        d, v = self._runs[run_id]
        path = self.results / "variants" / f"{v.id}.py"
        if not path.exists():
            return None
        sample = {"id": v.id, "kind": "variant", "label": v.id, "group": v.group, "base": v.base,
                  "description": v.description, "planted_class": v.defect_class, "site_line": v.site_line}
        view = adapter.view_from_stored(d, path.read_bytes(), sample=sample)
        report = render_markdown(adapter.result_from_record(d), adapter.record_from_dict(d))
        return {"view": view, "record": d, "report_md": report}


def load(results: Path = RESULTS) -> Fleet | None:
    """None when the evaluation's results are not on this machine (results/ is gitignored)."""
    if not (results / "runs" / "A4").is_dir():
        return None
    return Fleet(results)

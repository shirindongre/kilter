"""Run record -> UI view model (`kilter.run/1`, FRONTEND-SPEC section 8).

The UI computes nothing: verdict, tier attribution, sensitivity and ground-truth outcome all arrive from here.
This module only re-shapes what the verifier already decided. It never changes a verdict, and it lives outside
`src/kilter` so the verifier's code hash (AD-10, D-020) is untouched.

Spec fields the backend does not emit are derived or authored, and each is listed in web/README.md:
held_at (shallowest tier with a defect), check names/assertions/remedies (catalog.py), code excerpts (sliced from
the audited source), sensitivity numbers (parsed from the T1 finding's fixed-format evidence string).
"""
from __future__ import annotations

import re

import catalog
from kilter.core import record as rec
from kilter.core.findings import AuditResult, Finding, Kind, Tier, Verdict
from kilter.eval.metrics import finding_from_dict

SCHEMA = "kilter.run/1"
TIER_ORDER = {"T0": 0, "T1": 1, "T2": 2}
VERDICT_KEY = {Verdict.IN_KILTER: "in_kilter", Verdict.OUT_OF_KILTER: "out_of_kilter", Verdict.ESCALATE: "escalate"}
VERDICT_WORD = {"in_kilter": "IN KILTER", "out_of_kilter": "OUT OF KILTER", "escalate": "ESCALATE"}
ARM_LABEL = {"A3": "Full: T0 + T1 + T2", "A4": "Deterministic: T0 + T1", "A0": "No verification", "A1": "LLM self-critique"}
DEFECTISH = (Kind.DEFECT, Kind.UNREPORTED)


def _tier(f: Finding) -> str:
    return f.tier.value.lower()


# --- excerpts ------------------------------------------------------------------------------------

def excerpt(source: str, line: int | None, context: int = 3) -> dict | None:
    if not line:
        return None
    lines = source.splitlines()
    if not 1 <= line <= len(lines):
        return None
    lo, hi = max(1, line - context), min(len(lines), line + context)
    return {"from": lo, "to": hi, "line": line, "lines": [{"n": n, "text": lines[n - 1]} for n in range(lo, hi + 1)]}


# --- findings ------------------------------------------------------------------------------------

def _witness(f: Finding) -> dict:
    return {"tier": _tier(f), "check_id": f.check, "confidence": f.confidence if f.tier is Tier.T2 else None,
            "line": f.line, "message": f.message, "evidence": f.evidence}


def _group(findings: list[Finding]) -> list[tuple[Finding, list[Finding]]]:
    """Same grouping as the terminal report: one block per (class, kind), lowest tier leads, so a sound check and
    the critic agreeing reads as one finding with two witnesses."""
    groups: dict[tuple[str, Kind], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.defect_class, f.kind), []).append(f)
    out = [(sorted(g, key=lambda x: x.tier.value)[0], sorted(g, key=lambda x: x.tier.value)) for g in groups.values()]
    return sorted(out, key=lambda lw: (TIER_ORDER[lw[0].tier.value], lw[0].line or 0, lw[0].defect_class))


def _finding_view(lead: Finding, witnesses: list[Finding], source: str, filename: str) -> dict:
    site_line = next((w.line for w in witnesses if w.line), None)
    ex = excerpt(source, site_line)
    unreported = lead.kind is Kind.UNREPORTED
    t2 = [w for w in witnesses if w.tier is Tier.T2]
    return {
        "kind": "defect" if lead.tier is not Tier.T2 else "query",
        "unreported": unreported,
        "class": lead.defect_class,
        "class_name": catalog.class_name(lead.defect_class),
        "tier": _tier(lead),
        "check_id": lead.check,
        "witnesses": [_witness(w) for w in witnesses],
        "site": {"path": filename, "line": site_line, "from": ex["from"], "to": ex["to"]} if ex else
                ({"path": filename, "line": None, "from": None, "to": None}),
        "excerpt": ex,
        "statement": lead.message,
        "evidence": lead.evidence,
        "remedy": catalog.remedy_for(lead.defect_class, unreported),
        "confidence": max((w.confidence for w in t2), default=None),
    }


# --- blockers (escalate) -------------------------------------------------------------------------

def _blocker_view(f: Finding, filename: str, dataset: str | None) -> dict:
    tier = catalog.UNRESOLVED.get(f.check) or _tier(f)
    if f.tier is Tier.T2 and f.message.startswith("T2 suspects"):
        info = dict(title="The critic suspects a problem but is not confident", decision=catalog.BLOCKERS["T2.critic"]["decision"])
    else:
        info = catalog.BLOCKERS.get(f.check) or catalog.BLOCKERS["T2.critic" if f.tier is Tier.T2 else "T1.execute"]
    return {
        "tier": tier, "check_id": f.check, "title": info["title"], "reason": f.message, "evidence": f.evidence,
        "decision_for_human": info["decision"], "command": f"kilter audit {filename} --data {dataset or 'bace'}",
    }


# --- split sensitivity ---------------------------------------------------------------------------

_PAIR = re.compile(r"([\w-]+): (\d+\.\d+)")
_SEEDS = re.compile(r"\((\d+) seeds each\)")
_STATED = re.compile(r"\(stated: (?:'([^']*)'|not stated)\)")


def _sensitivity_view(f: Finding) -> dict | None:
    """T1.split-sensitivity writes a fixed-format evidence string (t1_runtime._split_sensitivity); parse it back."""
    scores = [{"label": k, "value": float(v)} for k, v in _PAIR.findall(f.evidence)]
    if len(scores) < 2:
        return None
    seeds = int(m.group(1)) if (m := _SEEDS.search(f.evidence)) else None
    stated = m.group(1) if (m := _STATED.search(f.message)) else None
    values = [s["value"] for s in scores]
    spread = max(values) - min(values)
    as_written = next((s for s in scores if s["label"] == stated), None)
    alternative = None
    if as_written:
        alternative = max((s for s in scores if s is not as_written), key=lambda s: abs(s["value"] - as_written["value"]))
    points = spread * 100
    headline = (f"The number moves {points:.1f} points on a choice nobody wrote down." if stated is None
                else f"The number moves {points:.1f} points between split protocols; the stated one is {stated}.")
    return {"choice": "split_protocol", "stated": stated is not None, "stated_label": stated, "metric": "auroc",
            "scores": scores, "as_written": as_written, "alternative": alternative,
            "delta": round(spread, 6), "seeds": seeds, "headline": headline, "message": f.message}


# --- checks register -----------------------------------------------------------------------------

def _checks_view(result: AuditResult) -> list[dict]:
    stuck = {f.check for f in result.findings if f.kind is Kind.INCONCLUSIVE and f.check in catalog.UNRESOLVED}
    ids = list(result.checks_run)
    if "T0.parse" in stuck:
        ids += [c for c in catalog.SOUND_DEFAULTS["t0"] if c not in ids]
    if stuck & {"T1.import", "T1.hooks", "T1.execute"}:
        ids += [c for c in catalog.SOUND_DEFAULTS["t1"] if c not in ids]
    could_not = set()
    if "T0.parse" in stuck:
        could_not |= set(catalog.SOUND_DEFAULTS["t0"])
    if stuck & {"T1.import", "T1.hooks", "T1.execute"}:
        could_not |= set(catalog.SOUND_DEFAULTS["t1"])
    if "T1.split-sensitivity" in stuck:
        could_not.add("T1.split-sensitivity")
        ids += [c for c in ["T1.split-sensitivity"] if c not in ids]

    def order(c: str):
        info = catalog.check_info(c)
        known = list(catalog.CHECKS)
        return (TIER_ORDER[info["tier"].upper()], known.index(c) if c in known else 99)

    rows = []
    for i, cid in enumerate(sorted(dict.fromkeys(ids), key=order), start=1):
        info = catalog.check_info(cid)
        mine = [f for f in result.findings if f.check == cid]
        if cid in could_not:
            res = "could_not_run"
        elif cid == "T2.critic":
            if any(f.kind is Kind.INCONCLUSIVE and f.message.startswith("T2 suspects") for f in mine) or \
               any(f.kind is Kind.DEFECT for f in mine):
                res = "query"
            elif any(f.kind is Kind.INCONCLUSIVE for f in mine):
                res = "could_not_run"
            else:
                res = "no_objection"
        else:
            res = "fired" if any(f.kind in DEFECTISH for f in mine) else "clear"
        rows.append({"no": i, "id": cid, "tier": info["tier"], "sound": info["sound"], "name": info["name"],
                     "assertion": info["assertion"], "result": res})
    return rows


# --- cost and provenance -------------------------------------------------------------------------

def _cost_view(record: rec.RunRecord) -> dict:
    tk = record.tokens()
    calls = [c for t in record.tiers.values() for c in t.llm_calls]
    return {
        "model": ", ".join(record.model.get("reported") or []) or None,
        "model_requested": record.model.get("requested"),
        "calls": tk["calls"], "replayed_calls": tk["cached_calls"],
        "tokens_in": tk["input"], "tokens_out": tk["output_billed"],
        "llm_seconds": round(sum(c["seconds"] for c in calls), 2),
        "tier_seconds": {k: round(t.seconds, 3) for k, t in record.tiers.items()},
        "usd_equivalent": None,   # no list price configured (providers.yaml): the UI renders a bracketed slot
    }


# --- ground truth (sample browser) ---------------------------------------------------------------

def ground_truth(result: AuditResult, planted_class: str | None, site_line: int | None) -> dict:
    caught = [f for f in result.findings if f.kind in DEFECTISH]
    classes = {f.defect_class for f in caught}
    verdict = VERDICT_KEY[result.verdict]
    if planted_class is None:
        outcome = "false_alarm" if caught else ("clean_ok" if verdict == "in_kilter" else "escalated")
        return {"planted_class": None, "site_line": None, "outcome": outcome, "site_match": None}
    if planted_class in classes:
        outcome = "caught"
    elif caught:
        outcome = "wrong_class"
    elif verdict == "escalate":
        outcome = "escalated"
    else:
        outcome = "missed"
    site_match = None
    if outcome == "caught" and site_line:
        site_match = any(f.line == site_line for f in caught if f.defect_class == planted_class)
    return {"planted_class": planted_class, "site_line": site_line, "outcome": outcome, "site_match": site_match}


# --- stored records (fleet view) -----------------------------------------------------------------
# The evaluation already ran. These functions re-shape its saved run records for display and never re-run a tier,
# re-adjudicate, or change a verdict: the stored verdict is shown, and cross-checked against the stored findings.

def result_from_record(d: dict) -> AuditResult:
    checks = [c for t in ("T0", "T1", "T2") if t in d["tiers"] for c in d["tiers"][t]["checks"]]
    return AuditResult(d["variant_id"] + ".py", [finding_from_dict(f) for f in d["findings"]], checks)


def stored_cell(result: AuditResult, stored_verdict: str, planted_class: str | None, site_line: int | None) -> dict:
    """One arm's outcome on one variant, from its stored findings. `consistent` is False if the findings would not
    adjudicate to the verdict the record stored (a sign the record was edited or came from other code)."""
    caught = [f for f in result.findings if f.kind in DEFECTISH]
    verdict = VERDICT_KEY[result.verdict]
    held_at = min((_tier(f) for f in caught), key=lambda t: TIER_ORDER[t.upper()]) if verdict == "out_of_kilter" else None
    truth = ground_truth(result, planted_class, site_line)
    return {"verdict": verdict, "held_at": held_at, "convicted": sorted({f.defect_class for f in caught}),
            "outcome": truth["outcome"], "site_match": truth["site_match"],
            "consistent": result.verdict.value == stored_verdict}


def record_from_dict(d: dict) -> rec.RunRecord:
    keep = {k: d[k] for k in ("run_id", "arm", "variant_id", "input_sha256", "code_sha256", "created_utc", "seed", "model",
                              "versions", "verdict", "findings", "config", "schema_version")}
    return rec.RunRecord(**keep, tiers={k: rec.TierRun(**t) for k, t in d["tiers"].items()})


def view_from_stored(d: dict, source: bytes, *, sample: dict | None = None) -> dict:
    """The run screen's view model for a record saved by the evaluation. `source` is the audited file's bytes.
    Provenance shows the digest the file carries, checked against its own body, not one recomputed here, and says
    whether `source` is the file the record hashed (if not, the excerpts could point at the wrong lines)."""
    text = source.decode("utf-8").replace("\r\n", "\n")
    view = to_view(result_from_record(d), record_from_dict(d), text, sample=sample)
    view["provenance"]["record_sha256"] = d.get("record_sha256")
    view["provenance"]["digest_ok"] = rec.verify(d)
    # pipeline.py hashes the file bytes followed by the dataset name
    view["provenance"]["source_matches"] = rec.sha256_bytes(source + (d["config"].get("dataset") or "").encode()) == d["input_sha256"]
    view["stored"] = True
    return view


# --- the view ------------------------------------------------------------------------------------

def _statement(verdict: str, held_at: str | None, groups: list[dict], blockers: list[dict]) -> str:
    if verdict == "in_kilter":
        return catalog.TAGLINE["in_kilter"]
    if verdict == "escalate":
        return catalog.TAGLINE["escalate"]
    lead = groups[0]
    if held_at == "t2":
        return "Only the critic objected. No sound check agrees, so read this as a query to answer, not a proven defect."
    label = catalog.TIER_LABEL[held_at]
    more = f" {len(groups) - 1} more finding{'s' if len(groups) > 2 else ''} below." if len(groups) > 1 else ""
    return f"A sound check held the mark at {label}: {lead['class_name']}.{more}"


def to_view(result: AuditResult, record: rec.RunRecord, source: str, *, sample: dict | None = None) -> dict:
    filename = result.target.replace("\\", "/").rsplit("/", 1)[-1]
    dataset = record.config.get("dataset")
    verdict = VERDICT_KEY[result.verdict]

    grouped = _group([f for f in result.findings if f.kind in DEFECTISH])
    findings = [_finding_view(lead, ws, source, filename) for lead, ws in grouped]
    blockers = sorted((_blocker_view(f, filename, dataset) for f in result.findings if f.kind is Kind.INCONCLUSIVE),
                      key=lambda b: TIER_ORDER[b["tier"].upper()])
    sens = [v for f in result.findings
            if f.kind is Kind.SENSITIVITY and f.check == "T1.split-sensitivity" and (v := _sensitivity_view(f))]
    notes = [{"tier": _tier(f), "class": f.defect_class, "message": f.message, "evidence": f.evidence,
              "confidence": f.confidence if f.tier is Tier.T2 else None}
             for f in result.findings if f.kind is Kind.SENSITIVITY and f.check != "T1.split-sensitivity"]

    held_at = None
    if verdict == "out_of_kilter" and findings:
        held_at = min((f["tier"] for f in findings), key=lambda t: TIER_ORDER[t.upper()])
    unresolved_tier = blockers[0]["tier"] if (verdict == "escalate" and blockers) else None
    mark = held_at if held_at else ("esc" if verdict == "escalate" else "clear")

    checks = _checks_view(result)
    ran = [c for c in checks if c["result"] != "could_not_run"]
    statement = _statement(verdict, held_at, findings, blockers)
    detail = (f"{len(ran)} check{'s' if len(ran) != 1 else ''} ran: " + ", ".join(c["name"] for c in ran)) if ran else "No check completed."

    view = {
        "schema": SCHEMA,
        "run_id": record.run_id,
        "surveyed_at": record.created_utc,
        "arm": record.arm,
        "arm_label": ARM_LABEL.get(record.arm, record.arm),
        "llm_mode": record.config.get("llm_mode"),
        "subject": {"path": filename, "dataset": dataset, "input_sha256": record.input_sha256, "seed": record.seed,
                    "source": source},
        "verdict": verdict,
        "verdict_word": VERDICT_WORD[verdict],
        "held_at": held_at,
        "mark": mark,
        "unresolved_tier": unresolved_tier,
        "statement": statement,
        "detail": detail,
        "checks": checks,
        "checks_ran": len(ran),
        "findings": findings,
        "blockers": blockers,
        "sensitivity": sens,
        "notes": notes,
        "bounds": catalog.PASS_BOUNDS if verdict == "in_kilter" else None,
        "cost": _cost_view(record),
        "provenance": {
            "code_sha256": record.code_sha256, "record_sha256": record.to_dict()["record_sha256"],
            "digest_ok": rec.verify(record.to_dict()), "versions": record.versions,
            "t2_prompt_sha256": record.config.get("t2_prompt_sha256"),
            "convict_at": record.config.get("convict_at"), "escalate_at": record.config.get("escalate_at"),
        },
        "sample": None,
    }
    if sample:
        view["sample"] = {k: sample.get(k) for k in ("id", "kind", "label", "group", "base", "description")}
        if sample.get("kind") in ("demo", "variant"):
            view["sample"]["truth"] = ground_truth(result, sample.get("planted_class"), sample.get("site_line"))
    return view

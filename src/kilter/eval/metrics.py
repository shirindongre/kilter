"""Metrics over run records (blueprint 8.2, 8.3). Exact binomial CIs only: n is small and bare percentages mislead.

Everything is computed from the saved run records plus the planted ground truth in the variant list, never from
printed output. The main set and the holdout are different populations and are reported separately (AIMS D-018).
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from scipy.stats import beta, binomtest

from kilter.core.adjudicator import adjudicate
from kilter.core.findings import Finding, Kind, Tier, Verdict
from kilter.defects.variants import Variant

ROOT = Path(__file__).resolve().parents[3]
CLASSES = ("D1", "D2", "D3", "D4", "D5")


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided binomial confidence interval."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def load_records(directory: Path) -> dict[str, dict]:
    """variant_id -> run record dict (one per variant per arm)."""
    out: dict[str, dict] = {}
    for f in sorted(Path(directory).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["variant_id"]] = d
    return out


def finding_from_dict(d: dict) -> Finding:
    return Finding(d["defect_class"], Tier(d["tier"]), Kind(d["kind"]), d["message"], d["evidence"], d["check"],
                   d.get("file"), d.get("line"), d.get("confidence", 1.0))


def raw_findings(record: dict) -> list[Finding]:
    """Findings as the tiers emitted them, before the adjudicator reclassified T2 by confidence."""
    return [finding_from_dict(f) for t in record["tiers"].values() for f in t["findings"]]


def hit(variant: Variant, verdict: str, findings: list[dict | Finding]) -> bool:
    """Detection for a defective variant (a conviction naming the planted class); false positive for a clean one."""
    if variant.clean:
        return verdict == Verdict.OUT_OF_KILTER.value
    cls = variant.defect_class
    for f in findings:
        d = f.to_dict() if isinstance(f, Finding) else f
        if d["defect_class"] == cls and d["kind"] in (Kind.DEFECT.value, Kind.UNREPORTED.value):
            return True
    return False


def per_class(variants: list[Variant], records: dict[str, dict]) -> dict[str, dict]:
    """class -> {k, n, rate, lo, hi}; the key 'clean' is the false-positive rate."""
    k: dict[str, int] = defaultdict(int)
    n: dict[str, int] = defaultdict(int)
    for v in variants:
        key = v.defect_class or "clean"
        n[key] += 1
        k[key] += hit(v, records[v.id]["verdict"], records[v.id]["findings"])
    out = {}
    for key in n:
        lo, hi = clopper_pearson(k[key], n[key])
        out[key] = {"k": k[key], "n": n[key], "rate": k[key] / n[key], "lo": lo, "hi": hi}
    return out


def escalations(variants: list[Variant], records: dict[str, dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for v in variants:
        out[v.defect_class or "clean"] += records[v.id]["verdict"] == Verdict.ESCALATE.value
    return dict(out)


def paired_exact(variants: list[Variant], a: dict[str, dict], b: dict[str, dict], cls: str | None) -> dict:
    """Exact McNemar test on one class: do arms A and B differ in which variants they detect?"""
    only_a = only_b = 0
    for v in variants:
        if (v.defect_class or "clean") != (cls or "clean"):
            continue
        ha, hb = hit(v, a[v.id]["verdict"], a[v.id]["findings"]), hit(v, b[v.id]["verdict"], b[v.id]["findings"])
        only_a += ha and not hb
        only_b += hb and not ha
    disc = only_a + only_b
    p = 1.0 if disc == 0 else float(binomtest(min(only_a, only_b), disc, 0.5).pvalue)
    return {"only_first": only_a, "only_second": only_b, "p": p}


def cost(records: dict[str, dict]) -> dict[str, float]:
    """Mean and total tokens / seconds per audit (AD-3). Cached calls keep the original call's accounting."""
    n = len(records)
    tok = [r["tokens"] for r in records.values()]
    # Deterministic tiers: measured wall-clock. LLM calls: the RECORDED call latency, because a replayed call
    # returns instantly and would make the LLM arms look free.
    secs = [
        sum(t["seconds"] for name, t in r["tiers"].items() if name in ("T0", "T1"))
        + sum(c["seconds"] for t in r["tiers"].values() for c in t["llm_calls"])
        for r in records.values()
    ]
    return {
        "audits": n,
        "input_tokens_total": sum(t["input"] for t in tok),
        "output_tokens_billed_total": sum(t["output_billed"] for t in tok),
        "calls_total": sum(t["calls"] for t in tok),
        "input_tokens_mean": sum(t["input"] for t in tok) / n,
        "output_tokens_billed_mean": sum(t["output_billed"] for t in tok) / n,
        "seconds_mean": sum(secs) / n,
    }


def abstention_sweep(variants: list[Variant], records: dict[str, dict], thresholds=None) -> list[dict]:
    """Re-adjudicate the raw findings at several T2 conviction thresholds (escalate band = [t/2, t)).

    Gives the detection / false-positive / escalation trade-off (section 8.2). If T2 confidences saturate near 1.0
    the curve is flat, which is itself the finding: the model's stated confidence carries no abstention signal.
    """
    thresholds = thresholds or [round(0.1 * i, 1) for i in range(1, 11)]
    out = []
    for t in thresholds:
        det = fp = esc = nd = nc = 0
        for v in variants:
            r = records[v.id]
            res = adjudicate(v.id, raw_findings(r), r.get("checks_run", []), convict_at=t, escalate_at=t / 2)
            if v.clean:
                nc += 1
                fp += res.verdict is Verdict.OUT_OF_KILTER
            else:
                nd += 1
                det += hit(v, res.verdict.value, res.findings)
            esc += res.verdict is Verdict.ESCALATE
        out.append({"threshold": t, "detection": det / nd, "false_positive_rate": fp / max(1, nc),
                    "escalate_rate": esc / len(variants)})
    return out


def with_confidences(records: dict[str, dict]) -> list[float]:
    return [f.confidence for r in records.values() for f in raw_findings(r) if f.tier is Tier.T2 and f.kind is Kind.DEFECT]


__all__ = ["clopper_pearson", "load_records", "per_class", "paired_exact", "cost", "abstention_sweep", "escalations",
           "with_confidences", "replace"]

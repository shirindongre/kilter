"""Run one arm over all variants with the real pipeline, writing a run record per variant. Resumable.

usage: python scripts/run_arm.py A0|A1|A3|A4 [main|holdout]
A3 = T0+T1+T2 (needs artifacts: scripts/build_artifacts.py). A4 = T0+T1 only. Results: results/runs/ + results/<arm>_summary.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from evalutil import keep_evaluated
from kilter.defects.variants import generate_holdout, generate_variants
from kilter.eval.score import detected
from kilter.eval.arms import ARMS, run_arm

ROOT = Path(__file__).resolve().parents[1]


def main(arm: str, which: str = "main") -> None:
    if arm not in ARMS:
        raise SystemExit(f"arm must be one of {ARMS}")
    variants = generate_holdout() if which == "holdout" else generate_variants()
    tag = "" if which == "main" else f"_{which}"
    vdir = ROOT / "results" / "variants"
    keep_evaluated(variants, vdir)
    runs = ROOT / "results" / "runs" / f"{arm}{tag}"
    rows, t0 = [], time.time()
    for i, v in enumerate(variants, 1):
        t = time.time()
        res, r = run_arm(arm, vdir / f"{v.id}.py", v.id, runs)
        hit = detected(v, res)
        rows.append({"variant": v.id, "truth": v.defect_class, "verdict": r.verdict, "detected": hit,
                     "tokens": r.tokens(), "seconds": r.seconds_total(), "run_id": r.run_id,
                     "tiers": sorted({f["tier"] for f in r.findings if f["defect_class"] == v.defect_class})})
        mark = "FP " if (v.clean and hit) else ("hit" if hit else ("ok " if v.clean else "MISS"))
        print(f"[{i:2d}/{len(variants)}] {v.id:16s} {mark} {r.verdict:14s} tok_in={r.tokens()['input']:5d} "
              f"calls={r.tokens()['calls']} {time.time() - t:4.0f}s", flush=True)
    (ROOT / "results" / f"{arm}{tag}_summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "A3", sys.argv[2] if len(sys.argv) > 2 else "main")

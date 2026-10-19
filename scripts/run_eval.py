"""The full Phase 1 evaluation, in one deterministic pass over cached LLM responses (blueprint 5.3 Day 3).

usage: python scripts/run_eval.py            # replays fixtures: no network, no API key
       KILTER_LLM_MODE=record python scripts/run_eval.py   # records any response not yet in fixtures/llm

Clears results/runs first, so every record in the final tables comes from this pass and carries ONE code hash
(AIMS M-004). Arms: A0, A1, A3, A4; sets: main (48) and holdout (16), reported separately (AIMS D-018).
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("KILTER_LLM_MODE", "replay")

from kilter.defects.variants import generate_holdout, generate_variants, write_variants  # noqa: E402
from kilter.eval.arms import ARMS, run_arm  # noqa: E402
from kilter.eval import summarize  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    runs = ROOT / "results" / "runs"
    shutil.rmtree(runs, ignore_errors=True)
    vdir = ROOT / "results" / "variants"
    t0 = time.time()
    for which, gen in (("main", generate_variants), ("holdout", generate_holdout)):
        variants = gen()
        write_variants(variants, vdir)
        suffix = "" if which == "main" else "_holdout"
        for arm in ARMS:
            for i, v in enumerate(variants, 1):
                run_arm(arm, vdir / f"{v.id}.py", v.id, runs / f"{arm}{suffix}")
            print(f"{which:8s} {arm}: {len(variants)} audits  ({(time.time() - t0) / 60:.1f} min elapsed)", flush=True)
    summarize.build_all()
    print("wrote results/summary.json, results/phase1.json, results/results_table.md")


if __name__ == "__main__":
    sys.exit(main())

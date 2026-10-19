"""Execute all variants of a set for real and cache their artifacts. Resumable: cached variants are skipped.

usage: python scripts/build_artifacts.py [main|holdout]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from kilter.defects.variants import generate_holdout, generate_holdout2, generate_variants, write_variants
from kilter.eval.artifacts import ARTIFACT_DIR, ARTIFACT_SEEDS, artifact_for

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "main"
    variants = {"holdout": generate_holdout, "holdout2": generate_holdout2}.get(which, generate_variants)()
    out = ROOT / "results" / "variants"
    write_variants(variants, out)
    t0 = time.time()
    for i, v in enumerate(variants, 1):
        path = out / f"{v.id}.py"
        t = time.time()
        try:
            art = artifact_for(path)
            r = art["result"]
            print(f"[{i:2d}/{len(variants)}] {v.id:16s} auroc={r['auroc_mean']:.3f} "
                  f"({art['run_seconds']}s, {time.time() - t:.0f}s wall)", flush=True)
        except Exception as e:  # keep going: one broken variant must not hide the rest
            print(f"[{i:2d}/{len(variants)}] {v.id:16s} FAILED {type(e).__name__}: {e}", flush=True)
    print(f"done in {(time.time() - t0) / 60:.1f} min; seeds={ARTIFACT_SEEDS}; dir={ARTIFACT_DIR}", flush=True)


if __name__ == "__main__":
    sys.exit(main())

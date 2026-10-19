"""Record a clean reference analysis's metrics under BOTH random and scaffold splits (blueprint P0.5).

The random-vs-scaffold delta is the ground truth D3 / AD-9 needs, and the multi-seed spread is
required by §8.3 (single-seed chemistry results are invalid, REF-18).

usage: python scripts/record_reference_metrics.py bace [n_seeds]
"""
from __future__ import annotations

import importlib.util
import json
import platform
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_reference(name: str):
    path = ROOT / "references" / f"{name}_clean.py"
    spec = importlib.util.spec_from_file_location(f"reference_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "bace"
    n_seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ref = load_reference(name)
    out = {
        "reference": f"references/{name}_clean.py",
        "date": date.today().isoformat(),
        "n_seeds": n_seeds,
        "versions": {"python": platform.python_version(), **{p: version(p) for p in ("numpy", "scikit-learn", "rdkit", "scikit-fingerprints")}},
        "splits": {},
    }
    for split in ("random", "scaffold", "scaffold_det"):
        res = ref.run(split=split, n_seeds=n_seeds)
        out["splits"][split] = {k: res[k] for k in ("auroc_mean", "auroc_sd", "comparisons", "conclusion")}
        print(f"{name} {split}: AUROC {res['auroc_mean']:.3f} +/-{res['auroc_sd']:.3f}", flush=True)
    rand = out["splits"]["random"]["auroc_mean"]
    out["random_minus"] = {k: rand - out["splits"][k]["auroc_mean"] for k in ("scaffold", "scaffold_det")}
    for k, v in out["random_minus"].items():
        print(f"random - {k} = {v:+.3f} AUROC", flush=True)
    dest = ROOT / "results" / f"reference_metrics_{name}.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

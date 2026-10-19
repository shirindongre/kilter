"""Execute an audited script for real and cache its result: the "executed artifact" T2 reasons over (AD-2).

Content-addressed by the script's hash, so identical sources never run twice and a changed script can never
be served a stale artifact. Cost is real model fitting (~1 min per variant), paid once.
"""
from __future__ import annotations

import hashlib
import json
import time
import warnings
from pathlib import Path

from kilter.core.tiers.t1_runtime import _load

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = ROOT / "results" / "artifacts"
FIXTURE_ARTIFACT_DIR = ROOT / "fixtures" / "artifacts"
ARTIFACT_SEEDS = 6  # >= 6 so an exact Wilcoxon test can reach p < 0.05; the same value for every variant (AIMS D-013)


def source_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_for(path: str | Path, *, n_seeds: int = ARTIFACT_SEEDS, cache_dir: Path = ARTIFACT_DIR) -> dict:
    path = Path(path)
    key = f"{source_hash(path)[:16]}-s{n_seeds}"
    cached = cache_dir / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    shipped = FIXTURE_ARTIFACT_DIR / f"{key}.json"  # tracked copies, so the offline demo needs no model fitting
    if shipped.exists():
        return json.loads(shipped.read_text(encoding="utf-8"))
    mod = _load(path)
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = mod.run(n_seeds=n_seeds)
    art = {"script": path.name, "source_sha256": source_hash(path), "n_seeds": n_seeds,
           "run_seconds": round(time.time() - t0, 1), "result": result}
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(art, indent=2), encoding="utf-8")
    return art

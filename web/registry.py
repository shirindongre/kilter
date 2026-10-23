"""The scripts the UI can audit without an upload: the 3 demos and the 80 generated evaluation variants.

Variants come from the same generators as the evaluation (`kilter.defects.variants`), so each one carries its planted
ground truth (class and site line). Nothing here needs `results/`; it needs only `references/`, which is in the repo.
Auditing a variant with the critic additionally needs its executed artifact (results/artifacts, ~1 min each to
build) and a recorded critic response (fixtures/llm).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEMOS = [
    dict(id="demo-clean-bace", file="1_clean_bace.py", base="bace", planted_class=None,
         label="A clean analysis",
         description="BACE-1, ECFP with a random forest, scaffold split stated and held out. Nothing is wrong with it."),
    dict(id="demo-leakage-bbbp", file="2_leakage_bbbp.py", base="bbbp", planted_class="D1",
         label="Test data leaks into preprocessing",
         description="BBBP. A preprocessing step is fitted on every row before the split, so the test set shapes the model."),
    dict(id="demo-overclaim-bace", file="3_overclaim_bace.py", base="bace", planted_class="D5",
         label="The numbers are fine, the conclusion is not",
         description="BACE-1. The statistics are sound; the written conclusion claims more than they show."),
]


def demo_samples() -> list[dict]:
    return [dict(d, kind="demo", group="demo", site_line=None, path=ROOT / "demo" / d["file"]) for d in DEMOS]


def variant_samples(work_dir: Path) -> list[dict]:
    """The 80 variants, written into work_dir. If results/variants holds the bytes the evaluation audited they replace
    the regenerated ones: generation goes through ast.unparse, whose f-string quoting differs between Python minor
    versions (3.11 vs 3.12 changes 16 of the 80 files), and the artifact and critic caches are keyed to the bytes."""
    from kilter.defects.variants import generate_holdout, generate_holdout2, generate_variants, write_variants

    out = []
    work_dir.mkdir(parents=True, exist_ok=True)
    for gen in (generate_variants, generate_holdout, generate_holdout2):
        vs = gen()
        write_variants(vs, work_dir)   # same writer as the evaluation, so line endings and bytes match its artifacts
        for v in vs:
            evaluated = ROOT / "results" / "variants" / f"{v.id}.py"
            if evaluated.exists():
                (work_dir / f"{v.id}.py").write_bytes(evaluated.read_bytes())
        out += [dict(id=v.id, kind="variant", label=v.id, group=v.group, base=v.base, planted_class=v.defect_class,
                     site_line=v.site_line, description=v.description, path=work_dir / f"{v.id}.py") for v in vs]
    return out


def artifact_ready(path: Path) -> bool:
    from kilter.eval.artifacts import ARTIFACT_DIR, ARTIFACT_SEEDS, FIXTURE_ARTIFACT_DIR, source_hash

    key = f"{source_hash(path)[:16]}-s{ARTIFACT_SEEDS}.json"
    return (ARTIFACT_DIR / key).exists() or (FIXTURE_ARTIFACT_DIR / key).exists()


def public(sample: dict) -> dict:
    """The sample as the browser may see it: no filesystem path."""
    return {k: v for k, v in sample.items() if k not in ("path", "file") and not k.startswith("_")}

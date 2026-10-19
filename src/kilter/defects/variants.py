"""Build the Phase 1 variant set (AD-4): clean analyses and analyses with exactly one planted defect.

Design: 2 references x 4 benign configurations = 8 CLEAN bases. Each defect class D1-D4 is injected into each
clean base, giving 8 defective variants per class with exact ground truth (class + site line). Benign
configurations change hyperparameters only, so a checker that fires on them is a false positive by construction.
D5 (overclaiming conclusions) has no sound check and is hand-authored (defects/d5_overclaim.py): 8 more variants, 48 in all (AIMS Q-005).
"""
from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from kilter.defects import d5_overclaim, holdout, holdout2
from kilter.defects.injectors import d1_leakage, d2_duplicates, d3_split, d4_multiplicity
from kilter.defects.injectors.base import render

REFERENCES_DIR = Path(__file__).resolve().parents[3] / "references"

# Module-level constant overrides per benign configuration (index 0 = the reference as written).
BENIGN: dict[str, list[dict[str, object]]] = {
    "bace": [{}, {"K_FEATURES": 256}, {"K_FEATURES": 1024, "TEST_SIZE": 0.25}, {"N_SEEDS": 5, "TEST_SIZE": 0.15}],
    "bbbp": [{}, {"N_FEATURES": 200}, {"N_FEATURES": 800, "TEST_FRACTION": 0.25}, {"N_REPEATS": 5, "TEST_FRACTION": 0.15}],
}
DEFECT_CLASSES = ("D1", "D2", "D3", "D4")   # injectable by AST transform; sound tiers target these
ALL_CLASSES = (*DEFECT_CLASSES, "D5")        # D5 is hand-authored and has no sound check


@dataclass(frozen=True)
class Variant:
    id: str
    base: str                  # reference name
    benign: int                # benign configuration index
    defect_class: str | None   # None = clean
    site_line: int | None      # ground-truth line of the defect in `source`
    description: str
    source: str
    group: str = "main"       # "main" or "holdout" (AIMS D-018): never pooled in a results table

    @property
    def clean(self) -> bool:
        return self.defect_class is None

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("source")
        return d


def _apply_benign(source: str, overrides: dict[str, object]) -> str:
    tree = ast.parse(source)
    seen: set[str] = set()
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id in overrides:
                n.value = ast.Constant(overrides[n.targets[0].id])
                seen.add(n.targets[0].id)
    missing = set(overrides) - seen
    if missing:
        raise KeyError(f"benign override for constants not in reference: {sorted(missing)}")
    return render(tree)


def _inject(cls: str, source: str, benign: int):
    if cls == "D1":
        return d1_leakage.inject(source)
    if cls == "D2":
        return d2_duplicates.inject(source)
    if cls == "D3":
        # Alternate the two ways D3 occurs so both are represented for each reference.
        return d3_split.inject(source, "random" if benign < 2 else "unstated")
    if cls == "D4":
        return d4_multiplicity.inject(source)
    raise ValueError(cls)


def _author_d5(source: str, base: str, benign: int):
    return d5_overclaim.inject(source, base, benign)


def generate_variants(references_dir: Path = REFERENCES_DIR) -> list[Variant]:
    out: list[Variant] = []
    for base, configs in BENIGN.items():
        raw = (references_dir / f"{base}_clean.py").read_text(encoding="utf-8")
        for b, overrides in enumerate(configs):
            clean_src = _apply_benign(raw, overrides)
            out.append(Variant(f"{base}-b{b}-clean", base, b, None, None, "verified-clean analysis", clean_src))
    clean = list(out)
    for cls in DEFECT_CLASSES:
        for v in clean:
            inj = _inject(cls, v.source, v.benign)
            out.append(Variant(f"{v.base}-b{v.benign}-{cls}", v.base, v.benign, cls, inj.site_line, inj.description, inj.source))
    for v in clean:
        inj = _author_d5(v.source, v.base, v.benign)
        out.append(Variant(f"{v.base}-b{v.benign}-D5", v.base, v.benign, "D5", inj.site_line, inj.description, inj.source))
    return out


def generate_holdout(references_dir: Path = REFERENCES_DIR) -> list[Variant]:
    """16 holdout variants over the same 8 clean bases: 8 subtle D5 (-H5) and 8 honest-but-confident clean (-HC)."""
    out: list[Variant] = []
    for v in (x for x in generate_variants(references_dir) if x.clean):
        for suffix, table, cls in (("H5", holdout.SUBTLE, "D5"), ("HC", holdout.HONEST, None)):
            kind, expr = table[(v.base, v.benign)]
            inj = d5_overclaim.splice_conclusion(v.source, expr, cls, f"holdout ({suffix}): {kind}")
            out.append(Variant(f"{v.base}-b{v.benign}-{suffix}", v.base, v.benign, cls, inj.site_line if cls else None,
                               inj.description, inj.source, group="holdout"))
    return out


def generate_holdout2(references_dir: Path = REFERENCES_DIR) -> list[Variant]:
    """16 fresh variants (AIMS D-022): 8 beyond-the-data D5 (-B5) and 8 honest-but-confident clean (-HC2). Own group, never pooled."""
    out: list[Variant] = []
    for v in (x for x in generate_variants(references_dir) if x.clean):
        for suffix, table, cls in (("B5", holdout2.BEYOND, "D5"), ("HC2", holdout2.HONEST, None)):
            kind, expr = table[(v.base, v.benign)]
            inj = d5_overclaim.splice_conclusion(v.source, expr, cls, f"holdout2 ({suffix}): {kind}")
            out.append(Variant(f"{v.base}-b{v.benign}-{suffix}", v.base, v.benign, cls, inj.site_line if cls else None,
                               inj.description, inj.source, group="holdout2"))
    return out


def write_variants(variants: list[Variant], out_dir: Path) -> Path:
    """Write each variant as <id>.py plus manifest.json (ground truth). Returns the manifest path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for v in variants:
        (out_dir / f"{v.id}.py").write_text(v.source, encoding="utf-8")
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps([v.meta() for v in variants], indent=2), encoding="utf-8")
    return manifest

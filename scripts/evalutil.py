"""Shared by the evaluation scripts. Lives in scripts/, outside src/kilter, so it does not enter the code hash."""
from __future__ import annotations

from pathlib import Path

from kilter.defects.variants import write_variants


def keep_evaluated(variants, vdir: Path) -> None:
    """Write only the variants that are not in `vdir` yet.

    results/variants is tracked: those bytes are what was evaluated, and the artifact cache, the critic recordings
    and every run record's input hash are keyed to them. Regenerating overwrites them, and the generator is not
    byte-stable across Python minor versions (ast.unparse, AIMS L-012), so an existing file is never replaced.
    """
    missing = [v for v in variants if not (vdir / f"{v.id}.py").exists()]
    if missing:
        write_variants(missing, vdir)

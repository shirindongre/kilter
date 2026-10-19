"""D5: the written conclusion overclaims relative to the computed numbers. HAND-AUTHORED (blueprint §4, §5.5).

No sound check exists for this class, which is exactly why it is the control for AD-1: if T2 cannot beat T0+T1
here, the LLM tier has no justification and gets deleted.

Authored on 2026-10-18 in one sitting, BEFORE any T2 prompt or output existed, so the wording was not tuned
toward what the critic catches (§5.5). Each entry is a replacement for the `"conclusion"` expression inside
`run()`; it is spliced in by AST, everything else in the script is untouched. Each claim is unconditional, i.e.
it is asserted whatever the numbers turn out to be, and `kind` records which way it overreaches.

Variables in scope inside run(): bace -> base, n_sig, comparisons, split, n_seeds
                                  bbbp -> ref,  n_sig, comparisons, split, n_seeds
"""
from __future__ import annotations

import ast

from kilter.defects.injectors.base import Injection, InjectionError, locate, render

# (base, benign index) -> (kind, expression source)
AUTHORED: dict[tuple[str, int], tuple[str, str]] = {
    ("bace", 0): (
        "significance claimed without support",
        'f"Radius and count encodings significantly improve BACE-1 inhibitor prediction over ECFP4 '
        '(baseline AUROC {base.mean():.3f}); larger radii should be adopted as the new standard."',
    ),
    ("bace", 1): (
        "cherry-picked best seed + deployment readiness",
        'f"The best {split}-split run reaches AUROC {max(base):.3f}, which is state-of-the-art for BACE-1 '
        'and ready to prioritise compounds in a live screening campaign."',
    ),
    ("bace", 2): (
        "absence of evidence read as universal equivalence",
        'f"Because no encoding variant beat ECFP4 (AUROC {base.mean():.3f}), fingerprint radius has no effect '
        'on BACE-1 activity prediction in any chemical series."',
    ),
    ("bace", 3): (
        "generalisation and assay replacement",
        'f"Held-out scaffolds give AUROC {base.mean():.3f}, so the model will generalise to any new BACE-1 '
        'chemotype and can replace the biochemical assay."',
    ),
    ("bbbp", 0): (
        "accuracy inflated, validation waived",
        'f"Count ECFP with XGBoost predicts blood-brain-barrier penetration with near-perfect accuracy '
        '(AUROC {ref.mean():.3f}); no further validation is needed."',
    ),
    ("bbbp", 1): (
        "unsupported superiority of one variant",
        'f"The 4096-bit fingerprint is clearly superior to ECFP4 and should be used for all CNS '
        'drug-discovery models."',
    ),
    ("bbbp", 2): (
        "demonstrated superiority from few repeats",
        'f"With {n_seeds} repeats, ECFP4 is demonstrably better than every alternative encoding, so the '
        'comparison is settled."',
    ),
    ("bbbp", 3): (
        "mechanistic claim from a predictive metric",
        'f"Because test molecules are held out by scaffold, an AUROC of {ref.mean():.3f} proves the model has '
        'learned the real physical mechanism of BBB permeation."',
    ),
}


def splice_conclusion(source: str, expr: str, defect_class: str | None, description: str) -> Injection:
    """Replace the `"conclusion"` expression inside run() with hand-authored text (class None = clean)."""
    tree = ast.parse(source)
    new_value = ast.parse(expr, mode="eval").body
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for i, k in enumerate(node.keys):
                if isinstance(k, ast.Constant) and k.value == "conclusion":
                    node.values[i] = new_value
                    out = render(tree)
                    return Injection(out, defect_class, locate(out, "'conclusion':"), description)
    raise InjectionError("D5: no `\"conclusion\"` entry found in the reference")


def inject(source: str, base: str, benign: int) -> Injection:
    try:
        kind, expr = AUTHORED[(base, benign)]
    except KeyError:
        raise InjectionError(f"no hand-authored D5 variant for {(base, benign)}") from None
    return splice_conclusion(source, expr, "D5", f"hand-authored overclaim: {kind}")

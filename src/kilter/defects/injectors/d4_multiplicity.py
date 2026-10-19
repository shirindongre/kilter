"""D4: drop the multiple-comparison correction so raw p-values are reported as the final ones (REF-3)."""
from __future__ import annotations

import ast

from kilter.core import astutil as au
from kilter.defects.injectors.base import Injection, InjectionError, locate, render, rewrite_blocks


def inject(source: str) -> Injection:
    tree = ast.parse(source)
    needle: list[str] = []

    def fn(st: ast.stmt):
        if (isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) and st.value.args
                and (name := au.call_name(st.value)) and au.CORRECTION_RE.search(name)):
            new = ast.copy_location(ast.Assign(targets=st.targets, value=st.value.args[0]), st)  # p_adj = p_raw
            needle.append(ast.unparse(new))
            return [new]
        return None

    if not rewrite_blocks(tree, fn):
        raise InjectionError("D4: no `adjusted = <correction>(p_values)` assignment found")
    out = render(tree)
    return Injection(out, "D4", locate(out, needle[0]),
                     "correction removed; raw p-values are used as the adjusted p-values")

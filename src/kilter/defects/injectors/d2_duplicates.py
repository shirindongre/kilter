"""D2: test molecules also present in the training set (REF-1, REF-15).

Injected after the split rather than before it: a scaffold split keeps identical molecules together, so
duplicating before the split would not cross the boundary. The realistic bug is augmenting or merging the
training set from a pool that still contains test rows.
"""
from __future__ import annotations

import ast

from kilter.core import astutil as au
from kilter.defects.injectors.base import Injection, InjectionError, locate, render, rewrite_blocks


def inject(source: str) -> Injection:
    tree = ast.parse(source)
    needle: list[str] = []

    def fn(st: ast.stmt):
        if (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Tuple)
                and len(st.targets[0].elts) == 2 and all(isinstance(e, ast.Name) for e in st.targets[0].elts)
                and "split" in (au.call_name(st.value) or "").lower()):
            train, test = (e.id for e in st.targets[0].elts)
            leak = ast.parse(f"{train} = np.concatenate([{train}, {test}[:max(1, len({test}) // 10)]])").body[0]
            needle.append(ast.unparse(leak))
            return [st, leak]
        return None

    if not rewrite_blocks(tree, fn):
        raise InjectionError("D2: no `train, test = <split>(...)` unpacking found")
    has_np = any(isinstance(n, ast.Import) and any(a.name == "numpy" and a.asname == "np" for a in n.names)
                 for n in tree.body)
    if not has_np:
        tree.body.insert(1, ast.parse("import numpy as np").body[0])
    out = render(tree)
    return Injection(out, "D2", locate(out, needle[0]),
                     "10% of the test molecules are appended to the training indices")

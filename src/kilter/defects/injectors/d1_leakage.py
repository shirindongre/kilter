"""D1: fit preprocessing on the full data instead of the training rows (REF-1 leakage taxonomy)."""
from __future__ import annotations

import ast

from kilter.core import astutil as au
from kilter.defects.injectors.base import Injection, InjectionError, locate, render, rewrite_blocks


def inject(source: str) -> Injection:
    tree = ast.parse(source)
    preproc = {
        t
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign) and au.call_name(n.value) in au.PREPROC_CTORS
        for tgt in n.targets
        for t in au.target_names(tgt)
    }
    needle: list[str] = []

    def is_train_slice(a: ast.AST) -> bool:
        return (isinstance(a, ast.Subscript) and isinstance(a.slice, ast.Name)
                and au.partition_role(a.slice.id) == "train")

    def on_preproc(call: ast.Call, method: str) -> bool:
        f = call.func
        return (isinstance(f, ast.Attribute) and f.attr == method and isinstance(f.value, ast.Name)
                and f.value.id in preproc and any(is_train_slice(a) for a in call.args))

    def widen(call: ast.Call) -> list[ast.expr]:
        return [a.value if is_train_slice(a) else a for a in call.args]

    def fn(st: ast.stmt):
        # `prep.fit(X[train], y[train])`  ->  `prep.fit(X, y)`
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and on_preproc(st.value, "fit"):
            new = ast.Expr(ast.Call(func=st.value.func, args=widen(st.value), keywords=st.value.keywords))
            needle.append(ast.unparse(new))
            return [new]
        # `Xt = prep.fit_transform(X[train], y[train])`  ->  `prep.fit(X, y)` ; `Xt = prep.transform(X[train])`
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) and on_preproc(st.value, "fit_transform"):
            recv = st.value.func.value
            fit_stmt = ast.Expr(ast.Call(
                func=ast.Attribute(value=recv, attr="fit", ctx=ast.Load()),
                args=widen(st.value), keywords=st.value.keywords,
            ))
            transform = ast.Call(
                func=ast.Attribute(value=recv, attr="transform", ctx=ast.Load()),
                args=st.value.args[:1], keywords=[],
            )
            needle.append(ast.unparse(fit_stmt))
            return [fit_stmt, ast.Assign(targets=st.targets, value=transform)]
        return None

    if not rewrite_blocks(tree, fn):
        raise InjectionError("D1: no train-only preprocessing fit found to widen")
    out = render(tree)
    return Injection(out, "D1", locate(out, needle[0]),
                     "preprocessing fit on all rows (train + test) before the model sees the split")

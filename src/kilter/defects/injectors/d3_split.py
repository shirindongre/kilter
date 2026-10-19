"""D3: split protocol random where novel scaffolds are claimed, or not stated at all (REF-14, REF-15, REF-18)."""
from __future__ import annotations

import ast
import re

from kilter.core import astutil as au
from kilter.defects.injectors.base import Injection, InjectionError, locate, render

SPLIT_DECL_RE = re.compile(r"^split(_?(protocol|method|type|strategy|kind))?$", re.I)


def _declaration(tree: ast.Module) -> tuple[int, ast.Assign]:
    for i, n in enumerate(tree.body):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                and SPLIT_DECL_RE.match(n.targets[0].id) and isinstance(n.value, ast.Constant)):
            return i, n
    raise InjectionError("D3: no module-level split declaration found")


def inject(source: str, mode: str) -> Injection:
    tree = ast.parse(source)
    i, decl = _declaration(tree)
    name, original = decl.targets[0].id, decl.value.value

    if mode == "random":
        decl.value = ast.Constant("random")
        out = render(tree)
        return Injection(out, "D3", locate(out, f"{name} = 'random'"),
                         "stated split protocol swapped to random while the claim is novel scaffolds")

    if mode == "unstated":
        del tree.body[i]
        chooser = au.protocol_chooser(tree, SPLIT_DECL_RE)
        if chooser is None:
            raise InjectionError("D3: no function chooses the split protocol")

        class Inline(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name):
                return ast.copy_location(ast.Constant(original), node) if node.id == name else node

            def visit_Dict(self, node: ast.Dict):
                self.generic_visit(node)
                keep = [(k, v) for k, v in zip(node.keys, node.values)
                        if not (isinstance(k, ast.Constant) and k.value == "split")]
                node.keys, node.values = [k for k, _ in keep], [v for _, v in keep]
                return node

        tree = ast.fix_missing_locations(Inline().visit(tree))
        out = render(tree)
        return Injection(out, "D3", locate(out, f"def {chooser.name}("),
                         "split protocol no longer declared or reported; the value is a buried default")
    raise ValueError(f"unknown D3 mode {mode!r}")

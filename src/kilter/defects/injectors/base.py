"""Shared machinery for AST-transform injectors (AD-4): one clean script in, one script with exactly one defect out."""
from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass


class InjectionError(RuntimeError):
    """The reference has no site this injector can corrupt (a bug in the reference or the injector, never silent)."""


@dataclass(frozen=True)
class Injection:
    source: str
    defect_class: str
    site_line: int       # ground truth: 1-indexed line in `source` where the defect lives
    description: str


def locate(source: str, needle: str) -> int:
    for i, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return i
    raise InjectionError(f"injected text {needle!r} not found in output")


def rewrite_blocks(tree: ast.AST, fn: Callable[[ast.stmt], list[ast.stmt] | None]) -> bool:
    """Apply `fn` to statements in every block until it rewrites one (so exactly one defect is planted).

    `fn` returns the replacement statement list, or None to leave the statement alone.
    """
    blocks = [
        (node, field)
        for node in ast.walk(tree)
        for field in ("body", "orelse", "finalbody")
        if isinstance(getattr(node, field, None), list)
    ]
    for node, field in blocks:
        block = getattr(node, field)
        for i, stmt in enumerate(block):
            replacement = fn(stmt)
            if replacement is not None:
                block[i : i + 1] = replacement
                return True
    return False


def render(tree: ast.Module) -> str:
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"

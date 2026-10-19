"""T0: static analysis of the analysis code (AD-1). Sound-by-construction rules over the AST; nothing is executed.

Each rule fires only on a pattern that is wrong regardless of the data, and every finding carries the
line and the code that triggered it. Rules are heuristic about *naming* (see core/astutil.py), so a
non-conforming script yields no finding rather than a wrong one; T1 and T2 cover what T0 cannot see.
"""
from __future__ import annotations

import ast
import re

from kilter.core import astutil as au
from kilter.core.findings import Finding, Kind, Tier

SCAFFOLD_CLAIM_RE = re.compile(r"scaffold|novel|chemotype|unseen", re.I)
SPLIT_DECL_RE = re.compile(r"^split(_?(protocol|method|type|strategy|kind))?$", re.I)

CHECKS = ("T0.leakage", "T0.split-protocol", "T0.multiple-comparisons")


def run_t0(source: str, filename: str = "<script>") -> tuple[list[Finding], list[str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        bad = Finding("D1", Tier.T0, Kind.INCONCLUSIVE, "Script does not parse; static checks skipped.",
                      str(e), "T0.parse", filename, e.lineno)
        return [bad], []
    findings = [*_leakage(tree, filename), *_split_protocol(tree, filename), *_multiple_comparisons(tree, filename)]
    return findings, list(CHECKS)


# --- D1: preprocessing fit on data that includes the test partition -------------------------------

def _leakage(tree: ast.Module, fname: str) -> list[Finding]:
    out: list[Finding] = []
    for scope in au.scopes(tree):
        nodes = list(au.walk_scope(scope))
        preproc: set[str] = set()
        index_names: set[str] = set()
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            index_names |= {a.arg for a in [*scope.args.args, *scope.args.kwonlyargs] if au.partition_role(a.arg)}
        for n in nodes:
            if isinstance(n, ast.Assign):
                names = [x for t in n.targets for x in au.target_names(t)]
                cname = au.call_name(n.value)
                if cname in au.PREPROC_CTORS:
                    preproc.update(names)
                if cname and "split" in cname.lower():
                    index_names.update(names)
                index_names.update(x for x in names if au.partition_role(x))

        # arrays that are sliced by partition indices anywhere in this scope are "partitioned" arrays
        sliced: dict[str, list[tuple[int, str]]] = {}
        for n in nodes:
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and isinstance(n.slice, ast.Name):
                if n.slice.id in index_names:
                    sliced.setdefault(n.value.id, []).append((n.lineno, n.slice.id))

        sk_splits = [
            n for n in nodes
            if isinstance(n, ast.Assign) and au.call_name(n.value) == "train_test_split"
        ]
        for n in nodes:
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in au.FIT_METHODS):
                continue
            recv = n.func.value
            if not ((isinstance(recv, ast.Name) and recv.id in preproc) or au.call_name(recv) in au.PREPROC_CTORS):
                continue
            reasons: list[str] = []
            for a in n.args:
                if isinstance(a, ast.Name) and a.id in sliced:
                    where = ", ".join(f"`{a.id}[{s}]` (line {ln})" for ln, s in sliced[a.id][:3])
                    reasons.append(f"`{a.id}` is the full array, also partitioned as {where}")
                elif (isinstance(a, ast.Subscript) and isinstance(a.slice, ast.Name)
                      and au.partition_role(a.slice.id) == "test"):
                    reasons.append(f"`{ast.unparse(a)}` is the test partition")
                elif isinstance(a, ast.Name):
                    for sp in sk_splits:
                        split_args = [x.id for x in sp.value.args if isinstance(x, ast.Name)]
                        if a.id in split_args and n.lineno < sp.lineno:
                            reasons.append(f"`{a.id}` is fit before it is split by `train_test_split` (line {sp.lineno})")
            if reasons:
                out.append(Finding(
                    "D1", Tier.T0, Kind.DEFECT,
                    "Preprocessing is fit on data that includes the test partition (leakage, REF-1).",
                    f"`{ast.unparse(n)}`: " + "; ".join(dict.fromkeys(reasons)),
                    "T0.leakage", fname, n.lineno,
                ))
    return out


# --- D3: split protocol unstated, or random where novel scaffolds are claimed ---------------------

def _split_protocol(tree: ast.Module, fname: str) -> list[Finding]:
    consts = au.module_constants(tree)
    decl = next(((k, v) for k, v in consts.items() if SPLIT_DECL_RE.match(k) and isinstance(v[0], str)), None)
    claim = " ".join(str(v[0]) for k, v in consts.items() if "claim" in k.lower() and isinstance(v[0], str))
    claim += " " + (ast.get_docstring(tree) or "")
    claims_scaffold = bool(SCAFFOLD_CLAIM_RE.search(claim))

    if decl is not None:
        name, (value, line) = decl
        if claims_scaffold and "scaffold" not in value.lower():
            return [Finding(
                "D3", Tier.T0, Kind.DEFECT,
                f"Stated split protocol is {value!r}, which does not hold scaffolds out, but the analysis claims "
                "generalisation to novel scaffolds (REF-14, REF-15).",
                f"`{name} = {value!r}` at line {line}; claim text mentions scaffolds/novelty",
                "T0.split-protocol", fname, line,
            )]
        return []

    splits = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and "split" in (au.call_name(n) or "").lower()]
    if not splits:
        return []  # nothing is partitioned, so there is no protocol to state
    chooser = au.protocol_chooser(tree, SPLIT_DECL_RE)
    line = chooser.lineno if chooser else min(n.lineno for n in splits)
    return [Finding(
        "D3", Tier.T0, Kind.UNREPORTED,
        "The train/test split protocol is not stated anywhere in the analysis. Reported metrics depend on it "
        "(REF-16, REF-18); Kilter flags the omission and does not assert a single correct protocol (AD-9).",
        f"no module-level split declaration; split is chosen at line {line}",
        "T0.split-protocol", fname, line,
    )]


# --- D4: significance reported for a family of tests with no multiplicity correction --------------

def _multiple_comparisons(tree: ast.Module, fname: str) -> list[Finding]:
    parents = au.parent_map(tree)
    tests = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and au.call_name(n) in au.STAT_TESTS]
    if not tests:
        return []

    def repeated(call: ast.AST) -> bool:
        p = parents.get(call)
        while p is not None:
            if isinstance(p, au.LOOP_NODES):
                return True
            p = parents.get(p)
        return False

    if not (len(tests) >= 2 or any(repeated(t) for t in tests)):
        return []  # a single test is not a family

    corrections = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_correction(au.call_name(n))]
    first = min(tests, key=lambda n: n.lineno)
    family = f"{len(tests)} significance-test call site(s) ({au.call_name(first)}, line {first.lineno})"
    if corrections:
        if _correction_used(tree, corrections):
            return []
        c = corrections[0]
        return [Finding(
            "D4", Tier.T0, Kind.DEFECT,
            "A multiple-comparison correction is computed but its result is never used.",
            f"{family}; `{ast.unparse(c)}` at line {c.lineno} is not assigned to a name that is read later",
            "T0.multiple-comparisons", fname, c.lineno,
        )]
    return [Finding(
        "D4", Tier.T0, Kind.DEFECT,
        "A family of significance tests is reported with no multiple-comparison correction.",
        f"{family}, repeated across comparisons; no Bonferroni/Holm/FDR call found",
        "T0.multiple-comparisons", fname, first.lineno,
    )]


def _is_correction(name: str | None) -> bool:
    return bool(name and au.CORRECTION_RE.search(name))


def _correction_used(tree: ast.Module, corrections: list[ast.Call]) -> bool:
    assigned: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and n.value in corrections:
            assigned.update(x for t in n.targets for x in au.target_names(t))
    if not assigned:
        return True  # used inline, e.g. as an argument or in a return; assume consumed
    loads = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return bool(assigned & loads)

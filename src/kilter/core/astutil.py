"""Small AST helpers shared by T0 and the defect injectors.

Heuristics here are deliberately name-based (train/test index naming, known sklearn constructors).
Because injectors and checkers share them, a detection rate on injected defects partly measures
agreement between the two (AD-4's known limitation); style diversity across references is the mitigation.
"""
from __future__ import annotations

import ast
import re
from collections.abc import Iterator

PREPROC_CTORS = frozenset(
    {
        "Pipeline", "make_pipeline", "StandardScaler", "MinMaxScaler", "RobustScaler", "MaxAbsScaler",
        "Normalizer", "SelectKBest", "SelectPercentile", "SelectFromModel", "VarianceThreshold", "PCA",
        "TruncatedSVD", "SimpleImputer", "RFE", "RFECV",
    }
)
FIT_METHODS = frozenset({"fit", "fit_transform"})
TRAIN_TOKENS = frozenset({"train", "tr"})
TEST_TOKENS = frozenset({"test", "te", "valid", "val", "holdout"})
STAT_TESTS = frozenset(
    {
        "wilcoxon", "ttest_rel", "ttest_ind", "ttest_1samp", "mannwhitneyu", "kruskal", "f_oneway",
        "chi2_contingency", "fisher_exact", "pearsonr", "spearmanr", "kendalltau", "friedmanchisquare",
    }
)
CORRECTION_RE = re.compile(
    r"(holm|bonferroni|bonf|fdr|benjamini|hochberg|sidak|multipletests|false_discovery|multiple_?comp|p_?adjust|adjust_?p)",
    re.I,
)
LOOP_NODES = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def call_name(node: ast.AST) -> str | None:
    """Last component of a call's callee: `a.b.fit(...)` -> "fit", `Foo(...)` -> "Foo"."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def partition_role(name: str) -> str | None:
    """"train" / "test" if the identifier looks like a partition index or array, else None."""
    tokens = set(name.lower().split("_"))
    if tokens & TRAIN_TOKENS:
        return "train"
    if tokens & TEST_TOKENS:
        return "test"
    return None


def target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for e in target.elts for n in target_names(e)]
    return []


def walk_scope(node: ast.AST) -> Iterator[ast.AST]:
    """Walk a function (or module) body without descending into nested function/class definitions."""
    stack = list(reversed(getattr(node, "body", [])))
    while stack:
        n = stack.pop()
        yield n
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(n))))


def scopes(tree: ast.Module) -> Iterator[ast.AST]:
    yield tree
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def protocol_chooser(tree: ast.Module, name_re: re.Pattern[str]) -> ast.FunctionDef | None:
    """The function where the split protocol is chosen: one with a *defaulted* split-like parameter
    (a caller-facing entry point such as `run(split=...)`), else any function with a split-like parameter."""
    fallback = None
    for n in ast.walk(tree):
        if not isinstance(n, ast.FunctionDef):
            continue
        a = n.args
        positional = [*a.posonlyargs, *a.args]
        defaulted = {p.arg for p in positional[len(positional) - len(a.defaults):]} if a.defaults else set()
        defaulted |= {p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None}
        names = {p.arg for p in [*positional, *a.kwonlyargs]}
        if any(name_re.match(x) for x in defaulted):
            return n
        if fallback is None and any(name_re.match(x) for x in names):
            fallback = n
    return fallback


def module_constants(tree: ast.Module) -> dict[str, tuple[object, int]]:
    """Top-level `NAME = <literal>` assignments -> (value, lineno)."""
    out: dict[str, tuple[object, int]] = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = (ast.literal_eval(n.value), n.lineno)
            except (ValueError, SyntaxError):
                pass
    return out

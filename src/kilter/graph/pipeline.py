"""The audit pipeline as an explicit graph (AD-5): Loader -> T0 -> T1 -> [T2] -> Adjudicator -> Report.

One graph serves two arms: A3 (full, `use_t2=True`) and A4 (T0+T1 only, `use_t2=False`). They differ only in
whether the T2 node runs, which is what makes the A3-vs-A4 comparison clean (blueprint 8.1).
AD-5 fallback: every node is a plain function over a state dict, so the graph can be replaced by a function
chain without touching any logic if LangGraph ever costs more than its 6-hour budget.
"""
from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from kilter import llm
from kilter.core import record as rec
from kilter.core.adjudicator import CONVICT_AT, ESCALATE_AT, adjudicate
from kilter.core.astutil import module_constants
from kilter.core.datacard import data_card
from kilter.core.findings import AuditResult, Finding
from kilter.core.tiers.t0_static import run_t0
from kilter.core.tiers.t1_runtime import run_t1
from kilter.core.tiers.t2_critic import SYSTEM as T2_SYSTEM_PROMPT
from kilter.core.tiers.t2_critic import run_t2
from kilter.eval.artifacts import ARTIFACT_SEEDS, artifact_for

ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = ROOT / "results" / "runs"


class State(TypedDict, total=False):
    path: Path
    variant_id: str
    arm: str
    use_t2: bool
    sensitivity: bool
    runs_dir: Path
    source: str
    dataset: str | None
    card: dict
    findings: list[Finding]
    checks: list[str]
    tiers: dict[str, rec.TierRun]
    result: AuditResult
    record: rec.RunRecord


def _dicts(fs: list[Finding]) -> list[dict]:
    return [f.to_dict() for f in fs]


def loader(s: State) -> State:
    source = Path(s["path"]).read_text(encoding="utf-8")
    ds = module_constants(ast.parse(source)).get("DATASET", (None, 0))[0]
    return {"source": source, "dataset": ds, "card": data_card(ds) if ds else {}, "findings": [], "checks": [], "tiers": {}}


def t0(s: State) -> State:
    t = time.perf_counter()
    f, c = run_t0(s["source"], Path(s["path"]).name)
    tr = rec.TierRun("T0", time.perf_counter() - t, c, _dicts(f))
    return {"findings": s["findings"] + f, "checks": s["checks"] + c, "tiers": {**s["tiers"], "T0": tr}}


def t1(s: State) -> State:
    t = time.perf_counter()
    f, c = run_t1(s["path"], sensitivity=s.get("sensitivity", False))
    tr = rec.TierRun("T1", time.perf_counter() - t, c, _dicts(f))
    return {"findings": s["findings"] + f, "checks": s["checks"] + c, "tiers": {**s["tiers"], "T1": tr}}


def t2(s: State) -> State:
    t = time.perf_counter()
    art = artifact_for(s["path"])  # real execution result, cached by script hash (AIMS D-013)
    out = run_t2(s["source"], art, s["card"], s["findings"], s["checks"], Path(s["path"]).name)
    tr = rec.TierRun("T2", time.perf_counter() - t, ["T2.critic"], _dicts(out.findings), [out.call])
    return {"findings": s["findings"] + out.findings, "checks": s["checks"] + ["T2.critic"], "tiers": {**s["tiers"], "T2": tr}}


def adjudicator(s: State) -> State:
    return {"result": adjudicate(str(s["path"]), s["findings"], s["checks"])}


def make_record(path: Path, dataset: str | None, arm: str, variant_id: str, tiers: dict[str, rec.TierRun],
                result: AuditResult, use_t2: bool) -> rec.RunRecord:
    """One place builds every arm's record, so provenance fields are identical across arms (AD-10)."""
    path = Path(path)
    pinned = llm.load_config()["pinned_for_reported_results"]
    calls = [c for tr in tiers.values() for c in tr.llm_calls]
    return rec.RunRecord(
        run_id=rec.new_run_id(variant_id, arm),
        arm=arm,
        variant_id=variant_id,
        input_sha256=rec.sha256_bytes(path.read_bytes() + (dataset or "").encode()),
        code_sha256=rec.code_hash(),
        created_utc=rec.now_utc(),
        seed=None,  # T0/T1 are deterministic; LLM calls run at temperature 0 (see config)
        model={"provider": pinned["provider"], "requested": pinned["model"],
               "reported": sorted({c["model_reported"] for c in calls})} if calls else {"provider": None},
        versions=rec.library_versions(),
        tiers=tiers,
        verdict=result.verdict.value,
        findings=_dicts(result.findings),
        config={"use_t2": use_t2, "convict_at": CONVICT_AT, "escalate_at": ESCALATE_AT, "temperature": 0.0,
                "thinking_level": "minimal", "artifact_seeds": ARTIFACT_SEEDS, "dataset": dataset,
                "llm_mode": llm.llm_mode(),
                "t2_prompt_sha256": rec.sha256_bytes(T2_SYSTEM_PROMPT.encode())},  # detects any edit to the frozen prompt (D-015)
    )


def report(s: State) -> State:
    r = make_record(s["path"], s["dataset"], s["arm"], s["variant_id"], s["tiers"], s["result"], s["use_t2"])
    r.save(s.get("runs_dir") or RUNS_DIR)
    return {"record": r}


def build_graph():
    g = StateGraph(State)
    for name, fn in [("loader", loader), ("t0", t0), ("t1", t1), ("t2", t2), ("adjudicator", adjudicator), ("report", report)]:
        g.add_node(name, fn)
    g.add_edge(START, "loader")
    g.add_edge("loader", "t0")
    g.add_edge("t0", "t1")
    g.add_conditional_edges("t1", lambda s: "t2" if s["use_t2"] else "adjudicator", {"t2": "t2", "adjudicator": "adjudicator"})
    g.add_edge("t2", "adjudicator")
    g.add_edge("adjudicator", "report")
    g.add_edge("report", END)
    return g.compile()


_GRAPH = None


def audit_full(
    path: str | Path,
    *,
    use_t2: bool = True,
    variant_id: str | None = None,
    sensitivity: bool = False,
    runs_dir: Path | None = None,
) -> tuple[AuditResult, rec.RunRecord]:
    global _GRAPH
    _GRAPH = _GRAPH or build_graph()
    path = Path(path)
    state = _GRAPH.invoke({
        "path": path, "variant_id": variant_id or path.stem, "arm": "A3" if use_t2 else "A4",
        "use_t2": use_t2, "sensitivity": sensitivity, "runs_dir": runs_dir,
    })
    return state["result"], state["record"]

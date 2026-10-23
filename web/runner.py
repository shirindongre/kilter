"""Run one audit through the real pipeline and return what the UI stores. Shared by server.py and build_fixtures.py.

It drives the same LangGraph the CLI uses (`kilter.graph.pipeline.build_graph`) and streams node updates so the UI
can show the tiers lighting up. It does not touch `src/kilter`.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

import adapter
from kilter.graph.pipeline import build_graph
from kilter.report import render_markdown

ORDER = ("loader", "t0", "t1", "t2", "adjudicator", "report")
STAGE_LABEL = {
    "loader": "Read the script", "t0": "T0 static checks", "t1": "T1 runtime checks",
    "t2": "T2 critic", "adjudicator": "Adjudicate", "report": "Write the run record",
}
_graph = None


def stages_for(arm: str) -> list[str]:
    return [s for s in ORDER if s != "t2" or arm == "A3"]


def run_audit(path: str | Path, arm: str, sample: dict | None = None, *, sensitivity: bool = False,
              on_stage: Callable[[str, str], None] | None = None) -> dict:
    """arm is "A3" (T0+T1+T2) or "A4" (T0+T1). Raises on pipeline errors after marking the running stage failed."""
    global _graph
    if arm not in ("A3", "A4"):
        raise ValueError(f"arm must be A3 or A4, got {arm!r}")
    _graph = _graph or build_graph()
    path = Path(path)
    stages = stages_for(arm)
    emit = on_stage or (lambda *_: None)
    current = stages[0]
    emit(current, "running")
    final: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        state0 = {"path": path, "variant_id": path.stem, "arm": arm, "use_t2": arm == "A3",
                  "sensitivity": sensitivity, "runs_dir": Path(tmp)}
        try:
            for update in _graph.stream(state0, stream_mode="updates"):
                for node, upd in update.items():
                    final.update(upd or {})
                    emit(node, "done")
                    nxt = stages.index(node) + 1
                    if nxt < len(stages):
                        current = stages[nxt]
                        emit(current, "running")
        except Exception:
            emit(current, "failed")
            raise
    result, record = final["result"], final["record"]
    source = path.read_text(encoding="utf-8")
    return {
        "view": adapter.to_view(result, record, source, sample=sample),
        "record": record.to_dict(),
        "report_md": render_markdown(result, record),
    }

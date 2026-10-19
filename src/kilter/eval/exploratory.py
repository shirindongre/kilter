"""EXPLORATORY analyses, not pre-registered arms. Kept apart from the headline tables and labelled as such.

A1 makes two calls: a first review, then a self-critique in the same conversation. The first response alone is a
critic with no tiers and no self-critique, i.e. the LLM-alone control that A2 would be (blueprint 8.1, deferred).
Because both responses are recorded, the first turn can be scored from the fixtures at no extra cost. This answers
two questions the headline arms cannot separate:
  1. How much of A3's D1-D4 detection is the critic echoing T0/T1 (which it is shown) versus finding things itself?
  2. Did A1's second turn (self-critique) remove correct findings, as REF-7 predicts?
The A1 system prompt differs from T2's only by omitting the lines about automated checks.
"""
from __future__ import annotations

import ast
from pathlib import Path

from kilter import llm
from kilter.core.adjudicator import adjudicate
from kilter.core.astutil import module_constants
from kilter.core.datacard import data_card
from kilter.core.tiers.t2_critic import CriticReport, build_prompt
from kilter.defects.variants import Variant
from kilter.eval import metrics
from kilter.eval.arms import A1_SYSTEM, _findings
from kilter.eval.artifacts import artifact_for

ROOT = Path(__file__).resolve().parents[3]


def a1_first_turn(variants: list[Variant], vdir: Path = ROOT / "results" / "variants") -> dict[str, dict]:
    """variant id -> {verdict, findings} for the first A1 response only. Replays fixtures; never calls the API."""
    out = {}
    for v in variants:
        path = vdir / f"{v.id}.py"
        source = path.read_text(encoding="utf-8")
        ds = module_constants(ast.parse(source)).get("DATASET", (None, 0))[0]
        prompt = build_prompt(source, artifact_for(path), data_card(ds), None, None)
        resp = llm.generate(prompt, system=A1_SYSTEM, response_schema=CriticReport, max_output_tokens=2048)
        report = CriticReport.model_validate_json(resp.text)
        res = adjudicate(v.id, _findings(report, path.name, ""), ["A1.turn1"])
        out[v.id] = {"verdict": res.verdict.value, "findings": [f.to_dict() for f in res.findings]}
    return out


def a1_turn1_per_class(variants: list[Variant]) -> dict:
    return metrics.per_class(variants, a1_first_turn(variants))

"""The scope prompt is a separate variant; the frozen prompt must stay byte-identical (AIMS D-015, D-022)."""
import difflib
import json
from pathlib import Path

import pytest

from kilter.core import record as rec
from kilter.core.tiers import t2_critic, t2_scope

FROZEN_SHA256 = "484e6bfe01faeb53587052d1baf95b5dedad9e599c1a7569d0c776b37d339058"
SUMMARY = Path(__file__).resolve().parents[1] / "results" / "holdout2_summary.json"


def test_frozen_prompt_unchanged():
    assert rec.sha256_bytes(t2_critic.SYSTEM.encode()) == FROZEN_SHA256


def test_scope_prompt_is_a_distinct_minimal_variant():
    assert t2_scope.SYSTEM_SCOPE != t2_critic.SYSTEM
    assert t2_scope.PROMPT_SHA256 == rec.sha256_bytes(t2_scope.SYSTEM_SCOPE.encode())
    changed = [l for l in difflib.unified_diff(t2_critic.SYSTEM.splitlines(), t2_scope.SYSTEM_SCOPE.splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    # Exactly three edits: the D5 definition and the hedged-conclusion rule are rewritten, one scope rule is added.
    assert sum(l.startswith("-") for l in changed) == 2 and sum(l.startswith("+") for l in changed) == 3


def test_holdout2_results_recorded_with_both_prompts():
    if not SUMMARY.exists():
        pytest.skip("holdout2 not run")
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert s["prompt_sha256"] == {"frozen": FROZEN_SHA256, "scope": t2_scope.PROMPT_SHA256}
    for p in ("frozen", "scope"):
        assert s["arms"][p]["detect_B5"]["n"] == 8 and s["arms"][p]["fp_HC2"]["n"] == 8
    # Rule 3 of the brief: a prompt that raises false positives on the honest set is a failure.
    assert s["arms"]["scope"]["fp_HC2"]["k"] <= s["arms"]["frozen"]["fp_HC2"]["k"]

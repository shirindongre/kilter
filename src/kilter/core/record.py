"""Run records (AD-10): everything needed to reproduce and to cost an audit.

`record_sha256` is a content digest over the canonical JSON of the record: it makes edits detectable, but it is
not an authenticated signature (no key management in Phase 1; stated in the README Limitations).
T0/T1 outputs reproduce bit-identically, so `tiers_sha256` over them must match across reruns of the same input.
"""
from __future__ import annotations

import hashlib
import json
import platform
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

SCHEMA_VERSION = 1
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TRACKED_LIBS = ("numpy", "scikit-learn", "rdkit", "scikit-fingerprints", "xgboost", "langgraph", "google-genai")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# Modules that only READ run records to build tables and figures. They cannot change an audit, so editing a plot
# must not invalidate every record's provenance.
ANALYSIS_ONLY = frozenset({"eval/metrics.py", "eval/summarize.py", "eval/figures.py", "eval/exploratory.py"})


def code_hash() -> str:
    """Hash of the verifier: every .py file in the kilter package except analysis-only modules."""
    h = hashlib.sha256()
    for f in sorted(PACKAGE_ROOT.rglob("*.py")):
        if f.relative_to(PACKAGE_ROOT).as_posix() in ANALYSIS_ONLY:
            continue
        h.update(f.relative_to(PACKAGE_ROOT).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def library_versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for lib in TRACKED_LIBS:
        try:
            out[lib] = version(lib)
        except PackageNotFoundError:
            out[lib] = "not installed"
    return out


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class TierRun:
    tier: str
    seconds: float = 0.0
    checks: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    llm_calls: list[dict] = field(default_factory=list)   # one dict per LLM call (T2 and the A1 baseline)


@dataclass
class RunRecord:
    run_id: str
    arm: str
    variant_id: str
    input_sha256: str
    code_sha256: str
    created_utc: str
    seed: int | None
    model: dict
    versions: dict
    tiers: dict[str, TierRun]
    verdict: str
    findings: list[dict]
    config: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    record_sha256: str = ""

    # --- derived accounting (AD-3) -------------------------------------------------
    def tokens(self) -> dict[str, int]:
        calls = [c for t in self.tiers.values() for c in t.llm_calls]
        return {
            "calls": len(calls),
            "cached_calls": sum(bool(c.get("cached")) for c in calls),
            "input": sum(c["input_tokens"] for c in calls),
            "output": sum(c["output_tokens"] for c in calls),
            "thinking": sum(c["thinking_tokens"] for c in calls),
            "output_billed": sum(c["output_tokens"] + c["thinking_tokens"] for c in calls),
        }

    def seconds_total(self) -> float:
        return round(sum(t.seconds for t in self.tiers.values()), 3)

    def tiers_sha256(self, tiers: tuple[str, ...] = ("T0", "T1")) -> str:
        """Digest of the deterministic tiers' checks and findings only (no timings)."""
        body = {t: {"checks": self.tiers[t].checks, "findings": self.tiers[t].findings} for t in tiers if t in self.tiers}
        return sha256_bytes(canonical(body).encode())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tokens"], d["seconds_total"] = self.tokens(), self.seconds_total()
        d.pop("record_sha256")
        d["record_sha256"] = sha256_bytes(canonical({k: v for k, v in d.items()}).encode())
        return d

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        return path


def verify(record: dict) -> bool:
    """True if the record's content digest matches its body (detects edits, does not authenticate the author)."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    return sha256_bytes(canonical(body).encode()) == record.get("record_sha256")


def new_run_id(variant_id: str, arm: str) -> str:
    return f"{variant_id}__{arm}__{uuid.uuid4().hex[:8]}"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

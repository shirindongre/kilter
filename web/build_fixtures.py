"""Build the static, offline data for the UI: the three demo scripts, both arms, replayed from recorded critic calls.

    python web/build_fixtures.py

Writes web/static/data/index.json and web/static/data/runs/<run_id>.json. With these files the UI works without the
server (any static file host), which is also what gets embedded in a recording or a screenshot. The records are real
pipeline output; this script contains no results of its own. Needs the BACE and BBBP datasets cached once.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["KILTER_LLM_MODE"] = "replay"   # never call an API from the fixture builder
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fleet  # noqa: E402
import registry  # noqa: E402
import runner  # noqa: E402

DATA = HERE / "static" / "data"


def main() -> None:
    shutil.rmtree(DATA / "runs", ignore_errors=True)
    (DATA / "runs").mkdir(parents=True)
    samples, runs = [], []
    for s in registry.demo_samples():
        entry = registry.public(s) | {"runs": {}}
        for arm in ("A4", "A3"):
            print(f"{s['id']:22s} {arm} ...", end=" ", flush=True)
            saved = runner.run_audit(s["path"], arm, registry.public(s))
            v = saved["view"]
            (DATA / "runs" / f"{v['run_id']}.json").write_text(json.dumps(saved, default=str), encoding="utf-8")
            summary = {"run_id": v["run_id"], "sample_id": s["id"], "label": s["label"], "script": v["subject"]["path"],
                       "arm": arm, "verdict": v["verdict"], "held_at": v["held_at"], "surveyed_at": v["surveyed_at"],
                       "outcome": v["sample"]["truth"]["outcome"], "planted_class": s["planted_class"]}
            entry["runs"][arm] = summary
            runs.append(summary)
            print(v["verdict_word"], flush=True)
        samples.append(entry)
    index = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "samples": samples, "runs": runs}
    (DATA / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"wrote {len(runs)} runs to {DATA}")
    stored = fleet.load()   # the fleet screen's numbers; its run pages need the server, so only the summary is saved
    if stored:
        (DATA / "fleet.json").write_text(json.dumps(stored.payload), encoding="utf-8")
        print(f"wrote fleet.json ({len(stored.payload['variants'])} variants)")
    else:
        (DATA / "fleet.json").unlink(missing_ok=True)
        print("no results/ found: the offline copy has no fleet screen data")


if __name__ == "__main__":
    main()

# Kilter web UI

A local interface for the verifier. It audits a script, shows how deep the mark had to sink before something held it, and lets you browse the 83 scripts Kilter has ground truth for. It never decides a verdict: it runs the same pipeline as the CLI and re-shapes the run record for display (AIMS D-024).

## Run it

From the repo root, in the activated venv (cmd on Windows):

    pip install -e ".[web]"
    python web\server.py

It opens http://127.0.0.1:8765/. Options: `--port 8765`, `--no-browser`, `--live`.

- **Replay (default).** Critic answers come from the recordings in `fixtures/llm`. Nothing calls an API. A script of your own can only be audited with the deterministic arm (T0 + T1), because no critic answer was recorded for it.
- **`--live`.** A missing critic answer is fetched from the model (needs `GOOGLE_API_KEY`) and recorded. Existing recordings are never overwritten.
- The datasets (BACE, BBBP) must be cached once: `python -c "from kilter.data import load_dataset as l; l('bace'); l('bbbp')"`.

## Offline copy (no server)

    python web\build_fixtures.py

Runs the three demos through both arms from recordings and writes `web/static/data/`. After that, `web/static` can be opened from any static file host (for example `python -m http.server` inside `web/static`) and shows those six saved runs. Commit `web/static/data/` if you want the recording or the screenshots to be reproducible without the datasets.

## Screens

| Route | What it does |
|---|---|
| `#/` Audit | Pick a demo, upload a `.py`, or paste a script; choose the deterministic arm or the full arm; optionally measure split sensitivity (slow). |
| `#/run/<id>` | The verdict: mark scale, what was found with the code line, what could not be checked, the check register, cost, provenance and the digest check. |
| `#/samples` | The 3 demos and 80 evaluation variants with their planted defect and the outcome of any run (caught, missed, false alarm). "Audit all shown" runs the deterministic arm over the list. |
| `#/fleet` | Every evaluated script (main 48, holdout 16, holdout 2 16), both arms, outcome against the planted class, confusion per set, and a check that every count agrees with the evaluation's own summary files. Reads `results/`; re-runs nothing (D-025). |
| `#/history` | Every saved run in `web/runs/`. |

## How the verdict is drawn

The mark's depth is the shallowest tier with a sound conviction: T0 and T1 are sound, T2 (the critic) is not. A mark held only by the critic is labelled a query. A mark that could not be set because a tier could not run (for example a script without the Kilter hooks) is ESCALATE. A defect found by an earlier tier outranks a later tier that could not run, so a hook-less script with a real static finding is OUT OF KILTER and also lists what T1 could not check.

## What is derived, and where

`adapter.py` builds the view from the run record. Nothing below is new analysis:

- `held_at`, `mark`, `unresolved_tier`: from finding tiers and the unresolved check ids.
- Code excerpt: seven lines around the finding's line, from the audited bytes.
- Witnesses: findings of the same class at the same site are grouped, the same grouping as the terminal report.
- Sensitivity table: parsed from the fixed-format T1 evidence string.
- Ground truth (sample browser): planted class and line compared with the verdict.
- Authored text (check names and assertions, remedies, blocker titles, what a pass does not mean): `catalog.py`, written by hand.

Tests: `pytest tests/test_web_adapter.py`. They push hand-built findings through the real adjudicator and assert the adapter does not change a verdict.

## Security

The server is for one person on one machine.

- Binds 127.0.0.1 only; rejects other Host headers (DNS rebinding) and `Sec-Fetch-Site: cross-site`.
- Every API call needs a per-process token, delivered by `/api/session` and sent as `X-Kilter-Token`.
- Strict CSP; every string from the audited script or the backend is rendered with `textContent`.
- **Tier 1 executes the script it audits, with no sandbox.** Audit only scripts you would run yourself.

## Differences from the spec

See D-024 in `AIMS/decisions.md`: 6 real checks instead of 20 register rows, 83 samples instead of 40, a slightly shifted mark line, no 1280 px minimum width, and an empty `[USD]` slot because no list price is configured.

## The fleet screen and `results/`

`results/` is mostly gitignored, so on a fresh clone the screen says there are no results. It needs, at the repository root: `runs/` (the run records), `variants/` (the exact bytes that were audited), `holdout2/` and `_scratch_runs/` (holdout 2's rows and its T0+T1 records), and `summary.json` / `holdout2_summary.json` for the reconciliation. A tile opens the run screen on a view rebuilt from the stored record; the script shown is checked against the record's input hash. Holdout 2's A3 and Scope columns are critic-prompt rows, not run records, so they have no run page. The offline copy (`build_fixtures.py`) saves the fleet numbers to `data/fleet.json` but its tiles are not links.

If the page lists a code-hash or Python-version difference, that is real: see D-025 and L-012.

## Not done

`--live` mode and the split-sensitivity option have not been exercised on real runs. No Linux checkout has been tried (the demo artifacts are keyed to CRLF bytes).

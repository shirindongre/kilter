# CLAUDE.md — Kilter

Kilter is a reproducibility-gated audit tool for bioinformatics/cheminformatics analysis scripts.
It answers **IN KILTER / OUT OF KILTER / ESCALATE** and shows which tier of checking caught what.

**Source of truth:** [docs/blueprint.md](docs/blueprint.md) (v1.2). Read the section you are implementing before writing code.
**Owner:** Shashwat Kumar. **Audience for Phase 1:** an interviewer. It must read as a finished tool.

## Session protocol (do this every session)

1. Read `AIMS/README.md`, then `AIMS/context.md` (current state), `AIMS/decisions.md`, `AIMS/mistakes.md`.
2. Open `tracker/data.js` to see what is in progress. Work on the in-progress item, or the next one in phase order.
3. While working: log decisions to `AIMS/decisions.md`, errors to `AIMS/mistakes.md`, discoveries to `AIMS/learnings.md`, unanswered questions to `AIMS/open-questions.md`.
4. Before ending: update `tracker/data.js` statuses, rewrite `AIMS/context.md`, append to `AIMS/session-log.md`.

## Non-negotiable rules (from the blueprint)

- **Gates are gates.** Do not start the next phase/day until the current gate passes (§5.3, §5.6). Day 1 gate: T0+T1 catch >= 80% of injected D1–D4 with 0 false positives on the 8 clean variants, with **no LLM called**.
- **Scope is Phase 1 only** (§5.1–5.2): molecular property prediction, BACE + BBBP, ECFP + RF/XGBoost, defects D1–D5, 40 variants, arms A0/A1/A3/A4. No scRNA-seq, no generation mode, no web UI, no Docker/CI. If tempted, re-read AD-8 and §10.
- **Audit mode only** (AD-8). Kilter audits an existing script; it does not write analyses.
- **Tiers:** T0 static AST (sound) -> T1 runtime assertions (sound) -> T2 LLM critic (unsound, last). (AD-1)
- **T2 critic input is restricted** to executed artifact + data card + T0/T1 output. Never the analyst's prompt/reasoning. (AD-2)
- **Token-matched baselines, always.** Log input/output tokens, wall-clock, USD-equivalent per run. (AD-3)
- **Never claim a single correct split/method.** Report what was used, whether stated, and sensitivity to the alternative. (AD-9)
- **Determinism + provenance:** every run emits a run record (input hash, code hash, model string, seed, lib versions, tier outputs, tokens, time). (AD-10)
- **Never demo against a live API.** `kilter demo` uses recorded fixtures: offline, deterministic. (§5.7)
- **Never edit an AD silently.** Append a revision line (blueprint §0 rule 1). Claims need a `[REF-n]` or an explicit `[assumption]`/`[my judgment]`.
- **Single-seed chemistry results are invalid** (§8.3, REF-18). Use multiple seeds for any reported number.
- **Free-tier limits:** record the limits actually shown in each provider console, with date, in `config/providers.yaml`. Never use limits from a blog post.
- API keys go in environment variables / `.env` (gitignored). Never write keys into code, config, logs, or AIMS.

## Layout

```
src/kilter/            package (core/, graph/, defects/, eval/, cli.py)
config/providers.yaml  model strings + verified quotas + date
references/            clean verified analyses (inputs to the injector)
results/               run records, figures, tables
tests/                 pytest
docs/blueprint.md      source of truth
AIMS/                  AI Memory System (persistent project memory)
tracker/index.html     visual project tracker; data lives in tracker/data.js
```

Deviation from blueprint §9 (package nested under `src/kilter/`): see `AIMS/decisions.md` D-001.

## Commands (Windows / PowerShell)

```
.venv\Scripts\Activate.ps1          # activate env
pip install -e ".[dev]"             # install
pytest                              # tests
kilter audit path\to\analysis.py --data bace
kilter demo                         # cached offline demo (stand-in for `make demo`, see D-002)
start tracker\index.html            # open tracker
```

## Conventions

- Python 3.11, type hints, `from __future__ import annotations`, small modules, no dead code.
- Findings are a typed dataclass (class, site `file:line`, evidence, tier, confidence). Changing it late is expensive; keep it stable.
- Tests are the gate: if a behaviour matters, a pytest asserts it.
- Comments explain *why* (cite AD/REF), not *what*.
- Keep the tracker honest: a task is `done` only when its test/gate actually passes.

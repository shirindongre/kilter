# Mistakes log

Record every error: what happened, root cause, and the rule that prevents it recurring. Append immediately.

Format:

```
## M-001 — Short title (YYYY-MM-DD)
What happened: ...
Root cause: ...
Prevention rule: ...
```

## M-001 — Assumed `skfp.__version__` exists (2026-10-17)
What happened: `scripts/record_reference_metrics.py` crashed with AttributeError when building the run-record header. It was launched as a long background job without a smoke run, so the failure surfaced only via the task-completion notification.
Root cause: used a module attribute without verifying it; not every library exposes `__version__`.
Prevention rule: read versions with `importlib.metadata.version(<dist-name>)`. Smoke-run any new script with a tiny config (e.g. 1 seed) in the foreground before launching a long background job.

## M-002 — Escape sequences corrupted by writing code through a shell/Python heredoc (2026-10-17)
What happened: twice (tests/test_t0.py, src/kilter/cli.py) a `\n` inside a string literal was expanded to a real newline while patching files via `python - <<EOF`, producing SyntaxErrors. A third attempt, a large `cat > file <<'EOF'` batch, failed on quoting and wrote nothing.
Root cause: code-bearing text passed through two layers of escaping (shell, then Python string).
Prevention rule: write or edit source files with the Write/Edit tools, never via heredoc-generated Python. Use heredocs only for plain text appends (AIMS notes).

## M-003 — Almost leaked the answers into the critic prompt (2026-10-18)
What happened: the first draft of the T2 system prompt defined D5 by listing overclaim kinds that mirrored the 8 hand-authored variants one-to-one.
Caught by: re-reading the prompt against the authored variants before the first T2 call (D-015). Fixed before any call was made; no results were affected.
Prevention rule: write every prompt from the class definitions alone, then diff it against the authored test cases for shared vocabulary before the first run. Freeze it before evaluating.

## M-004 — Verifier code edited between arms (2026-10-18)
What happened: A4 was run, then llm.py was edited (throttle, 5xx retry), then A3 was run, so the two arms carried different code_sha256 values. The run records exposed it (2 distinct hashes).
Impact: none on results (the edits touched only the LLM client, T0/T1 outputs were identical across arms 48/48), but it would have broken the "same verifier" claim.
Prevention rule: after any change under src/kilter, rerun every arm that will be compared; check that all records in a comparison share one code_sha256 (done: 96 records, 1 hash).

## M-002 recurrence (2026-10-18)
Wrote `\n` inside a string through `python - <<'PYEOF'` again while editing arms.py, despite the rule above. Fixed with the Edit tool. Reinforced rule: any edit that contains a backslash escape goes through Edit/Write, no exceptions; heredoc-python is only for pure-text appends and replacements without escapes.

## M-002 third occurrence (2026-10-18)
Same escaping failure in summarize.py (heredoc-python containing `\n`). It failed at import, before any compute, so it cost a few minutes, not a run. This is now the third time: the rule is absolute. Never use `python - <<EOF` to edit code. Use the Edit/Write tools for every source edit. Heredocs are for plain-text appends to AIMS notes only.

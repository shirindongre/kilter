# AIMS — AI Memory System

Persistent project memory for Kilter, so any session (or any agent) can resume with full context.
Plain markdown, human-readable, append-mostly.

| File | Purpose | Update rule |
|---|---|---|
| `context.md` | Current state snapshot: where we are, what's next, blockers | **Rewrite** at end of every session |
| `decisions.md` | Implementation decisions (D-nnn) with why + what would change it | Append; supersede, never silently edit |
| `mistakes.md` | Errors made, root cause, prevention rule (M-nnn) | Append immediately when found |
| `learnings.md` | Non-obvious facts about the stack, data, environment (L-nnn) | Append |
| `open-questions.md` | Unresolved questions for the owner (Q-nnn) | Append; mark answered with date + answer |
| `session-log.md` | Chronological log of sessions | Append at end of session |

Relationship to the blueprint: **architectural** decisions (AD-n) live in `docs/blueprint.md` §3.
`decisions.md` holds **implementation** decisions made while building (tooling, layout, library choices)
and any proposed revisions to an AD (which must also be appended to the blueprint revision log).

Entry format:

```
## D-001 — Title (YYYY-MM-DD)
Decision: ...
Why: ...
Revisit if: ...
Status: active | superseded by D-0xx
```

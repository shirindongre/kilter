## main set (48 variants)

| arm | D1 | D2 | D3 | D4 | D5 | false positives | all defects |
|---|---|---|---|---|---|---|---|
| A0 | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 0/40 (0-9%) |
| A1 | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 1/8 (0-53%) | 2/8 (3-65%) | 0/8 (0-37%) | 3/40 (2-20%) |
| A3 | 8/8 (63-100%) | 8/8 (63-100%) | 8/8 (63-100%) | 8/8 (63-100%) | 8/8 (63-100%) | 0/8 (0-37%) | 40/40 (91-100%) |
| A4 | 8/8 (63-100%) | 8/8 (63-100%) | 8/8 (63-100%) | 8/8 (63-100%) | 0/8 (0-37%) | 0/8 (0-37%) | 32/40 (64-91%) |

| arm | LLM calls / audit | input tokens / audit | output tokens / audit (billed) | seconds / audit |
|---|---|---|---|---|
| A0 | 0.0 | 0 | 0 | 0.0 |
| A1 | 2.0 | 5,573 | 270 | 10.2 |
| A3 | 1.0 | 2,914 | 176 | 8.1 |
| A4 | 0.0 | 0 | 0 | 6.5 |

Exploratory (not a pre-registered arm): did the self-critique turn help?

| | D1 | D2 | D3 | D4 | D5 | false positives |
|---|---|---|---|---|---|---|
| critic alone, first pass (no tiers, no self-critique) | 5/8 (24-91%) | 0/8 (0-37%) | 4/8 (16-84%) | 5/8 (24-91%) | 7/8 (47-100%) | 0/8 (0-37%) |
| A1 = same critic after a self-critique turn | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) | 1/8 (0-53%) | 2/8 (3-65%) | 0/8 (0-37%) |

## holdout set (16 variants)

| arm | D5 | false positives | all defects |
|---|---|---|---|
| A0 | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) |
| A1 | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) |
| A3 | 3/8 (9-76%) | 0/8 (0-37%) | 3/8 (9-76%) |
| A4 | 0/8 (0-37%) | 0/8 (0-37%) | 0/8 (0-37%) |

| arm | LLM calls / audit | input tokens / audit | output tokens / audit (billed) | seconds / audit |
|---|---|---|---|---|
| A0 | 0.0 | 0 | 0 | 0.0 |
| A1 | 2.0 | 5,538 | 175 | 4.0 |
| A3 | 1.0 | 2,855 | 90 | 8.5 |
| A4 | 0.0 | 0 | 0 | 6.9 |

Exploratory (not a pre-registered arm): did the self-critique turn help?

| | D5 | false positives |
|---|---|---|
| critic alone, first pass (no tiers, no self-critique) | 2/8 (3-65%) | 0/8 (0-37%) |
| A1 = same critic after a self-critique turn | 0/8 (0-37%) | 0/8 (0-37%) |

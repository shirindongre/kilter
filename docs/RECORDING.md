# The 90 second fallback recording, and the rehearsal

Blueprint 5.6 wants a recording that exists before you present, so a dead laptop, a dead network or a dead terminal does not end the demo. `kilter demo` is already offline and byte-identical across runs (`tests/test_demo.py`), so the recording is a screen capture of it with your voice over it. Nothing here needs an API key.

## Before you record (cmd, from the repo root)

```
cd /d "D:\Shirin\Uni\Sem 5\FAAI\kilter"
.venv\Scripts\activate.bat
set HF_HUB_OFFLINE=1
set GOOGLE_API_KEY=
kilter demo > nul
echo %errorlevel%
```

`0` means the datasets are cached and the demo runs offline. If it prints `demo fixture missing` or `datasets must be cached`, run the one-time download first: `python -c "from kilter.data import load_dataset as l; l('bace'); l('bbbp')"`.

Window: Windows Terminal or the classic console, **100 columns or wider** (the verdict boxes are 100 characters), font 18 pt or larger, dark background, nothing else on screen. Turn off notifications. Record with Win+G (Xbox Game Bar) or OBS at 1080p. The demo prints about 60 lines; at 18 pt the window shows about 30, so you will scroll once per screen.

## The take (90 s)

Run `cls`, start recording, then type `kilter demo` live (it makes the offline claim visible) and press Enter. It prints all three screens at once. Scroll to each in turn.

| Time | On screen | Say (152 words: about 60 s at speaking pace, the rest is typing and scrolling) |
|---|---|---|
| 0:00-0:10 | the command, then the title line | "Kilter audits a modelling script and answers in kilter, out of kilter, or escalate. This is `kilter demo`. It is offline: the model answers are replayed from recorded calls." |
| 0:10-0:30 | Screen 1, IN KILTER | "A clean BACE analysis. It passes, and it lists every check that ran, so a pass is never silent: leakage, split protocol, multiple comparisons, duplicates, scaffold overlap, and the critic." |
| 0:30-1:00 | Screen 2, OUT OF KILTER, D1 | "Now a BBBP script where a preprocessing step is fitted on every row before the split. Out of kilter. It names the class, the line, 2_leakage_bbbp.py line 61, the evidence, and which tier caught it: static analysis, a sound check, confirmed by the critic." |
| 1:00-1:25 | Screen 3, OUT OF KILTER, D5 | "Last, a script whose numbers are fine and whose conclusion is not. No sound check can see that, so only the critic flags it, and Kilter labels it a query, not a proven defect." |
| 1:25-1:30 | the three verdicts on screen | "Sound checks first, a model only where none exists, and it says which one spoke." |

Do not read the numbers from the results table on this recording; it shows the tool working, not the evaluation. If you want a claim on screen, use only `40 of 40` / `32 of 40` from `results/results_table.md`, and say the intervals.

## After recording

1. Export to MP4. Name it `kilter-demo-90s.mp4`. **Do not commit it** (binary, several MB); keep it outside the repo or attach it to a release.
2. Put one copy on the laptop and one on the phone. On the phone, open it once with the radio off to prove it plays offline, and check the text is legible at arm's length.
3. Watch it once at 1x. It must be 90 s or under, and the verdict words must be readable in the first frame of each screen.

## Rehearsal (docs/TALK.md, out loud, timed)

Nothing below has been done; it needs you and a clock.

What the script's own word count says, so you know what to expect (estimate, not a measurement): the five beats contain about 257 words of speech, which is roughly 1 min 45 s at 150 words a minute. The other three minutes are the demo running and the pauses. The 4:50 in the table is the slot each beat gets, not how long each beat takes to say. The thinnest beats are the thesis (32 words in a 45 s slot) and the demo (63 words in 105 s). Expect your first timed run to finish well under 4:50, and decide on purpose whether to fill the gap (the first two sentences of Q1 are the natural addition) or leave a minute for questions.

Run order:

1. Read it aloud once with a phone stopwatch, no demo. Write down the time per beat.
2. Run it with the live `kilter demo` between 1:15 and 3:00. If it misbehaves, play `kilter-demo-90s.mp4` instead and keep talking; do this switch once on purpose so it is not new on the day.
3. Answer the six questions aloud, 30 s each. Say the limits before they ask.
4. Fix only what broke. Do not add claims. Every number in TALK.md was checked against `results/` on 2026-10-23 (AIMS D-025).

## Q-001, the presentation format

Open until you answer it. It changes one thing: a screen-share needs the 90 s recording and a test of the call software with `kilter demo` already run once (so the terminal shows the command history), an in-person laptop needs the phone copy. Tell the next session which one it is and Q-001 closes.

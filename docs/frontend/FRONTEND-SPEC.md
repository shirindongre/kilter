# Kilter Frontend Specification — "Draft Mark"

**Direction:** Draft Mark (ship classification / painted load-line marks)
**Scope:** desktop web app, 1440 px design width. No mobile, no tablet.
**Owner:** Shashwat Kumar
**Status:** locked for implementation 2026-10-18
**Source of truth for product behaviour:** `blueprint.md`. This document governs the interface only. Where the two disagree about behaviour, the blueprint wins; where they disagree about presentation, this document wins.

---

## 0. The one idea

**Depth equals unsoundness.** An analysis descends through the tier stack until a check holds it. A mark high on the hull means a sound, deterministic check caught the defect. A mark low on the hull means only the LLM critic objected. No mark at all means it came through clean; a mark that cannot be set means escalate.

Everything in this interface exists to make that one reading instant. If a design decision does not serve it, cut the decision.

### Non-goals

- Do not imply the system writes analyses. It audits them.
- Do not render a verdict the backend did not emit. The UI never derives a verdict from checks.
- Do not display an unmeasured number as a value. See §7.
- No dark/light theme switch. One palette, dark, by design: the hull is the subject.

---

## 1. Color tokens

```css
:root {
  /* ground */
  --hull:        #16302C;  /* page ground */
  --boot:        #0E201D;  /* recessed panel, plate interior */
  --rule:        #2A4A44;  /* section divider */
  --rule-faint:  #22413C;  /* table row divider */
  --scribe:      #35564F;  /* tier mark line on the plate */

  /* ink */
  --chalk:       #EDEAE2;  /* primary text, painted numerals     11.4:1 */
  --chalk-2:     #CFDEDA;  /* body copy                           9.9:1 */
  --chalk-3:     #B9CDC8;  /* secondary body                      8.3:1 */
  --mute:        #9DB5AF;  /* labels, metadata                    6.3:1 */
  --mute-2:      #8EA8A2;  /* smallest metadata, em-dash slots    5.5:1 */
  --mute-3:      #7F9D97;  /* dimmed tier numerals, UI borders    4.8:1 */

  /* signal */
  --sea:         #3E6F73;  /* water fill (non-text) */
  --pass:        #7FBAB2;  /* in kilter                           6.3:1 */
  --mark:        #E8B33C;  /* out of kilter, primary action       7.1:1 */
  --mark-hi:     #F5C860;  /* hover on mark */
  --ember:       #E07A4E;  /* escalate, incomplete                4.6:1 */
  --rust:        #A8431F;  /* defect fill behind chalk — NEVER text on hull */
}
```

**Hard rules.**

1. `--rust` has a 2.3:1 ratio on `--hull`. It is a **fill only**: a badge background with `--chalk` on it (5.0:1), or an inset 3–4 px edge. Never set text in it on the hull ground. Use `--ember` when escalate needs to be a text colour.
2. Tier identity is carried by **lightness, not hue**: T0 `--chalk`, T1 `--mark`, T2 `--mute-3`. Salience falls as soundness falls. This is load-bearing — do not reassign.
3. Verdict colours: in kilter `--pass`, out of kilter `--mark`, escalate `--chalk` headline with an `--ember` rule beneath it. Escalate is deliberately *not* coloured like a failure.
4. `--rule`, `--rule-faint` and `--scribe` are decorative separators and exempt from text contrast; they must not be the only cue for anything.

---

## 2. Typography

| Role | Family | Weight | Size / line-height | Tracking |
|---|---|---|---|---|
| Painted mark (verdict) | Archivo | 900 | 56 / 1.0 | −0.01em |
| Page title | Archivo | 900 | 44 / 1.08 | −0.03em |
| Section title | Archivo | 900 | 24 / 1.2 | −0.02em |
| Panel title | Archivo | 900 | 19 / 1.25 | −0.015em |
| Finding title | Archivo | 700 | 20 / 1.3 | −0.01em |
| Lead paragraph | Archivo | 400 | 17 / 1.6 | — |
| Body | Archivo | 400 | 16 / 1.65 | — |
| Dense body / table | Archivo | 400 | 15 / 1.5 | — |
| Label | Archivo | 600 | 13.5 / 1.4 | — |
| Big figure | Archivo | 900 | 34–56 / 1.0 | −0.03em |
| Code, hashes, IDs | JetBrains Mono | 400–500 | 12–13 / 1.9 | — |

Load both from Google Fonts. **Never** Inter, Roboto or Arial.

**Rules.** Measure caps at 66ch for body, 28ch for display. Sentence case everywhere — caps are reserved for the painted verdict words and the `T0 / T1 / T2 / ESC` plate numerals, which are objects, not labels. No all-caps eyebrow labels above headings. `font-variant-numeric: tabular-nums` on every figure that sits in a column or changes. Painted type gets `text-shadow: 0 1px 0 rgba(0,0,0,.4)` at ≤32 px and `0 2px 0 rgba(0,0,0,.45)` above.

---

## 3. Layout and spacing

- 8 px base. Permitted steps: 4, 8, 12, 14, 18, 22, 26, 32, 36, 48, 56, 64, 72.
- Page gutter 48 px. Content max-width 1344 px.
- Header bar 64 px, `--boot`-adjacent, bottom `1px solid var(--rule)` plus `inset 0 1px 0 rgba(237,234,226,.05)`.
- Two-column hero: mark scale `flex: 0 1 460px` (min 340), content `flex: 1 1 520px; min-width: 0`.
- Sections separated by `border-top: 1px solid var(--rule)` + 48 px top padding. No card grids. Grouping comes from rules and the inset-edge panel (§4), never from a row of equal rounded boxes.
- Border radius: **0 everywhere.** The only curves in the system are the plate hatch and nothing else.

---

## 4. Material (the anti-flat rules)

Depth comes from edge light and recession, never from gradient washes or drop-shadowed cards.

```css
/* recessed panel */
.panel { background: var(--boot);
  box-shadow: inset 0 1px 0 rgba(237,234,226,.06), 0 1px 6px rgba(0,0,0,.4); }

/* recessed panel carrying a status edge */
.panel--flag  { box-shadow: inset 4px 0 0 var(--rust),  inset 0 1px 0 rgba(237,234,226,.06), 0 1px 6px rgba(0,0,0,.4); }
.panel--top   { box-shadow: inset 0 3px 0 var(--mark),  inset 0 4px 0 rgba(237,234,226,.06), 0 1px 5px rgba(0,0,0,.4); }

/* hull plate */
.plate { background: var(--boot);
  box-shadow: inset 0 0 0 1px rgba(237,234,226,.07),
              inset 5px 0 14px rgba(0,0,0,.55),
              inset -3px 0 10px rgba(0,0,0,.4); }

/* water */
.water { background: var(--sea); transform-origin: top;
  box-shadow: inset 0 2px 0 rgba(237,234,226,.18),      /* surface specular */
              inset 0 -6px 14px rgba(14,32,29,.5); }

/* the mark */
.mark { height: 5px; background: var(--mark);
  box-shadow: 0 -1px 0 rgba(255,255,255,.4), 0 3px 8px rgba(0,0,0,.55); }

/* primary action */
.btn { background: var(--mark); color: var(--hull);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 2px 5px rgba(0,0,0,.4); }
```

Forbidden: `linear-gradient` as decoration; uniform soft shadow under repeated blocks; any blur radius over 14 px. A hard two-stop gradient used as a *data encoding* (a glyph split between two tiers) is allowed; a gradient used as atmosphere is not.

---

## 5. Motion

Tokens from IBM Carbon; application rules from Atlassian.

```css
:root {
  --prod:  cubic-bezier(0.2, 0, 0.38, 0.9);  /* answers a pointer */
  --enter: cubic-bezier(0, 0, 0.3, 1);       /* entrances, the mark */
  --exit:  cubic-bezier(0.4, 0.14, 1, 1);
  --t-press: 70ms;  --t-hover: 110ms;  --t-small: 150ms;
  --t-move: 240ms;  --t-plate: 400ms;  --t-settle: 760ms;
}
```

**Rules, in priority order.**

1. **Transform and opacity only.** Never animate height, width, top or left. The water fills on `scaleY` with `transform-origin: top`; the mark travels on `translateY`.
2. **One or two properties per transition.**
3. **One non-user-triggered moment per screen.** Everything else responds to a pointer, a key or a click.
4. **Exits are 50–100 ms shorter than entrances.**
5. **Stagger is 6 ms for a field of forty glyphs, 40 ms for a list of twenty rows.** Total sequence never exceeds 1.3 s.
6. **Reduced motion reduces, it does not remove.** Collapse every animation and transition to 1 ms so the end state still arrives, and force hover-revealed content permanently visible.

```css
@media (prefers-reduced-motion: reduce) {
  .k-plate, .k-flood, .k-settle, .k-rise, .k-fade, .k-bar, .k-unset, .k-stamp {
    animation-duration: 1ms !important; animation-delay: 0ms !important;
  }
  .k-glide, .k-mark, .k-row, .k-assert, .k-seg, .k-btn, .k-block { transition-duration: 1ms !important; }
  .k-assert, .k-cmd { opacity: 1 !important; }
}
```

### The orchestrated moment, per screen

| Screen | Moment | Spec |
|---|---|---|
| Out of kilter | The mark settles | plate `scaleY` 400 ms → water `scaleY` 700 ms @200 ms → mark `translateY` from −138 px with an 8 px overshoot at 84%, 760 ms @300 ms |
| In kilter | The register stamps in | 20 rows, `opacity` 110 ms, 40 ms apart; mark line fades at the top of the hull, never descends |
| Escalate | The mark fails to hold | `translateY` to the T1 line by 38%, holds to 54%, slides to rest 50 px lower, dashed, 1100 ms @200 ms; hatch zone fades in at 1320 ms |
| Fleet | — (user-triggered only) | 40 marks glide 240 ms on `translateY`+`opacity`, 6 ms stagger by index |

### Micro-interactions

| Target | Property | Duration |
|---|---|---|
| Button press | `transform: scale(.985)` | 70 ms |
| Button hover | `background-color` / `border-color` | 110 ms |
| Table row hover | `background-color` to `rgba(62,111,115,.14)` | 70 ms |
| Assertion reveal on row hover | `opacity` 0→1 | 110 ms |
| Finding panel hover | `box-shadow` inset edge thickens | 150 ms |
| Segmented control select | `background-color`, `color`, `border-color` | 110 ms |
| Mark glide on state change | `transform` | 240 ms |
| Tier numeral brighten on band hover | `color` | 110 ms |

---

## 6. Components

### 6.1 Mark scale

The signature component. Fixed 620 px tall in the hero, 300–340 px in compact use.

- Plate: 148 px wide, `left: 92px`, `.plate` material.
- Mark depths at 620 px: **T0 150, T1 262, T2 404, ESC 546.** Compact 300 px: 72 / 132 / 192 / 262. Derive others proportionally.
- Tier numerals right-aligned in an 80 px column to the left of the plate, 42 px Archivo 900, coloured per §1 rule 2, with a mono sub-label beneath (`sound` / `unsound` / count).
- Water: `top: 0`, height = mark depth, `.water`, scaled on load.
- Mark line: 320 px wide starting at `left: 60px` so it overhangs the plate on both sides, like a scribed line on a hull.
- `HELD HERE` callout to the right of the mark: 15 px Archivo 900 in the verdict colour, plus a mono line naming the check.
- Escalate variant: mark rendered as a dash pattern `repeating-linear-gradient(90deg, var(--ember) 0 13px, transparent 13px 23px)`; the region below the last resolved tier gets `repeating-linear-gradient(135deg, rgba(224,122,78,.16) 0 6px, transparent 6px 13px)`.
- Accessibility: wrap in `role="img"` with an `aria-label` that states the verdict and the depth in words. Every internal tick is `aria-hidden="true"`.

### 6.2 Hull glyph (fleet)

18 × 52 px miniature of the plate. Mark depths 12 / 24 / 36 / 45. Renders **two** mark elements always, controlled by `opacity` and `translateY`, so switching views glides instead of remounting. `transition-delay` = index × 6 ms. Hover thickens the inset edge to `rgba(232,179,60,.55)`.

### 6.3 Verdict block

Painted word + rule + one-sentence statement. In kilter and escalate carry a second line naming the count of checks that ran. Never a badge, never an icon, never a coloured pill.

### 6.4 Finding block

`.panel--flag`. Header row: class badge (`--rust` fill, `--chalk` text) + finding title. Then the statement (≤76ch), then the code excerpt, then the remedy in one sentence. Code excerpt: `--boot` panel, mono 13/1.9, `file:line` and the catching tier in the header strip, offending line marked with a 3 px `--mark` left border and raised to `--chalk`.

### 6.5 Register row

`display: flex`, baseline-aligned, `padding: 13px 14px`, bottom `1px solid var(--rule-faint)`. Columns: no. (52), tier (56), name (flex 1 1 320), assertion (flex 1 1 300, hidden until row hover), result (120). Result vocabulary is fixed: `Clear` / `Fired` / `Not applicable` / `Could not run` / `No objection` / `Query`.

### 6.6 Segmented control

Real `<button>` elements with `aria-pressed`. Selected: `--mark` fill, `--hull` text, `--mark` border. Unselected: transparent fill, `--chalk-2` text, `--mute-3` border. 6 px gap, 0 radius, 10 px × 16 px padding.

### 6.7 Buttons

Primary `.btn` (`--mark`). Secondary: transparent, `1px solid var(--mute-3)`, `--chalk` text; hover borders `--mark` and fills `rgba(232,179,60,.08)`. Minimum target 44 px. `:focus-visible { outline: 2px solid var(--mark); outline-offset: 3px }` — never remove it.

---

## 7. Content rules

**Verdict vocabulary is fixed and used identically everywhere:** `IN KILTER`, `OUT OF KILTER`, `ESCALATE`. Tiers are `T0 static`, `T1 runtime`, `T2 critic`. A T2 finding is a **query**, never a defect. A T0/T1 finding is a **defect**.

**Voice.** Active, present, plain. State what was found, where, and what to do. Errors do not apologise. The empty state is an invitation, not a shrug.

**Never assert a single correct method.** For contested methodology the UI reports: what was used, whether it was stated, and the magnitude of the sensitivity. The phrasing pattern is *"The number moves N points on a choice nobody wrote down."* Never *"you used the wrong split."*

**Placeholders.** Any figure the project has not measured renders as a bracketed slot — `[RATE]`, `[TOKENS]`, `[COUNT]` — set in `--mute-2`, never as `0`, never as a plausible-looking number. In a table of pending results use an em-dash in `--mute-2`. Delete this rule once the eval has run; until then it is the difference between a prototype and a lie.

**Bounds on screen.** The pass state carries a "what a pass does not mean" block and the escalate state carries "what a person should look at". These are not optional. Volunteering a limit reads as command of the problem; conceding it under questioning reads as overselling.

---

## 8. Data contract

The UI renders one run record and computes nothing. Verdict, tier attribution and sensitivity all arrive from the backend.

```jsonc
{
  "schema": "kilter.run/1",
  "run_id": "0a7f21c",
  "surveyed_at": "2026-10-18T01:48:00+05:30",
  "subject": {
    "path": "bace_rf.py", "code_sha256": "4e1b…c902",
    "dataset": "bace", "data_sha256": "90cf…11ad", "seed": 0
  },

  "verdict": "out_of_kilter",        // in_kilter | out_of_kilter | escalate
  "held_at": "t0",                   // t0 | t1 | t2 | null  → drives mark depth

  "checks": [{
    "id": "c04", "tier": "t0", "sound": true,
    "name": "Transform fitted before the partition",
    "assertion": "no fit() on a frame that outlives the split",
    "result": "fired"                // fired | clear | not_applicable | could_not_run
  }],

  "findings": [{
    "kind": "defect",                // defect (t0/t1) | query (t2)
    "class": "D1", "tier": "t0", "check_id": "c04",
    "site": { "path": "bace_rf.py", "line": 41, "from": 38, "to": 44 },
    "excerpt": "…",                  // raw source lines, from..to
    "statement": "…",                // what is wrong, one paragraph
    "remedy": "…"                    // one sentence, imperative
  }],

  "sensitivity": [{
    "choice": "split_protocol", "stated": false, "metric": "auroc",
    "as_written": { "label": "random",   "value": 89.30 },
    "alternative": { "label": "scaffold", "value": 78.25 },
    "delta": 11.05, "seeds": 1
  }],

  "blockers": [{                     // escalate only
    "tier": "t1", "affects": ["c10", "c11"],
    "reason": "…", "decision_for_human": "…", "command": "kilter audit …"
  }],

  "cost": {
    "model": null, "tokens_in": null, "tokens_out": null,
    "wall_clock_s": null, "usd_equivalent": null, "t2_share": null
  }
}
```

**Rendering rules.** `held_at: null` + `verdict: in_kilter` → mark at the top of the hull, no water. `held_at: null` + `verdict: escalate` → dashed mark in the hatch zone below the deepest resolved tier. `null` in `cost` → bracketed placeholder. `seeds: 1` → always print the single-seed caveat beside the sensitivity figures.

The fleet view consumes `kilter.eval/1`: an array of `{ variant_id, planted_class | null, expected_tier, runs: { a0, a1, a3, a4 } }` where each arm is a run record or `null` for not surveyed.

---

## 9. Accessibility floor

Non-negotiable, verified before merge:

- Body text ≥ 4.5:1, text ≥ 24 px or ≥ 18.66 px bold ≥ 3:1. The ratios in §1 are measured against `--hull`; re-measure anything placed on `--boot`.
- Tier and verdict distinctions differ in **lightness**, not hue alone.
- Real `<button>`, `<a href>`, `<input>` + `<label>`. Never `role`/`onClick` on a `div`.
- Visible `:focus-visible` on every interactive element.
- `role="img"` + `aria-label` on the mark scale, the fleet and any graphic that carries meaning; `aria-hidden="true"` on every decorative tick.
- `aria-pressed` on segmented controls.
- Hover-revealed content (assertions, commands) must be reachable another way: keyboard focus on the row, and permanently visible under reduced motion.
- Announce state changes at the start of an animation, not after it finishes.

---

## 10. Build order

1. **Tokens.** §1, §2, §5 as CSS custom properties in one file. Nothing hard-coded afterwards.
2. **Mark scale component.** Props: `depth` (`t0|t1|t2|esc|clear|unset`), `height`, `verdict`, `tierStates`. Everything else depends on this; get the geometry and the reduced-motion path right before building a screen.
3. **Out of kilter screen** against a hand-written fixture of `kilter.run/1`.
4. **In kilter screen.** Register, assertion reveal, bounds block.
5. **Escalate screen.** Blocker blocks, hatch zone, failed-settle animation.
6. **Fleet screen.** Hull glyph, staggered glide, pending arms.
7. **Wire to the real record emitter** (`core/record.py`). Until then every screen reads a fixture file; keep the fixtures in the repo as the UI's test data.
8. **Accessibility pass** against §9, then a reduced-motion pass with the OS setting on.

**Stack.** Plain TypeScript + Vite, or React if the fleet's forty-glyph state gets awkward. No component library — every component here is bespoke and a library's defaults would fight §3 and §4. One stylesheet of tokens plus per-component CSS modules.

---

## 11. Open items

- Per-class variant counts in the fleet (currently 8 clean + 7/7/6/6/6 across D1–D5) are a proposal. The blueprint fixes only 8 clean and 32 defective.
- `blueprint.md` §5.7 forbids a web UI in Phase 1 and that still stands. This spec is Phase 2 work. Do not spend Phase 1 hours here.
- Escalate copy assumes the parse-failure blocker as its worked example. Replace with a real one from the first eval run that actually escalates.
- Abstention calibration figures are the only numbers on the escalate screen and they are all placeholders. The curve is a reported metric, so these slots must fill before the screen is shown to anyone.

---

## 12. Reference

- Motion tokens: IBM Carbon, Motion — https://carbondesignsystem.com/elements/motion/overview/
- Motion application rules: Atlassian, Applying motion — https://atlassian.design/foundations/motion/applying-motion
- Reduced motion: WCAG 2.3.3, Animation from Interactions — https://wcag.dock.codes/documentation/wcag-success-criteria/wcag233/
- Designs: the "Kilter Frontend Directions" canvas, boards `Draft`, `Draft-Clean`, `Draft-Escalate`, `Draft-Fleet`.

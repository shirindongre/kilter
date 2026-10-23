// The three verdict screens (out of kilter, in kilter, escalate) are one renderer driven by the run view.
// The UI computes nothing: verdict, tier attribution, outcome and sensitivity all arrive from the backend.
import {
  h, clear, tierChip, TIER, VERDICT_CLASS, RESULT_WORD, OUTCOME_WORD, announce, when, n0, slot, copyText, download, segmented,
} from "../util.js";
import { MarkScale } from "../markscale.js";
import { auditWithProgress } from "../progress.js";
import * as api from "../api.js";

const short = (v) => (v || "").slice(0, 16);

export async function renderRun(root, saved, ctx) {
  clear(root);
  const ms = MarkScale({ height: 620 });
  const body = h("div", { class: "hero-body" });
  const sections = h("div", {});
  root.append(h("div", { class: "page wrap" }, h("div", { class: "hero" }, h("div", { class: "hero-scale" }, ms.el), body), sections));

  let current = saved;
  let siblings = ctx.siblings ? await ctx.siblings(saved.view).catch(() => null) : null;

  function paint(s, animate) {
    current = s;
    const v = s.view;
    const heldCheck = v.held_at && v.findings.length ? v.findings[0].check_id : null;
    ms.set({ mark: v.mark, heldCheck, unresolved: v.unresolved_tier, blockers: v.blockers.length, checksRan: v.checks_ran }, { animate });
    announce(`${v.verdict_word}. ${v.statement}`);
    document.title = `${v.verdict_word}: ${v.subject.path} | Kilter`;
    paintBody(v, s);
    paintSections(v, s);
  }

  function paintBody(v, s) {
    clear(body);
    const sample = v.sample;
    body.append(h("div", { class: "stack" },
      h("div", { class: "t-label" }, sample && sample.label && sample.kind !== "upload" ? sample.label : "Audit of"),
      h("h1", { class: "t-page", style: "font-size:34px;overflow-wrap:anywhere" }, v.subject.path)));

    const word = h("h2", { class: `t-mark ${VERDICT_CLASS[v.verdict]}` }, v.verdict_word);
    body.append(h("div", { class: "verdict" }, word, h("div", { class: "v-rule", "aria-hidden": "true" }),
      h("p", { class: "lead" }, v.statement), h("div", { class: "meta" }, h("span", {}, v.detail))));

    if (sample && sample.truth) body.append(truthStrip(sample.truth));

    // Arm toggle: both arms for one script, so switching glides the mark and shows what the critic adds.
    const arms = siblings;
    const bothHere = arms && arms.A4 && arms.A3;
    if (v.stored) {
      // An evaluation record is a fixed artifact: no arm toggle (it would swap in a different, live run) and no re-run.
      body.append(h("p", { class: "note" }, h("b", {}, "Stored evaluation record. "),
        "Read from results/ as the evaluation wrote it; nothing was re-run. The other arm is one click back on the fleet page."),
        h("div", { class: "row" }, h("a", { class: "btn btn--2 k-btn", style: "display:inline-flex;align-items:center;text-decoration:none", href: "#/fleet" }, "Back to the fleet")));
    } else if (bothHere) {
      body.append(h("div", { class: "field" }, h("span", { class: "t-label" }, "Arm"),
        segmented([{ value: "A4", label: "Deterministic: T0 + T1" }, { value: "A3", label: "Full: T0 + T1 + T2" }], v.arm, async (arm) => {
          const sum = arms[arm];
          if (!sum || sum.run_id === current.view.run_id) return;
          paint(await api.getRun(sum.run_id), false);
          history.replaceState(null, "", `#/run/${sum.run_id}`);
        }, "Arm")));
    } else if (api.getMode() === "api" && sample && (sample.kind === "demo" || sample.kind === "variant")) {
      const other = v.arm === "A4" ? "A3" : "A4";
      const slotEl = h("div", { class: "stack" });
      body.append(h("div", { class: "field" }, h("span", { class: "t-label" }, "Compare"),
        h("div", { class: "row" }, h("button", { type: "button", class: "btn btn--2 k-btn", onclick: async () => {
          const job = await auditWithProgress(slotEl, { sample_id: sample.id, arm: other });
          if (job.status === "done") {
            siblings = await ctx.siblings(v).catch(() => null);
            paint(await api.getRun(job.run_id), false);
            history.replaceState(null, "", `#/run/${job.run_id}`);
          }
        } }, other === "A3" ? "Add the critic (T2) and compare" : "Run the deterministic arm and compare")), slotEl));
    }

    const rid = v.run_id;
    body.append(h("div", { class: "row" },
      h("button", { type: "button", class: "btn btn--2 k-btn", onclick: () => download(`${rid}.md`, s.report_md, "text/markdown") }, "Download report (.md)"),
      h("button", { type: "button", class: "btn btn--2 k-btn", onclick: () => download(`${rid}.record.json`, JSON.stringify(s.record, null, 2), "application/json") }, "Download run record (.json)"),
      h("a", { class: "btn btn--2 k-btn", style: "display:inline-flex;align-items:center;text-decoration:none", href: "#/" }, "Audit another")));
  }

  function paintSections(v, s) {
    clear(sections);
    if (v.findings.length) {
      sections.append(section("What was found", v.findings.map((f) => findingBlock(f, v))));
    }
    for (const sens of v.sensitivity) sections.append(section("Split sensitivity", [sensBlock(sens)]));
    if (v.notes.length) sections.append(section("Noted, not findings", v.notes.map(noteBlock)));
    if (v.blockers.length) {
      sections.append(section(v.verdict === "escalate" ? "What a person should look at" : "What could not be checked", v.blockers.map(blockerBlock)));
    }
    sections.append(section("Checks run", [register(v)]));
    if (v.bounds) sections.append(section("What a pass does not mean", [h("ul", { class: "bounds" }, v.bounds.map((b) => h("li", {}, b)))]));
    sections.append(section("Cost and provenance", [costBlock(v), provenanceBlock(v, s)]));
    sections.append(section("Script as audited", [sourceBlock(v)]));
  }

  paint(saved, true);
}

function section(title, kids) {
  return h("section", { class: "section" }, h("h2", { class: "t-section" }, title), h("div", { class: "stack" }, kids));
}

// --- ground truth (sample browser runs) ----------------------------------------------------------
function truthStrip(t) {
  const good = t.outcome === "caught" || t.outcome === "clean_ok";
  const planted = t.planted_class ? `Planted ${t.planted_class}${t.site_line ? ` at line ${t.site_line}` : ""}` : "Planted nothing: this analysis is clean";
  const site = t.outcome === "caught" && t.site_match != null
    ? (t.site_match ? "At the planted line." : "At a different line than the planted one.") : "";
  return h("div", { class: "truth" }, h("span", { class: "t-label" }, "Ground truth"), h("span", {}, planted),
    h("span", { class: `w ${good ? "w--ok" : (t.outcome === "escalated" ? "w--none" : "w--bad")}` }, OUTCOME_WORD[t.outcome] || t.outcome),
    site ? h("span", { class: "t-label" }, site) : null);
}

// --- findings ------------------------------------------------------------------------------------
function findingBlock(f, v) {
  const isQuery = f.kind === "query";
  const head = h("div", { class: "finding-head" },
    h("span", { class: `badge ${isQuery ? "badge--q" : ""}` }, isQuery ? `Query ${f.class}` : f.class),
    h("h3", { class: "t-finding" }, f.class_name));
  const wit = h("div", { class: "witnesses" }, h("span", {}, f.witnesses.length > 1 ? "Caught by" : "Caught by"),
    f.witnesses.map((w) => [tierChip(w.tier), w.confidence != null ? h("span", { class: "num" }, `confidence ${w.confidence.toFixed(2)}`) : null]),
    f.unreported ? h("span", {}, "Unreported: the method is not stated, which Kilter flags without ruling on a single correct one.") : null);
  const kids = [head, wit, h("p", { class: "stmt" }, f.statement)];
  if (f.excerpt) kids.push(codeBlock(f));
  kids.push(h("p", { class: "evid" }, `evidence: ${f.evidence}`));
  const critic = f.witnesses.find((w) => w.tier === "t2" && f.tier !== "t2");
  if (critic) kids.push(h("p", { class: "wit-note" }, `The critic's reading: ${critic.message}`));
  kids.push(h("p", { class: "remedy" }, h("b", {}, "What to do. "), f.remedy));
  return h("div", { class: `panel finding ${isQuery ? "panel--query" : "panel--flag"} k-block` }, kids);
}

function codeBlock(f) {
  const ex = f.excerpt;
  return h("div", { class: "code" },
    h("div", { class: "code-head" }, h("span", {}, `${f.site.path}:${ex.line}`), tierChip(f.tier)),
    h("div", { class: "code-body" }, ex.lines.map((l) =>
      h("div", { class: `code-line ${l.n === ex.line ? "hit" : ""}` }, h("i", {}, String(l.n)), h("span", {}, l.text || " ")))));
}

function sensBlock(s) {
  const lo = 0.5, hi = 1.0;   // AUROC from chance to perfect; the bars span that range
  const rows = s.scores.map((sc) => h("div", { class: `sens-row ${sc.label === s.stated_label ? "stated" : ""}` },
    h("span", { class: "lab" }, sc.label + (sc.label === s.stated_label ? " (stated)" : "")),
    h("div", { class: "sens-bar", role: "presentation" }, h("i", { style: `width:${Math.max(0, Math.min(100, ((sc.value - lo) / (hi - lo)) * 100))}%` })),
    h("span", { class: "val num" }, sc.value.toFixed(3))));
  return h("div", { class: "panel sens" },
    h("p", { class: "t-lead" }, s.headline),
    h("div", { class: "sens" }, rows),
    h("p", { class: "note" }, `AUROC by split protocol, bars from 0.5 to 1.0. ${s.seeds === 1 ? "One seed: indicative only. " : s.seeds ? `${s.seeds} seeds each. ` : ""}Kilter reports how far the number moves; it does not say which protocol is correct.`));
}

function noteBlock(n) {
  return h("div", { class: "panel" }, h("div", { class: "row" }, tierChip(n.tier), h("span", { class: "t-label" }, n.class)),
    h("p", { class: "t-dense", style: "margin-top:8px" }, n.message), h("p", { class: "evid t-mono" }, n.evidence));
}

// --- blockers ------------------------------------------------------------------------------------
function blockerBlock(b) {
  const copied = h("span", { class: "t-label", role: "status" }, "");
  return h("div", { class: "panel panel--esc blocker k-block" },
    h("div", { class: "finding-head" }, tierChip(b.tier), h("h3", { class: "t-finding" }, b.title)),
    h("p", { class: "stmt" }, b.reason),
    b.evidence ? h("p", { class: "evid t-mono" }, b.evidence) : null,
    h("p", { class: "decide" }, h("b", {}, "Decision for you. "), b.decision_for_human),
    h("div", { class: "cmd k-cmd" }, h("code", {}, b.command),
      h("button", { type: "button", class: "btn btn--2 btn--sm k-btn", onclick: async () => { copied.textContent = (await copyText(b.command)) ? "Copied" : "Copy failed"; } }, "Copy command"), copied));
}

// --- register ------------------------------------------------------------------------------------
function register(v) {
  const rows = v.checks.map((c, i) => h("div", { class: `reg-row k-row ${v.verdict === "in_kilter" ? "k-stamp" : ""}`, role: "listitem", tabindex: "0", style: `--i:${i}` },
    h("span", { class: "no" }, String(c.no).padStart(2, "0")),
    h("span", { class: "tr" }, tierChip(c.tier)),
    h("span", { class: "nm" }, c.name),
    h("span", { class: "as k-assert" }, c.assertion),
    h("span", { class: `rs rs--${c.result}` }, RESULT_WORD[c.result] || c.result)));
  const kids = [h("div", { class: "register", role: "list", "aria-label": "Checks that ran" }, rows)];
  if (v.arm === "A4") kids.push(h("p", { class: "note" }, "The T2 critic did not run in this arm. Hover or focus a row to read what it asserts."));
  else kids.push(h("p", { class: "note" }, "Hover or focus a row to read what it asserts."));
  return h("div", {}, kids);
}

// --- cost and provenance ---------------------------------------------------------------------------
function fig(label, value, sub) {
  return h("div", { class: "fig" }, h("div", { class: "t-fig num" }, value), h("small", {}, label), sub ? h("span", { class: "t-mono" }, sub) : null);
}

function costBlock(v) {
  const c = v.cost;
  const none = c.calls === 0;
  return h("div", { class: "stack" },
    h("div", { class: "figs" },
      fig("Tokens in", none ? "0" : n0(c.tokens_in), none ? "deterministic tiers only" : null),
      fig("Tokens out", none ? "0" : n0(c.tokens_out), none ? null : "includes hidden reasoning"),
      fig("LLM time", none ? "0 s" : `${c.llm_seconds.toFixed(1)} s`, none ? null : "of the recorded call"),
      fig("LLM calls", String(c.calls), c.calls ? `${c.replayed_calls} replayed from a recording` : null),
      fig("Cost in USD", slot("USD"), "no list price configured")),
    c.model ? h("p", { class: "note" }, `Model: ${c.model}${c.model_requested && c.model_requested !== c.model ? ` (requested ${c.model_requested})` : ""}.`) : null);
}

function provenanceBlock(v, s) {
  const p = v.provenance;
  const out = h("span", { role: "status" }, p.digest_ok ? h("span", { class: "ok" }, " Digest matched when the record was written.") : h("span", { class: "bad" }, " Digest did not match."));
  const btn = h("button", { type: "button", class: "btn btn--2 btn--sm k-btn", onclick: async () => {
    clear(out);
    try {
      const r = await api.verify(v.run_id);
      out.append(r.ok ? h("span", { class: "ok" }, " Digest verified just now: the saved record is unedited.") : h("span", { class: "bad" }, " Digest does NOT match: the saved record was edited."));
    } catch { out.append(h("span", { class: "bad" }, " Verification needs the local server.")); }
  } }, "Verify digest");
  const libs = Object.entries(p.versions || {}).map(([k, val]) => `${k} ${val}`).join(" . ");
  return h("dl", { class: "kv" },
    h("dt", {}, "Run"), h("dd", {}, v.run_id),
    h("dt", {}, "Surveyed"), h("dd", {}, when(v.surveyed_at)),
    h("dt", {}, "Arm"), h("dd", {}, `${v.arm}: ${v.arm_label}`),
    h("dt", {}, "Critic calls"), h("dd", {}, v.llm_mode === "replay" ? "replayed from recordings" : (v.llm_mode || "n/a")),
    h("dt", {}, "Input hash"), h("dd", {}, short(v.subject.input_sha256)),
    p.source_matches == null ? null : [h("dt", {}, "Script shown"), h("dd", {}, p.source_matches
      ? h("span", { class: "ok" }, "Its bytes hash to the input hash above.")
      : h("span", { class: "bad" }, "Its bytes do NOT hash to the input hash: the lines shown may not be the ones audited."))],
    h("dt", {}, "Verifier code hash"), h("dd", {}, short(p.code_sha256)),
    h("dt", {}, "Record digest"), h("dd", {}, short(p.record_sha256), " ", btn, out),
    p.t2_prompt_sha256 ? [h("dt", {}, "Critic prompt hash"), h("dd", {}, short(p.t2_prompt_sha256))] : null,
    p.convict_at != null ? [h("dt", {}, "Thresholds"), h("dd", {}, `critic convicts at ${p.convict_at}, escalates from ${p.escalate_at} (judgment calls, not literature)`)] : null,
    h("dt", {}, "Libraries"), h("dd", {}, libs));
}

function sourceBlock(v) {
  const hits = new Set(v.findings.map((f) => f.excerpt && f.excerpt.line).filter(Boolean));
  const lines = v.subject.source.split("\n");
  return h("details", { class: "src" }, h("summary", {}, `${v.subject.path}, ${lines.length} lines${hits.size ? `, ${hits.size} marked` : ""}`),
    h("div", { class: "code" }, h("div", { class: "code-body" }, lines.map((t, i) =>
      h("div", { class: `code-line ${hits.has(i + 1) ? "hit" : ""}` }, h("i", {}, String(i + 1)), h("span", {}, t || " "))))));
}

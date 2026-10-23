// The fleet: every evaluated script, both arms, read from the saved evaluation (AIMS D-025).
// Nothing here is computed. Counts, outcomes, intervals and the reconciliation arrive from web/fleet.py, which reads
// results/. Every string is rendered with textContent only.
import { h, clear, segmented, OUTCOME_WORD, announce } from "../util.js";
import * as api from "../api.js";

const ARM = {
  A4: { tag: "A4", name: "Deterministic: T0 + T1" },
  A3: { tag: "A3", name: "Full: T0 + T1 + T2" },
  scope: { tag: "Scope", name: "Full, with the scope-claim prompt" },
};
const TILE_WORD = { ...OUTCOME_WORD, clean_ok: "Passed" };   // "Clean, as planted" is too long for a tile
const PREDICTED = [["pass", "Passed"], ["escalate", "Escalated"]];
const short = (v) => (v || "").slice(0, 12);
const pct = (x) => `${Math.round(x * 100)}%`;
const interval = (ci) => (ci ? `${pct(ci[0])} to ${pct(ci[1])}` : null);
const tierTag = (t) => h("span", { class: `tier tier--${t}` }, t.toUpperCase());

export async function renderFleet(root, ctx) {
  clear(root);
  const page = h("div", { class: "page wrap" });
  root.append(page);
  page.append(h("div", { class: "stack", style: "margin-bottom:28px" },
    h("div", { class: "t-label" }, "Fleet"),
    h("h1", { class: "t-page" }, "Every script the evaluation audited"),
    h("p", { class: "t-lead" }, "Each script was generated with one planted defect at a known line, or none. This page reads the saved run records and shows what each arm made of every one. Nothing is re-run.")));

  const fleet = await api.fleet();
  if (!fleet || !fleet.available) {
    page.append(h("div", { class: "errbox", role: "status" }, h("b", {}, "No evaluation results on this machine."),
      h("span", { class: "note" }, (fleet && fleet.reason) || "The fleet needs the results folder."),
      h("span", { class: "note" }, "results/ is not in git. Put the evaluation's results/ folder at the repository root (it holds runs/, variants/, holdout2/ and summary.json), then restart the server, or rebuild the offline copy with python web\\build_fixtures.py.")));
    return;
  }
  const live = api.getMode() === "api";
  page.append(integrity(fleet));
  if (!live) page.append(h("p", { class: "note", style: "margin-top:14px" }, "Offline copy: the numbers below are saved, but run pages open only in the local server (python web/server.py)."));

  const state = { set: "all" };
  const options = [{ value: "all", label: "All 80" }, ...fleet.sets.map((s) => ({ value: s.id, label: `${s.label} (${s.n})` }))];
  const body = h("div", { class: "stack", style: "gap:56px;margin-top:32px" });
  const filter = segmented(options, state.set, (v) => { state.set = v; paint(); announce(`Showing ${v === "all" ? "all sets" : fleet.sets.find((s) => s.id === v).label}`); }, "Set");
  page.append(h("div", { class: "row", style: "margin-top:32px" }, filter,
    h("span", { class: "note" }, "Sets are different populations and are never pooled.")), body);
  page.append(reconciliation(fleet));

  function paint() {
    clear(body);
    for (const s of fleet.sets) {
      if (state.set === "all" || state.set === s.id) body.append(setSection(fleet, s, live));
    }
  }
  paint();
}

// --- what was read, and whether it adds up ---------------------------------------------------------

function integrity(f) {
  const p = f.provenance, r = f.reconciliation;
  const oneHash = p.code_sha256.length === 1;
  const treeMatches = oneHash && p.code_sha256[0] === p.tree_code_sha256;
  const pyMatches = p.python.length === 1 && p.python[0] === p.running_python;
  const ok = (good, text) => h("li", {}, h("span", { class: good ? "ok" : "bad" }, good ? "OK  " : "CHECK  "), text);
  const items = [
    ok(p.digests_ok === p.records, `${p.digests_ok} of ${p.records} run records match their own digest.`),
    ok(oneHash, oneHash ? `One verifier code hash across all of them: ${short(p.code_sha256[0])}.`
      : `${p.code_sha256.length} different code hashes across the records: ${p.code_sha256.map(short).join(", ")}. They are not one evaluation.`),
    ok(r.disagree.length === 0, r.disagree.length === 0
      ? `All ${r.checked} counts on this page agree with the evaluation's own summary files.`
      : `${r.disagree.length} of ${r.checked} counts disagree with the evaluation's summary files (listed below).`),
  ];
  if (!treeMatches) items.push(ok(false, `This checkout's verifier hashes to ${short(p.tree_code_sha256)}, not ${short(p.code_sha256[0])}. A live audit here would write a record with a different code hash, so these records are not reproducible from this checkout as it stands.`));
  if (!pyMatches) items.push(ok(false, `The records were produced on Python ${p.python.join(", ")}; this server runs ${p.running_python}. Generated scripts can differ in bytes between minor versions, so scripts shown here come from results/variants.`));
  for (const t of f.problems) items.push(ok(false, t));
  return h("section", { class: "panel panel--top", style: "margin-top:8px", "aria-label": "What was read" },
    h("div", { class: "t-label", style: "margin-bottom:12px" }, "What was read"),
    h("ul", { class: "fleet-checks" }, items),
    h("p", { class: "note", style: "margin-top:12px" }, `Model ${p.models.join(", ")}; critic prompt ${short(p.prompt_sha256[0])}. Critic answers were replayed from recordings.`));
}

function reconciliation(f) {
  const r = f.reconciliation;
  const rows = [...r.disagree, ...r.checks.filter((c) => c.ok)];
  return h("details", { class: "src", style: "margin-top:56px" },
    h("summary", {}, `Every count checked against the evaluation's summary files (${r.agree} of ${r.checked} agree)`),
    h("div", { style: "overflow-x:auto" }, h("table", { class: "tbl" },
      h("caption", { class: "sr" }, "Counts derived from run records beside the evaluation's reported counts"),
      h("thead", {}, h("tr", {}, ["Count", "From run records", "Reported", "Reported in", "Agree"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, rows.map((c) => h("tr", {},
        h("td", {}, h("span", { class: "t-mono" }, c.where)), h("td", {}, h("span", { class: "t-mono" }, c.derived)),
        h("td", {}, h("span", { class: "t-mono" }, c.reported)), h("td", {}, h("span", { class: "t-mono" }, c.source)),
        h("td", {}, h("span", { class: c.ok ? "out out--caught" : "out out--missed" }, c.ok ? "Agree" : "DISAGREE"))))))));
}

// --- one set ---------------------------------------------------------------------------------------

function setSection(f, s, live) {
  const rep = f.reported[s.id] || {};
  return h("section", { class: "stack", "aria-labelledby": `fs-${s.id}`, style: "gap:26px" },
    h("div", { class: "stack", style: "gap:8px" }, h("h2", { class: "t-section", id: `fs-${s.id}` }, `${s.label}, ${s.n} scripts`), h("p", { class: "note" }, s.about)),
    h("div", { class: "fleet-arms" }, s.arms.map((arm) => armFigs(arm, s.totals[arm]))),
    pairedNote(s, rep),
    grid(s, f.variants.filter((v) => v.set === s.id), live),
    h("div", { class: "fleet-conf" }, s.arms.map((arm) => confusion(s, arm))));
}

function armFigs(arm, t) {
  const fig = (n, l, sub) => h("div", { class: "fig" }, h("div", { class: "t-fig num" }, n), h("small", {}, l), sub ? h("span", { class: "t-mono" }, sub) : null);
  const extra = [t.wrong_class ? `${t.wrong_class} wrong class` : null, t.escalated ? `${t.escalated} escalated` : null].filter(Boolean).join(", ");
  return h("div", { class: "panel fleet-arm" }, h("div", { class: "t-label" }, `${ARM[arm].tag}  ${ARM[arm].name}`),
    h("div", { class: "figs", style: "gap:36px" },
      fig(`${t.caught}/${t.defective}`, "planted defects caught", t.detect_ci ? `95% interval ${interval(t.detect_ci)}${extra ? `; ${extra}` : ""}` : (extra || "no interval in the results files")),
      fig(`${t.false_alarm}/${t.clean}`, "false alarms on clean scripts", t.fp_ci ? `95% interval ${interval(t.fp_ci)}` : (t.clean_escalated ? `${t.clean_escalated} escalated` : null))));
}

function pairedNote(s, rep) {
  const p = rep.paired;
  if (!p) return null;
  const line = (label, x) => `${label}: ${x.only_first} vs ${x.only_second} scripts caught by only one arm, exact p = ${x.p.toPrecision(2)}`;
  if (s.id === "holdout2") return h("p", { class: "note" }, `Scope prompt against the frozen prompt, paired. ${line("Overclaims", p.detect_B5)}. Not significant at n = 8; read it as a direction, not a result. (holdout2_summary.json)`);
  const cls = p.D5;
  return cls ? h("p", { class: "note" }, `A3 against A4, paired, on D5. ${line("D5", cls)}. (summary.json)`) : null;
}

// --- the grid: base script x kind of script, two arms per tile ---------------------------------------

function grid(s, vs, live) {
  const bases = [...new Set(vs.map((v) => v.row))];
  const cell = (v, arm) => {
    const c = v.cells[arm];
    if (!c) return null;
    const good = c.outcome === "caught" || c.outcome === "clean_ok";
    const label = h("span", { class: "fa" }, ARM[arm].tag);
    const word = h("span", { class: `out out--${c.outcome}` }, TILE_WORD[c.outcome] || c.outcome);
    const extra = c.convicted.filter((k) => k !== v.planted_class);
    const inner = [label, word, c.held_at ? tierTag(c.held_at) : null,
      extra.length ? h("span", { class: "t-mono fa-extra", title: "Also convicted of" }, `+${extra.join(" +")}`) : null];
    const desc = `${v.id}, arm ${ARM[arm].tag}: ${OUTCOME_WORD[c.outcome] || c.outcome}${c.held_at ? `, held at ${c.held_at.toUpperCase()}` : ""}`;
    if (live && c.run_id) return h("a", { class: `fline ${good ? "" : "fline--bad"}`, href: `#/run/${encodeURIComponent(c.run_id)}`, "aria-label": `${desc}. Open the run.` }, inner);
    return h("span", { class: `fline ${good ? "" : "fline--bad"}`, title: c.run_id ? "Run pages need the local server" : "The evaluation stored a critic row for this script, not a full run record.", "aria-label": desc }, inner);
  };
  const rows = bases.map((base) => h("tr", {},
    h("th", { scope: "row", class: "frow" }, base.replace("-", " ")),
    s.columns.map((col) => {
      const v = vs.find((x) => x.row === base && x.col === col.id);
      return h("td", { class: "ftile" }, v ? [cell(v, "A4"), cell(v, "A3"), cell(v, "scope")] : null);
    })));
  return h("div", { class: "fleet-scroll", role: "region", tabindex: "0", "aria-label": `${s.label}: outcome of each script and arm` },
    h("table", { class: "tbl fgrid" }, h("caption", { class: "sr" }, `${s.label}: one tile per script, one line per arm`),
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Base script"), s.columns.map((c) => h("th", { scope: "col", title: c.long }, c.class ? `${c.class}  ${c.name}` : c.name)))),
      h("tbody", {}, rows)));
}


// --- confusion by planted class --------------------------------------------------------------------

function confusion(s, arm) {
  const conf = s.confusion[arm];
  const used = new Set(Object.keys(conf).filter((k) => k !== "clean"));
  for (const v of Object.values(conf)) for (const k of Object.keys(v.predicted)) used.add(k);
  const cols = [...used].filter((k) => /^D\d+$/.test(k)).sort();
  const wrapped = [...cols.map((k) => [k, k]), ...PREDICTED.filter(([k]) => used.has(k))];
  const head = ["Planted", "Scripts", ...wrapped.map(([, l]) => (/^D/.test(l) ? `Convicted of ${l}` : l)), "Outcome"];
  const rows = Object.entries(conf).map(([planted, v]) => {
    const outcome = Object.entries(v.outcomes).map(([o, n]) => `${n} ${(TILE_WORD[o] || o).toLowerCase()}`).join(", ");
    return h("tr", {},
      h("th", { scope: "row" }, h("span", { class: "t-mono" }, planted === "clean" ? "clean" : planted)),
      h("td", { class: "num" }, String(v.n)),
      wrapped.map(([k]) => {
        const n = v.predicted[k] || 0;
        const onDiagonal = k === planted || (planted === "clean" && k === "pass");
        return h("td", { class: `num ${onDiagonal ? "fc-diag" : ""} ${n === 0 ? "fc-zero" : ""}` }, String(n));
      }),
      h("td", {}, h("span", { class: "t-mono" }, outcome)));
  });
  const multi = Object.values(conf).reduce((a, v) => a + v.multi, 0);
  return h("div", { class: "stack", style: "gap:12px" },
    h("div", { class: "t-label" }, `${ARM[arm].tag}: what each planted class was convicted of`),
    h("div", { style: "overflow-x:auto" }, h("table", { class: "tbl fconf" },
      h("caption", { class: "sr" }, `${s.label}, ${ARM[arm].name}: planted class against classes convicted`),
      h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, rows))),
    multi ? h("p", { class: "note" }, `${multi} script${multi === 1 ? " was" : "s were"} convicted of more than one class, so a row can add to more than its script count.`) : null);
}

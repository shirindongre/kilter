// The sample browser: 3 demos + 80 evaluation variants, each with its planted ground truth and the outcome of any run.
import { h, clear, segmented, OUTCOME_WORD, announce } from "../util.js";
import * as api from "../api.js";

const GROUPS = [
  { value: "all", label: "All" }, { value: "demo", label: "Demos" }, { value: "main", label: "Main" },
  { value: "holdout", label: "Holdout 1" }, { value: "holdout2", label: "Holdout 2" },
];

const VERDICT = { in_kilter: "In kilter", out_of_kilter: "Out of kilter", escalate: "Escalate" };

export async function renderSamples(root, ctx) {
  clear(root);
  const page = h("div", { class: "page wrap" });
  root.append(page);
  if (api.getMode() === "static") {
    page.append(h("h1", { class: "t-page" }, "Samples"), h("p", { class: "note" }, "The sample browser needs the local server: python web/server.py."));
    return;
  }
  let all = await api.samples();
  const state = { group: "all", batch: null };
  const summary = h("div", { class: "summary", role: "status" });
  const tableWrap = h("div", { style: "overflow-x:auto" });
  const batchOut = h("div", { class: "stack" });
  const filter = segmented(GROUPS, state.group, (v) => { state.group = v; paintTable(); }, "Group");

  page.append(h("div", { class: "stack", style: "margin-bottom:28px" },
    h("div", { class: "t-label" }, "Samples"),
    h("h1", { class: "t-page" }, "Every script Kilter has ground truth for"),
    h("p", { class: "t-lead" }, "Each variant was generated with a planted defect at a known line, or none. Audit one and the page says whether Kilter caught what was planted.")),
    summary, h("div", { class: "row", style: "margin:20px 0" }, filter,
      h("button", { type: "button", class: "btn btn--2 k-btn", onclick: auditAll }, "Audit all shown (deterministic)")), batchOut, tableWrap);

  const inGroup = () => all.filter((s) => state.group === "all" || s.group === state.group);

  function paintSummary() {
    clear(summary);
    const runs = inGroup().map((s) => s.runs && (s.runs.A4 || s.runs.A3)).filter(Boolean);
    const count = (o) => runs.filter((r) => r.outcome === o).length;
    const planted = inGroup().filter((s) => s.planted_class).length;
    const fig = (n, l) => h("div", { class: "fig" }, h("div", { class: "t-fig num" }, String(n)), h("small", {}, l));
    summary.append(fig(inGroup().length, "scripts shown"), fig(planted, "with a planted defect"), fig(runs.length, "audited"),
      fig(count("caught"), "caught"), fig(count("missed"), "missed"), fig(count("false_alarm"), "false alarms"));
  }

  function outCell(run) {
    if (!run) return h("span", { class: "out out--none" }, "not run");
    return h("span", { class: `out out--${run.outcome || "none"}` }, run.outcome ? OUTCOME_WORD[run.outcome] : VERDICT[run.verdict]);
  }

  function paintTable() {
    paintSummary();
    clear(tableWrap);
    const rows = inGroup().map((s) => {
      const a4 = s.runs && s.runs.A4, a3 = s.runs && s.runs.A3;
      const view = a4 || a3;
      return h("tr", {},
        h("td", {}, h("div", { class: "id" }, s.id), h("div", { class: "sub" }, s.kind === "demo" ? s.label : s.group)),
        h("td", {}, s.planted_class ? h("span", { class: "t-mono" }, `${s.planted_class}${s.site_line ? ` . line ${s.site_line}` : ""}`) : h("span", { class: "t-mono" }, "clean")),
        h("td", {}, outCell(a4)),
        h("td", {}, outCell(a3)),
        h("td", {}, h("div", { class: "acts" },
          view ? h("a", { class: "btn btn--2 btn--sm k-btn", style: "text-decoration:none;display:inline-flex;align-items:center", href: `#/run/${view.run_id}` }, "Open") : null,
          h("button", { type: "button", class: "btn btn--2 btn--sm k-btn", onclick: () => audit(s, "A4") }, a4 ? "Re-run" : "Audit"),
          s.artifact_ready ? h("button", { type: "button", class: "btn btn--2 btn--sm k-btn", title: "Add the critic", onclick: () => audit(s, "A3") }, a3 ? "Re-run +T2" : "Audit +T2") : null)));
    });
    tableWrap.append(h("table", { class: "tbl" },
      h("caption", { class: "sr" }, "Evaluation scripts, planted defect and audit outcome"),
      h("thead", {}, h("tr", {}, ["Script", "Planted", "Deterministic (T0+T1)", "Full (+T2)", ""].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, rows)));
  }

  async function refresh() { all = await api.samples(); paintTable(); }

  async function audit(s, arm) {
    clear(batchOut).append(h("p", { class: "note", role: "status" }, `Auditing ${s.id} (${arm})...`));
    const job = await api.runAudit({ sample_id: s.id, arm }, () => {}).catch((e) => ({ status: "error", error: e.message }));
    if (job.status === "done") ctx.go(`#/run/${job.run_id}`);
    else clear(batchOut).append(h("div", { class: "errbox", role: "alert" }, h("b", {}, job.error || "The audit failed."), job.hint ? h("span", { class: "note" }, job.hint) : null));
  }

  async function auditAll() {
    const todo = inGroup();
    clear(batchOut);
    const label = h("p", { class: "note", role: "status" }, "");
    const bar = h("i", { style: "transform:scaleX(0)" });
    batchOut.append(label, h("div", { class: "pbar" }, bar));
    state.batch = true;
    for (let i = 0; i < todo.length; i++) {
      label.textContent = `Auditing ${todo[i].id} (${i + 1} of ${todo.length})`;
      bar.style.transform = `scaleX(${i / todo.length})`;
      try {
        const job = await api.runAudit({ sample_id: todo[i].id, arm: "A4" }, () => {});
        if (job.status === "error") { label.textContent = `Stopped at ${todo[i].id}: ${job.error}`; break; }
      } catch (e) { label.textContent = `Stopped at ${todo[i].id}: ${e.message}`; break; }
      if (i % 4 === 3) await refresh();
    }
    bar.style.transform = "scaleX(1)";
    await refresh();
    announce("Batch finished");
    if (label.textContent.startsWith("Auditing")) label.textContent = `Finished ${todo.length} scripts.`;
  }

  paintTable();
}

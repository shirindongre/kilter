// The tiers lighting up while an audit runs. Used by the audit screen, the sample browser and the arm toggle.
import { h, clear, announce } from "./util.js";
import * as api from "./api.js";

const WORD = { waiting: "waiting", running: "running", done: "done", failed: "failed" };

export function progressPanel(title = "Descending through the tiers") {
  const list = h("div", { class: "stages", role: "list" });
  const el = h("div", { class: "stack", "aria-live": "off" }, h("div", { class: "t-panel" }, title), list);
  let last = "";
  function update(job) {
    clear(list);
    for (const s of job.stages) {
      list.append(h("div", { class: "stage", role: "listitem", "data-s": s.status },
        h("span", { class: "nm" }, s.label), h("span", { class: "st" }, WORD[s.status] || s.status)));
    }
    const running = job.stages.find((s) => s.status === "running");
    if (running && running.id !== last) { last = running.id; announce(`${running.label} started`); }
  }
  return { el, update };
}

export function errorBox(message, hint) {
  return h("div", { class: "errbox", role: "alert" }, h("b", {}, message), hint ? h("span", { class: "note" }, hint) : null);
}

/** Run an audit, drive a progress panel, and resolve with the finished job. Never throws: errors come back on the job. */
export async function auditWithProgress(container, body) {
  const p = progressPanel();
  clear(container).append(p.el);
  try {
    const job = await api.runAudit(body, p.update);
    if (job.status === "error") container.append(errorBox(job.error || "The audit failed.", job.hint));
    return job;
  } catch (e) {
    container.append(errorBox(e.message || "The audit could not start."));
    return { status: "error", error: e.message };
  }
}

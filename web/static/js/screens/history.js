// Every saved run, newest first. Nothing here is computed: it lists what the pipeline wrote.
import { h, clear, when, OUTCOME_WORD } from "../util.js";
import * as api from "../api.js";

const VERDICT = { in_kilter: "In kilter", out_of_kilter: "Out of kilter", escalate: "Escalate" };
const VCLS = { in_kilter: "v-in", out_of_kilter: "v-out", escalate: "v-esc" };

export async function renderHistory(root) {
  clear(root);
  const page = h("div", { class: "page wrap" });
  root.append(page);
  const runs = await api.runs();
  page.append(h("div", { class: "stack", style: "margin-bottom:28px" },
    h("div", { class: "t-label" }, "History"),
    h("h1", { class: "t-page" }, "Saved runs"),
    h("p", { class: "t-lead" }, "Each row is a run record on this machine. Open one to see the finding, the evidence and the digest.")));
  if (!runs.length) { page.append(h("p", { class: "note" }, "Nothing has been audited yet. Audit a script and it will appear here.")); return; }
  page.append(h("div", { style: "overflow-x:auto" }, h("table", { class: "tbl" },
    h("caption", { class: "sr" }, "Saved audit runs"),
    h("thead", {}, h("tr", {}, ["Script", "Arm", "Verdict", "Held at", "Ground truth", "When", ""].map((t) => h("th", { scope: "col" }, t)))),
    h("tbody", {}, runs.map((r) => h("tr", {},
      h("td", {}, h("div", { class: "id" }, r.script), h("div", { class: "sub" }, r.label)),
      h("td", {}, h("span", { class: "t-mono" }, r.arm)),
      h("td", {}, h("span", { class: `out ${VCLS[r.verdict]}`, style: "font-weight:900" }, VERDICT[r.verdict])),
      h("td", {}, h("span", { class: "t-mono" }, r.held_at ? r.held_at.toUpperCase() : "none")),
      h("td", {}, r.outcome ? h("span", { class: `out out--${r.outcome}` }, OUTCOME_WORD[r.outcome]) : h("span", { class: "out out--none" }, "n/a")),
      h("td", {}, h("span", { class: "t-mono" }, when(r.surveyed_at))),
      h("td", {}, h("div", { class: "acts" }, h("a", { class: "btn btn--2 btn--sm k-btn", style: "text-decoration:none;display:inline-flex;align-items:center", href: `#/run/${r.run_id}` }, "Open")))))))));
}

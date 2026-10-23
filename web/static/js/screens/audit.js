// The front door: pick a script, pick an arm, audit. The mark scale idles unset until a verdict exists.
import { h, clear, segmented, when } from "../util.js";
import { MarkScale } from "../markscale.js";
import { auditWithProgress, errorBox } from "../progress.js";
import * as api from "../api.js";

export async function renderAudit(root, ctx) {
  clear(root);
  const ms = MarkScale({ height: 620 });
  ms.set({ mark: "unset" });
  const body = h("div", { class: "hero-body" });
  root.append(h("div", { class: "page wrap" }, h("div", { class: "hero" }, h("div", { class: "hero-scale" }, ms.el), body)));

  body.append(h("div", { class: "stack" },
    h("div", { class: "t-label" }, "Kilter"),
    h("h1", { class: "t-page" }, "Is this analysis in kilter?"),
    h("p", { class: "t-lead" }, "Give Kilter a modelling script. It checks the analysis for leakage, split problems, duplicated or scaffold-overlapping molecules, and unreported multiple comparisons, and says how deep it had to go to find the problem.")));

  if (api.getMode() === "static") return renderStatic(body, ctx);

  const session = api.getSession();
  const state = { source: "demo", arm: "A4", sample: null, name: "", text: "", sens: false };
  const form = h("div", { class: "stack" });
  const result = h("div", { class: "stack" });
  body.append(form, result);

  const samples = (await api.samples()).filter((s) => s.kind === "demo");
  state.sample = samples[0]?.id || null;

  function paint() {
    clear(form);
    form.append(
      h("div", { class: "field" }, h("span", { class: "t-label" }, "Script"),
        segmented([{ value: "demo", label: "Demo" }, { value: "upload", label: "Upload .py" }, { value: "paste", label: "Paste" }], state.source,
          (v) => { state.source = v; paint(); }, "Script source")),
      sourcePicker(),
      h("div", { class: "field" }, h("span", { class: "t-label" }, "Arm"),
        segmented([{ value: "A4", label: "Deterministic: T0 + T1" }, { value: "A3", label: "Full: T0 + T1 + T2" }], state.arm,
          (v) => { state.arm = v; paint(); }, "Arm"),
        h("p", { class: "note" }, state.arm === "A4"
          ? "Sound checks only. Static analysis and a runtime pass; no language model."
          : "Adds the critic, which reads the code and can raise queries the sound checks cannot. It is unsound, so it is reported separately.")),
      h("div", { class: "check" },
        h("input", { type: "checkbox", id: "sens", checked: state.sens, onchange: (e) => { state.sens = e.target.checked; } }),
        h("label", { for: "sens" }, "Also measure split sensitivity (re-runs the script under other split protocols; slow)")),
      h("p", { class: "note" }, h("b", {}, "Runs the script. "), "Tier 1 executes the script you give it, with no sandbox. Audit only scripts you would run yourself."),
      h("p", { class: "note" }, `Critic calls: ${session.mode}${session.mode === "replay" ? " (answers come from recordings; start the server with --live to call the model)" : ""}. Scripts up to ${session.max_source.toLocaleString()} characters.`),
      h("div", { class: "row" }, h("button", { type: "button", class: "btn k-btn", onclick: go }, "Audit")));
  }

  function sourcePicker() {
    if (state.source === "demo") {
      const sel = h("select", { class: "area", style: "min-height:0;height:48px", "aria-label": "Demo script", onchange: (e) => { state.sample = e.target.value; paint(); } },
        samples.map((s) => h("option", { value: s.id, selected: s.id === state.sample }, s.label)));
      const cur = samples.find((s) => s.id === state.sample);
      return h("div", { class: "field" }, sel, cur ? h("p", { class: "note" }, cur.description) : null);
    }
    if (state.source === "upload") {
      const input = h("input", { type: "file", accept: ".py,text/x-python,text/plain", onchange: async (e) => {
        const f = e.target.files[0]; if (!f) return;
        state.name = f.name; state.text = await f.text(); label.textContent = `${f.name}, ${state.text.length.toLocaleString()} characters`;
      } });
      const label = h("span", { class: "note", role: "status" }, state.name ? `${state.name}, ${state.text.length.toLocaleString()} characters` : "No file chosen");
      return h("div", { class: "field" }, h("label", { class: "file k-btn" }, "Choose a .py file", input), label);
    }
    return h("div", { class: "field" },
      h("input", { class: "area", style: "min-height:0;height:48px", placeholder: "file name, e.g. analysis.py", "aria-label": "File name", value: state.name,
        oninput: (e) => { state.name = e.target.value; } }),
      h("textarea", { class: "area", "aria-label": "Script text", spellcheck: "false", placeholder: "Paste a Python script here",
        oninput: (e) => { state.text = e.target.value; } }, state.text));
  }

  async function go() {
    let req = { arm: state.arm, sensitivity: state.sens };
    if (state.source === "demo") req.sample_id = state.sample;
    else {
      const name = (state.name || (state.source === "paste" ? "pasted.py" : "")).trim();
      if (!state.text.trim()) { clear(result).append(errorBox("There is no script to audit.", "Choose a file or paste the script text.")); return; }
      req = { ...req, name: name.endsWith(".py") ? name : `${name}.py`, source: state.text };
    }
    ms.set({ mark: "unset" });
    const job = await auditWithProgress(result, req);
    if (job.status === "done") ctx.go(`#/run/${job.run_id}`);
  }

  paint();
}

// No server: show the saved runs of the demos, which is what a screenshot or an offline copy can honestly offer.
async function renderStatic(body, ctx) {
  const runs = await api.runs();
  if (!runs.length) {
    body.append(errorBox("No server is running and no saved runs were found.", "Start the server with: python web/server.py. Or build the offline data with: python web/build_fixtures.py."));
    return;
  }
  body.append(h("p", { class: "note" }, "Offline view: these are saved runs. To audit a script, start the local server: python web/server.py."),
    h("div", { class: "stack" }, runs.map((r) => h("a", { class: "btn btn--2 k-btn", style: "text-decoration:none;display:flex;justify-content:space-between;gap:16px", href: `#/run/${r.run_id}` },
      h("span", {}, `${r.label} (${r.arm})`), h("span", { class: "t-mono" }, `${r.verdict.replace(/_/g, " ")} . ${when(r.surveyed_at)}`)))));
}

// Hash router and shell. Routes: #/ audit, #/samples, #/fleet, #/history, #/run/<id>.
import { h, clear } from "./util.js";
import * as api from "./api.js";
import { renderAudit } from "./screens/audit.js";
import { renderSamples } from "./screens/samples.js";
import { renderFleet } from "./screens/fleet.js";
import { renderHistory } from "./screens/history.js";
import { renderRun } from "./screens/verdict.js";
import { errorBox } from "./progress.js";

const main = document.getElementById("main");
const chips = document.getElementById("chips");
let seq = 0;   // a slow screen must not paint over a newer one

const ctx = {
  go: (hash) => { location.hash = hash; },
  // The latest run of each arm for the same sample, so the verdict screen can offer the arm toggle.
  async siblings(view) {
    const id = view.sample && view.sample.id;
    if (!id) return null;
    const runs = await api.runs();
    const pick = (arm) => runs.filter((r) => r.sample_id === id && r.arm === arm).sort((a, b) => (a.surveyed_at < b.surveyed_at ? 1 : -1))[0];
    return { A4: pick("A4"), A3: pick("A3") };
  },
};

function paintChips(info) {
  clear(chips);
  if (info.mode === "static") { chips.append(h("span", { class: "chip" }, "offline: saved runs")); return; }
  const s = info.session;
  chips.append(h("span", { class: "chip" }, `critic: ${s.mode}`));
  if (s.mode !== "replay") chips.append(h("span", { class: "chip chip--warn" }, "live calls"));
  chips.append(h("span", { class: "chip" }, "127.0.0.1"));
}

function paintNav(route) {
  const cur = route.startsWith("run") ? "" : route || "audit";
  document.querySelectorAll(".nav a").forEach((a) => {
    if (a.dataset.r === cur) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
}

async function route() {
  const my = ++seq;
  const hash = location.hash.replace(/^#\/?/, "");
  const [name, arg] = hash.split("/");
  paintNav(name || "audit");
  document.title = "Kilter";
  try {
    if (name === "samples") await renderSamples(main, ctx);
    else if (name === "fleet") await renderFleet(main, ctx);
    else if (name === "history") await renderHistory(main);
    else if (name === "run" && arg) {
      const saved = await api.getRun(decodeURIComponent(arg));
      if (my !== seq) return;
      await renderRun(main, saved, ctx);
    } else await renderAudit(main, ctx);
  } catch (e) {
    if (my !== seq) return;
    clear(main).append(h("div", { class: "page wrap" }, errorBox(e.message || "That screen could not be drawn.", "Go back to the audit screen and try again.")));
  }
  if (my === seq) { window.scrollTo(0, 0); }
}

const info = await api.init();
paintChips({ mode: info.mode, session: info.session });
window.addEventListener("hashchange", route);
route();

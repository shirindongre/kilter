// Two modes, chosen once at start-up:
//   "api"    the local server answers /api/session: live audits, history, uploads.
//   "static" no server: read data/index.json written by web/build_fixtures.py (the three demos, both arms).

let mode = "api";
let token = null;
let session = null;
let staticIndex = null;

export async function init() {
  try {
    const r = await fetch("/api/session", { cache: "no-store" });
    if (!r.ok) throw new Error("no server");
    session = await r.json();
    token = session.token;
    mode = "api";
  } catch {
    mode = "static";
    try {
      const r = await fetch("data/index.json", { cache: "no-store" });
      staticIndex = r.ok ? await r.json() : null;
    } catch { staticIndex = null; }
  }
  return { mode, session, hasStatic: !!staticIndex };
}

export const getMode = () => mode;
export const getSession = () => session;

async function call(path, opts = {}) {
  const r = await fetch(path, {
    cache: "no-store", ...opts,
    headers: { "X-Kilter-Token": token, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (!r.ok) {
    let msg = null;
    try { const j = await r.json(); msg = j.detail || j.error; } catch { /* not json */ }
    throw new Error(typeof msg === "string" ? msg : `The request failed (${r.status}).`);
  }
  return r.json();
}

export async function samples() {
  return mode === "api" ? call("/api/samples") : (staticIndex ? staticIndex.samples : []);
}

/** The stored evaluation, for the fleet screen. Offline copy: data/fleet.json if build_fixtures.py found results/. */
export async function fleet() {
  if (mode === "api") return call("/api/fleet");
  try {
    const r = await fetch("data/fleet.json", { cache: "no-store" });
    return r.ok ? r.json() : { available: false, reason: "This offline copy was built without the results folder." };
  } catch { return { available: false, reason: "This offline copy was built without the results folder." }; }
}

export async function runs() {
  return mode === "api" ? call("/api/runs") : (staticIndex ? staticIndex.runs : []);
}

export async function getRun(id) {
  if (mode === "api") return call(`/api/runs/${encodeURIComponent(id)}`);
  const r = await fetch(`data/runs/${encodeURIComponent(id)}.json`, { cache: "no-store" });
  if (!r.ok) throw new Error("That run is not in the static data.");
  return r.json();
}

export const startAudit = (body) => call("/api/audit", { method: "POST", body: JSON.stringify(body) });
export const job = (id) => call(`/api/jobs/${encodeURIComponent(id)}`);
export const verify = (id) => call(`/api/runs/${encodeURIComponent(id)}/verify`, { method: "POST" });

/** Start an audit and poll until it finishes. onUpdate receives the job (stages, status) on every poll. */
export async function runAudit(body, onUpdate) {
  let j = await startAudit(body);
  onUpdate?.(j);
  while (j.status === "queued" || j.status === "running") {
    await new Promise((res) => setTimeout(res, 500));
    j = await job(j.id);
    onUpdate?.(j);
  }
  return j;
}

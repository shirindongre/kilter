// Tiny DOM helpers. Everything the audited script or the backend sends is rendered with textContent only,
// never innerHTML: an uploaded script is untrusted text (the server also sets a strict CSP as a second layer).

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  append(el, kids);
  return el;
}

export function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return el;
}

export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

export const TIER = { t0: "T0 static", t1: "T1 runtime", t2: "T2 critic" };
export const tierChip = (t) => h("span", { class: `tier tier--${t}` }, TIER[t] || t);

export const VERDICT_CLASS = { in_kilter: "v-in", out_of_kilter: "v-out", escalate: "v-esc" };
export const RESULT_WORD = {
  clear: "Clear", fired: "Fired", not_applicable: "Not applicable", could_not_run: "Could not run",
  no_objection: "No objection", query: "Query",
};
export const OUTCOME_WORD = {
  caught: "Caught", missed: "Missed", false_alarm: "False alarm", clean_ok: "Clean, as planted",
  wrong_class: "Wrong class", escalated: "Escalated",
};

export function announce(msg) {
  const el = document.getElementById("announce");
  if (!el) return;
  el.textContent = "";
  setTimeout(() => { el.textContent = msg; }, 20);   // re-set so identical consecutive messages still read out
}

export function when(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export const n0 = (n) => (n == null ? null : Number(n).toLocaleString("en-US"));

export function slot(name) { return h("span", { class: "slot" }, `[${name}]`); }

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}

export function download(filename, text, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = h("a", { href: url, download: filename });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function segmented(options, value, onChange, label) {
  const wrap = h("div", { class: "seg", role: "group", "aria-label": label });
  const paint = () => wrap.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === value)));
  for (const o of options) {
    wrap.append(h("button", {
      type: "button", class: "k-seg", "data-v": o.value, disabled: o.disabled, title: o.title,
      onclick: () => { if (o.disabled) return; value = o.value; paint(); onChange(value); },
    }, o.label));
  }
  paint();
  return wrap;
}

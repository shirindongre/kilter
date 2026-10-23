// The signature component (spec section 6.1). Depth equals unsoundness: a mark high on the hull was caught by a
// sound check; a mark low on the hull was caught only by the critic; no mark means clean; a dashed mark in the
// hatch means the stack could not settle it (escalate).
//
// Transform and opacity only. The water fills on scaleY from the top; the mark travels on translateY.
import { h, TIER } from "./util.js";

const D620 = { t0: 150, t1: 262, t2: 404, esc: 546 };
const D300 = { t0: 72, t1: 132, t2: 192, esc: 262 };

function geometry(height) {
  if (height === 620) return { d: D620, clear: 10 };
  if (height === 300) return { d: D300, clear: 6 };
  const k = height / 620;
  return { d: Object.fromEntries(Object.entries(D620).map(([a, b]) => [a, Math.round(b * k)])), clear: Math.round(10 * k) };
}

const short = (id) => (id || "").replace(/^T\d\./, "");

function describe(s) {
  switch (s.mark) {
    case "t0": case "t1": case "t2": {
      const by = s.heldCheck ? `, by the check ${short(s.heldCheck)}` : "";
      const tail = s.mark === "t2" ? " Only the critic held it; no sound check did." : " A sound check held it.";
      return `Mark scale. Out of kilter. The mark is held at ${TIER[s.mark]}${by}.${tail}`;
    }
    case "clear": return "Mark scale. In kilter. No check objected, so the mark stays at the top of the hull.";
    case "esc": return `Mark scale. Escalate. The mark could not be set: ${TIER[s.unresolved] || "a tier"} could not run.`;
    default: return "Mark scale. Not yet surveyed.";
  }
}

export function MarkScale({ height = 620 } = {}) {
  const g = geometry(height);
  const sc = height / 620;
  const root = h("div", { class: "ms", role: "img", style: `--h:${height}px` });
  const water = h("div", { class: "ms-water k-glide" });
  const hatch = h("div", { class: "ms-hatch" });
  const plate = h("div", { class: "ms-plate", "aria-hidden": "true" }, water, hatch);
  const nums = {};
  for (const key of ["t0", "t1", "t2", "esc"]) {
    plate.append(h("div", { class: "ms-tick", style: `top:${g.d[key]}px` }));
    nums[key] = h("div", { class: `ms-num ms-num--${key}`, style: `top:${g.d[key] - 21}px`, "aria-hidden": "true" },
      key === "esc" ? "ESC" : key.toUpperCase(), h("small", {}, ""));
  }
  const mark = h("div", { class: "ms-mark k-glide", "aria-hidden": "true" });
  const callB = h("b", {}, "");
  const callS = h("span", {}, "");
  const call = h("div", { class: "ms-call k-glide", "aria-hidden": "true" }, callB, callS);
  root.append(nums.t0, nums.t1, nums.t2, nums.esc, plate, mark, call);

  const subs = { t0: "sound", t1: "sound", t2: "unsound" };
  const animated = [[plate, "k-plate"], [water, "k-flood"], [mark, "k-settle k-fail k-fade"], [hatch, "k-hatch"], [call, "k-fade"]];

  function reset() {
    for (const [el, cls] of animated) el.classList.remove(...cls.split(" "));
    call.style.animationDelay = "";
    void root.offsetWidth;   // restart animations when the same element is re-armed
  }

  /** state: { mark: t0|t1|t2|esc|clear|unset, heldCheck, unresolved, blockers, checksRan }; opts.animate plays the screen's one moment. */
  function set(s, opts = {}) {
    const m = s.mark || "unset";
    root.dataset.mark = m;
    let y = g.clear, fill = 0, yLine = g.d.t1;
    let top = "100%";
    if (m === "t0" || m === "t1" || m === "t2") { y = g.d[m]; fill = y / height; }
    else if (m === "esc") {
      yLine = g.d[s.unresolved || "t1"]; y = yLine + Math.round(50 * sc); fill = yLine / height; top = `${yLine}px`;
    }
    const st = root.style;
    st.setProperty("--y", `${y}px`);
    st.setProperty("--y-line", `${yLine}px`);
    st.setProperty("--y-start", `${g.clear}px`);
    st.setProperty("--fill", String(fill));
    st.setProperty("--hatch-top", top);
    hatch.style.display = m === "esc" ? "" : "none";

    for (const k of ["t0", "t1", "t2"]) nums[k].querySelector("small").textContent = subs[k];
    nums.esc.querySelector("small").textContent = m === "esc" ? `${s.blockers ?? 1} open` : "none";

    if (m === "t0" || m === "t1" || m === "t2") {
      callB.textContent = "HELD HERE"; callS.textContent = s.heldCheck ? short(s.heldCheck) : TIER[m];
    } else if (m === "clear") {
      callB.textContent = "CLEAR"; callS.textContent = `${s.checksRan ?? 0} checks ran`;
    } else if (m === "esc") {
      callB.textContent = "NOT HELD"; callS.textContent = `${TIER[s.unresolved] || "a tier"} could not run`;
    }
    root.setAttribute("aria-label", describe({ ...s, mark: m }));

    reset();
    if (!opts.animate || m === "unset") return;
    plate.classList.add("k-plate");
    if (m === "clear") {
      mark.classList.add("k-fade");
    } else if (m === "esc") {
      water.classList.add("k-flood"); mark.classList.add("k-fail"); hatch.classList.add("k-hatch");
    } else {
      water.classList.add("k-flood"); mark.classList.add("k-settle");
    }
    call.classList.add("k-fade"); call.style.animationDelay = m === "esc" ? "1400ms" : "1000ms";
    // Hand control back to the transitions once the entrance has played, so later changes glide.
    for (const [el, cls] of animated) {
      el.addEventListener("animationend", () => el.classList.remove(...cls.split(" ")), { once: true });
    }
  }

  return { el: root, set };
}

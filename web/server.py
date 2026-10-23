"""Local server for the Kilter web UI (FRONTEND-SPEC, AIMS D-024).

    python web/server.py              # replay mode: recorded critic responses only, no network, no API key
    python web/server.py --live       # same, but a critic response that was never recorded may call the API

SECURITY. Auditing runs the audited script on this computer (T1 and the artifact step execute it) and there is no
sandbox. So the server (1) binds to 127.0.0.1 only, (2) rejects any request whose Host is not localhost (DNS
rebinding), (3) requires a per-process token in a custom header that only this origin's JavaScript can read, which
also blocks cross-site form posts, and (4) serves a strict Content-Security-Policy. Do not expose it to a network.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    sys.exit('The web UI needs its optional dependencies:  pip install -e ".[web]"')

import fleet
import registry
import runner
from kilter.core import record as rec

# Windows can map .js to text/plain through the registry, which breaks <script type="module">.
for ext, mime in ((".js", "text/javascript"), (".css", "text/css"), (".woff2", "font/woff2"), (".json", "application/json")):
    mimetypes.add_type(mime, ext)

STATIC = HERE / "static"
WORK = HERE / "work"
RUNS = HERE / "runs"
TOKEN = secrets.token_urlsafe(24)
MAX_SOURCE = 200_000
NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,80}\.py$")
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
pool = ThreadPoolExecutor(max_workers=1)   # one audit at a time: T1 patches the audited module's hooks
jobs: dict[str, "Job"] = {}
samples: dict[str, dict] = {}
run_index: dict[str, dict] = {}
state = {"live": False, "fleet": None, "fleet_reason": "results/ was not found on this machine."}


class Job:
    def __init__(self, arm: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.status = "queued"
        self.stages = [{"id": s, "label": runner.STAGE_LABEL[s], "status": "waiting"} for s in runner.stages_for(arm)]
        self.run_id: str | None = None
        self.error: str | None = None
        self.hint: str | None = None

    def stage(self, sid: str, status: str) -> None:
        for s in self.stages:
            if s["id"] == sid:
                s["status"] = status

    def public(self) -> dict:
        return {"id": self.id, "status": self.status, "stages": self.stages, "run_id": self.run_id,
                "error": self.error, "hint": self.hint}


# --- saved runs ----------------------------------------------------------------------------------

def summarize(saved: dict) -> dict:
    v = saved["view"]
    sample = v.get("sample") or {}
    return {"run_id": v["run_id"], "sample_id": sample.get("id"), "label": sample.get("label") or v["subject"]["path"],
            "script": v["subject"]["path"], "arm": v["arm"], "verdict": v["verdict"], "held_at": v["held_at"],
            "surveyed_at": v["surveyed_at"], "outcome": (sample.get("truth") or {}).get("outcome"),
            "planted_class": (sample.get("truth") or {}).get("planted_class")}


def load_runs() -> None:
    RUNS.mkdir(exist_ok=True)
    for f in RUNS.glob("*.json"):
        try:
            saved = json.loads(f.read_text(encoding="utf-8"))
            run_index[saved["view"]["run_id"]] = summarize(saved)
        except (OSError, ValueError, KeyError):
            continue   # a half-written or foreign file must not stop the server


def save_run(saved: dict) -> None:
    RUNS.mkdir(exist_ok=True)
    rid = saved["view"]["run_id"]
    (RUNS / f"{rid}.json").write_text(json.dumps(saved, default=str), encoding="utf-8")
    run_index[rid] = summarize(saved)


def latest(sample_id: str, arm: str) -> dict | None:
    mine = [r for r in run_index.values() if r["sample_id"] == sample_id and r["arm"] == arm]
    return max(mine, key=lambda r: r["surveyed_at"]) if mine else None


# --- middleware ----------------------------------------------------------------------------------

@app.middleware("http")
async def guard(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        if request.headers.get("host", "").rsplit(":", 1)[0] not in ("127.0.0.1", "localhost"):
            return JSONResponse({"error": "bad host"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "cross-site request refused"}, status_code=403)
        if path != "/api/session" and request.headers.get("x-kilter-token") != TOKEN:
            return JSONResponse({"error": "missing or wrong token"}, status_code=403)
    resp = await call_next(request)
    resp.headers.update({"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
                         "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
    return resp


# --- API -----------------------------------------------------------------------------------------

@app.get("/api/session")
def session() -> dict:
    from kilter.llm import llm_mode
    return {"token": TOKEN, "mode": llm_mode(), "live": state["live"], "max_source": MAX_SOURCE}


@app.get("/api/samples")
def list_samples() -> list[dict]:
    out = []
    for s in samples.values():
        runs = {arm: latest(s["id"], arm) for arm in ("A4", "A3")}
        out.append(registry.public(s) | {"artifact_ready": s["_ready"], "runs": runs})
    return out


class AuditBody(BaseModel):
    sample_id: str | None = None
    name: str | None = None
    source: str | None = None
    arm: str = "A4"
    sensitivity: bool = False


@app.post("/api/audit")
def start_audit(body: AuditBody) -> dict:
    from kilter.llm import llm_mode

    if body.arm not in ("A3", "A4"):
        raise HTTPException(400, "arm must be A3 or A4")
    if body.sample_id:
        sample = samples.get(body.sample_id)
        if sample is None:
            raise HTTPException(404, "unknown sample")
        path = sample["path"]
    else:
        if not body.source or len(body.source) > MAX_SOURCE:
            raise HTTPException(400, f"send the script text, at most {MAX_SOURCE:,} characters")
        name = body.name or "pasted.py"
        if not NAME_RE.match(name):
            raise HTTPException(400, "file name must be letters, digits, _ . - and end in .py")
        if body.arm == "A3" and llm_mode() == "replay":
            raise HTTPException(400, "Replay mode has no recorded critic response for a script of your own. "
                                     "Audit with the deterministic arm, or start the server with --live.")
        digest = sha256(body.source.encode()).hexdigest()[:8]
        folder = WORK / "uploads" / digest
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_text(body.source, encoding="utf-8")
        sample = {"id": f"upload-{digest}", "kind": "upload", "label": name, "group": "upload", "base": None,
                  "description": "Uploaded script", "planted_class": None, "site_line": None}
    job = Job(body.arm)
    jobs[job.id] = job
    pool.submit(execute, job, path, sample, body.arm, body.sensitivity)
    return job.public()


def execute(job: Job, path: Path, sample: dict, arm: str, sensitivity: bool) -> None:
    from kilter.llm import FixtureMissing

    job.status = "running"
    try:
        saved = runner.run_audit(path, arm, registry.public(sample), sensitivity=sensitivity, on_stage=job.stage)
        save_run(saved)
        job.run_id, job.status = saved["view"]["run_id"], "done"
    except FixtureMissing:
        job.error, job.status = "No recorded critic response exists for this script.", "error"
        job.hint = "Audit with the deterministic arm, or start the server with --live and a GOOGLE_API_KEY."
    except Exception as e:  # noqa: BLE001 - surface any pipeline failure to the person, not a stack trace
        job.error, job.status = f"{type(e).__name__}: {str(e)[:400]}", "error"
        if "GOOGLE_API_KEY" in str(e):
            job.hint = "Live mode needs GOOGLE_API_KEY in .env (see .env.example). Or audit with the deterministic arm, which needs no key."
        elif "load_dataset" in str(e) or "HF" in str(e) or "huggingface" in str(e).lower():
            job.hint = "The datasets may not be cached. Run: python -c \"from kilter.data import load_dataset as l; l('bace'); l('bbbp')\""


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job.public()


@app.get("/api/runs")
def list_runs() -> list[dict]:
    return sorted(run_index.values(), key=lambda r: r["surveyed_at"], reverse=True)


@app.get("/api/fleet")
def get_fleet() -> dict:
    f = state["fleet"]
    return f.payload if f else {"available": False, "reason": state["fleet_reason"]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    if not re.fullmatch(r"[\w.\-]+", run_id):
        raise HTTPException(404, "unknown run")
    if run_id in run_index:
        return json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))
    f = state["fleet"]
    saved = f.saved(run_id) if f else None   # a record the evaluation stored, shown without re-running anything
    if saved is None:
        raise HTTPException(404, "unknown run")
    return saved


@app.post("/api/runs/{run_id}/verify")
def verify_run(run_id: str) -> dict:
    saved = get_run(run_id)
    return {"ok": rec.verify(saved["record"]), "record_sha256": saved["record"].get("record_sha256")}


# --- startup -------------------------------------------------------------------------------------

def build_samples() -> None:
    for s in [*registry.demo_samples(), *registry.variant_samples(WORK / "variants")]:
        s["_ready"] = registry.artifact_ready(s["path"])
        samples[s["id"]] = s


def main() -> None:
    ap = argparse.ArgumentParser(description="Kilter web UI (local only)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--live", action="store_true", help="allow a live critic call when no response was recorded")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    state["live"] = args.live
    os.environ["KILTER_LLM_MODE"] = "record" if args.live else "replay"   # record = read-through cache, never overwrites
    print("Preparing samples (demos + 80 evaluation variants)...", flush=True)
    build_samples()
    load_runs()
    try:
        state["fleet"] = fleet.load()
    except Exception as e:  # noqa: BLE001 - a bad results folder must not stop the rest of the UI
        state["fleet_reason"] = f"results/ could not be read: {type(e).__name__}: {str(e)[:200]}"
    print("Fleet view:", "stored evaluation loaded" if state["fleet"] else state["fleet_reason"], flush=True)
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Kilter UI: {url}   mode: {os.environ['KILTER_LLM_MODE']}   (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

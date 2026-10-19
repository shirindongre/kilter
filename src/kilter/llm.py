"""Thin LLM client for the T2 tier and the A1 baseline (AD-3, AD-6, AD-10).

One provider is pinned for all reported results (config/providers.yaml). Every call returns the token counts,
latency and the model version the API *reports* (not the one requested: `gemini-3.5-flash` silently serves
`gemini-3.6-flash`, AIMS D-012). Hidden "thinking" tokens are billed output, so they are counted separately
and included in `output_tokens_billed`. Never used on the demo path (section 5.7): the demo replays fixtures.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "providers.yaml"
FIXTURE_DIR = ROOT / "fixtures" / "llm"
_RETRY_RE = re.compile(r"retry in ([\d.]+)s", re.I)
MAX_RETRIES = 5
RETRYABLE = {429, 500, 503, 504}


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_requested: str
    model_reported: str
    input_tokens: int
    output_tokens: int        # visible output
    thinking_tokens: int      # hidden reasoning, billed as output
    seconds: float
    retries: int
    cached: bool = False      # True: served from a recorded fixture; token/second figures are those of the original call

    @property
    def output_tokens_billed(self) -> int:
        return self.output_tokens + self.thinking_tokens


class FixtureMissing(RuntimeError):
    """replay mode was asked for a response that was never recorded."""


def llm_mode() -> str:
    """live: always call the API | record (default): read-through cache, writing new responses | replay: never call."""
    mode = os.environ.get("KILTER_LLM_MODE", "record")
    if mode not in {"live", "record", "replay"}:
        raise ValueError(f"KILTER_LLM_MODE must be live, record or replay, got {mode!r}")
    return mode


def fixture_key(model: str, system: str | None, prompt: str, params: dict) -> str:
    blob = json.dumps({"model": model, "system": system, "prompt": prompt, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


_last_live_call = 0.0


def _throttle(model: str) -> None:
    """Space live calls to the verified requests-per-minute limit instead of spending calls on 429s (AD-6)."""
    global _last_live_call
    rpm = (load_config()["providers"]["google_ai_studio"]["limits"].get(model) or {}).get("rpm")
    if rpm:
        wait = _last_live_call + 60.0 / rpm + 0.5 - time.time()
        if wait > 0:
            time.sleep(wait)
    _last_live_call = time.time()


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def retry_delay(message: str, default: float = 15.0) -> float:
    """Seconds the server asked us to wait ("Please retry in 41.9s"), plus a small margin."""
    m = _RETRY_RE.search(message)
    return (float(m.group(1)) if m else default) + 1.0


def _client():
    from dotenv import load_dotenv
    from google import genai

    load_dotenv(ROOT / ".env")  # explicit path: independent of the current directory
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set (put it in .env, see .env.example)")
    return genai.Client(api_key=key)


def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_output_tokens: int = 1024,
    temperature: float = 0.0,
    thinking_level: str = "minimal",
    response_schema=None,
    history: list[tuple[str, str]] | None = None,
) -> LLMResponse:
    """`history` is prior (user_text, model_text) turns, for same-conversation follow-ups (the A1 self-critique arm)."""
    from google.genai import errors, types

    model = model or load_config()["pinned_for_reported_results"]["model"]
    if not model:
        raise RuntimeError("no model pinned in config/providers.yaml (pinned_for_reported_results.model)")
    schema_id = response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else repr(response_schema)
    params = {"t": temperature, "max": max_output_tokens, "think": thinking_level, "schema": schema_id}
    if history:
        params["history"] = history  # only when present, so keys of single-turn fixtures are unchanged
    key = fixture_key(model, system, prompt, params)
    fixture = FIXTURE_DIR / f"{key}.json"
    mode = llm_mode()
    if mode != "live" and fixture.exists():
        return LLMResponse(**{**json.loads(fixture.read_text(encoding="utf-8")), "cached": True})
    if mode == "replay":
        raise FixtureMissing(f"no recorded response for key {key} (model {model}); record it with KILTER_LLM_MODE=record")
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        response_mime_type="application/json" if response_schema else None,
        response_schema=response_schema,
    )
    contents = prompt
    if history:
        contents = [types.Content(role=role, parts=[types.Part(text=text)])
                    for u, m in history for role, text in (("user", u), ("model", m))]
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
    client = _client()
    t0, retries = time.time(), 0
    while True:
        _throttle(model)
        try:
            r = client.models.generate_content(model=model, contents=contents, config=cfg)
            break
        except (errors.ClientError, errors.ServerError) as e:
            code = getattr(e, "code", None)
            if code not in RETRYABLE or retries >= MAX_RETRIES:
                raise
            retries += 1
            # 429 carries the server's own wait hint; 5xx (e.g. 503 "high demand") gets exponential backoff
            time.sleep(retry_delay(str(e)) if code == 429 else 10.0 * 2 ** (retries - 1))
    u = r.usage_metadata
    resp = LLMResponse(
        text=r.text or "",
        model_requested=model,
        model_reported=r.model_version or model,
        input_tokens=u.prompt_token_count or 0,
        output_tokens=u.candidates_token_count or 0,
        thinking_tokens=getattr(u, "thoughts_token_count", None) or 0,
        seconds=time.time() - t0,
        retries=retries,
    )
    if mode == "record":
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps({k: v for k, v in asdict(resp).items() if k != "cached"}, indent=2), encoding="utf-8")
    return resp

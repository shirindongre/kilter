import os

import pytest

from kilter.llm import LLMResponse, generate, load_config, retry_delay


def test_retry_delay_follows_server_hint():
    assert retry_delay("Quota exceeded ... Please retry in 41.96330974s.") == pytest.approx(42.96, abs=0.01)
    assert retry_delay("no hint here", default=10) == 11.0


def test_billed_output_includes_hidden_thinking_tokens():
    r = LLMResponse("t", "m", "m", input_tokens=9, output_tokens=1, thinking_tokens=15, seconds=1.0, retries=0)
    assert r.output_tokens_billed == 16


def test_config_pins_explicit_model_not_an_alias():
    pinned = load_config()["pinned_for_reported_results"]
    assert pinned["provider"] == "google_ai_studio"
    assert "latest" not in pinned["model"] and pinned["model"] != "gemini-3.5-flash"  # D-012


@pytest.mark.live
def test_provider_smoke_hello(monkeypatch):
    """P0.3: one real call. Skipped without a key. Never part of the demo path."""
    from dotenv import load_dotenv

    from kilter.llm import ROOT

    monkeypatch.setenv("KILTER_LLM_MODE", "live")  # a smoke test must reach the provider, never a fixture

    load_dotenv(ROOT / ".env")
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    r = generate("Reply with exactly: kilter-ok", max_output_tokens=32)
    assert "kilter-ok" in r.text
    assert r.model_reported == load_config()["pinned_for_reported_results"]["model"]  # alias redirect would fail this
    assert r.input_tokens > 0 and r.seconds > 0

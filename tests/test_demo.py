"""Blueprint 5.6 exit gate: `kilter demo` runs clean, offline, identically, three times in a row."""
import os
import subprocess
import sys


def run_demo() -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "GOOGLE_API_KEY"}
    env.update({"HF_HUB_OFFLINE": "1", "PYTHONWARNINGS": "ignore", "KILTER_LLM_MODE": "live"})  # demo must override "live"
    return subprocess.run([sys.executable, "-c", "from kilter.cli import app; app(['demo'])"],
                          capture_output=True, text=True, env=env, timeout=300)


def test_demo_is_offline_and_byte_identical_three_times():
    outs = [run_demo() for _ in range(3)]
    for r in outs:
        assert r.returncode == 0, r.stderr[-800:]
    assert outs[0].stdout == outs[1].stdout == outs[2].stdout
    text = outs[0].stdout
    assert text.count("IN KILTER") == 1 and text.count("OUT OF KILTER") == 2
    assert "caught by  T0 static" in text and "caught by  T2 critic" in text
    assert "replayed from recorded call" in text

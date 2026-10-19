from pathlib import Path

from typer.testing import CliRunner

from kilter.cli import app
from kilter.defects.variants import generate_variants, write_variants

runner = CliRunner()


def test_exit_codes_and_json(tmp_path):
    vs = {v.id: v for v in generate_variants()}
    write_variants([vs["bace-b0-clean"], vs["bace-b0-D4"]], tmp_path)

    clean = runner.invoke(app, ["audit", str(tmp_path / "bace-b0-clean.py"), "--data", "bace", "--no-llm"])
    assert clean.exit_code == 0 and "IN KILTER" in clean.output

    bad = runner.invoke(app, ["audit", str(tmp_path / "bace-b0-D4.py"), "--data", "bace", "--json", "--no-llm"])
    assert bad.exit_code == 1
    assert '"verdict": "OUT OF KILTER"' in bad.output and '"tier": "T0"' in bad.output


def test_unknown_dataset_is_rejected(tmp_path):
    f = Path(tmp_path / "x.py")
    f.write_text("x = 1\n", encoding="utf-8")
    assert runner.invoke(app, ["audit", str(f), "--data", "tox21", "--no-llm"]).exit_code == 2

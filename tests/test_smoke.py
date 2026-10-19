from typer.testing import CliRunner

import kilter
from kilter.cli import app


def test_version_flag():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert kilter.__version__ in result.output

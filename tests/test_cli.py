import pytest
from typer.testing import CliRunner

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# We import the main app. If dependencies like typer are missing,
# this import will fail immediately, thus failing the test suite.
try:
    from main import app
except ImportError as e:
    pytest.fail(f"Failed to import the CLI app due to missing dependencies: {e}")

runner = CliRunner()

def test_cli_help():
    """Test that the CLI loads and the help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "aitranscribe" in result.stdout
    assert "file" in result.stdout
    assert "record" in result.stdout

def test_cli_file_missing_arg():
    """Test that the file command requires an argument."""
    result = runner.invoke(app, ["file"])
    # Should fail because file_path is missing
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "Missing" in result.stdout or result.exit_code == 2

"""Test isolation: the suite must never read or write the developer's real config.

`main` derives CONFIG_DIR and its siblings as module-level constants at import
time, so every test used to exercise whatever lived in ``~/.config/aitranscribe``
— a stale prompts.toml there made 120 tests error out.

The paths are repointed in two places:

* at import time, before any test module resolves them via ``from main import …``
* before every test, because ``test_import_does_not_initialize_state`` reloads
  `main` and would otherwise recompute the real home paths
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import main

# mkdtemp (not tmp_path_factory): the patch has to be in place before collection.
TEST_CONFIG_DIR = Path(tempfile.mkdtemp(prefix="aitranscribe-test-config-"))

_ISOLATED_PATHS = {
    "CONFIG_DIR": TEST_CONFIG_DIR,
    "CONFIG_FILE": TEST_CONFIG_DIR / "config.toml",
    "LEGACY_CONFIG_FILE": TEST_CONFIG_DIR / "aitranscribe.conf",
    "PROMPTS_FILE": TEST_CONFIG_DIR / "prompts.sqlite",
    "PROMPTS_CONFIG": TEST_CONFIG_DIR / "prompts.toml",
}


def _isolate() -> None:
    for name, value in _ISOLATED_PATHS.items():
        setattr(main, name, value)


_isolate()
main.CONFIG = None
main.STT_ENDPOINT = None
main.LLM_ENDPOINT = None
main._initialized = False


@pytest.fixture(autouse=True)
def _reassert_config_isolation():
    """Undo any test that reloaded `main` or repointed the module paths itself."""
    _isolate()
    yield

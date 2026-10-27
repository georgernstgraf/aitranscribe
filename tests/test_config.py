"""Tests for the TOML configuration module (schema version 2)."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config

MINIMAL = """\
version = 2

[stt]
provider = "selfhosted-1"

[stt.providers.selfhosted-1]
base_url = "https://whisper.test/v1"
api_key = "stt-key"
model = "large-v3"
max_upload_s = 900
max_upload_mb = 100

[llm]
provider = "groq"

[llm.providers.groq]
api_key = "llm-key"
model = "openai/gpt-oss-120b"
"""


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def test_load_reads_both_scopes_independently(tmp_path):
    """The core requirement: self-hosted STT plus a cloud LLM, fully decoupled."""
    cfg = config.load(write(tmp_path / "config.toml", MINIMAL), environ={})

    assert cfg.stt.provider == "selfhosted-1"
    assert cfg.stt.active().base_url == "https://whisper.test/v1"
    assert cfg.stt.active().api_key == "stt-key"
    assert cfg.stt.active().model == "large-v3"
    assert cfg.stt.active().max_upload_s == 900

    assert cfg.llm.provider == "groq"
    assert cfg.llm.active().base_url == "https://api.groq.com/openai/v1"
    assert cfg.llm.active().api_key == "llm-key"
    assert cfg.llm.active().max_upload_s == 120


def test_load_applies_provider_defaults(tmp_path):
    """A known provider id needs no base_url/model of its own."""
    path = write(tmp_path / "config.toml", '[llm]\nprovider = "cortecs"\n')
    cfg = config.load(path, environ={})

    endpoint = cfg.llm.active()
    assert endpoint.base_url == "https://api.cortecs.ai/v1"
    assert endpoint.model == "qwen3.8-flash-next"
    assert not endpoint.has_key


def test_load_rejects_unknown_provider_with_available_list(tmp_path):
    path = write(
        tmp_path / "config.toml",
        '[stt]\nprovider = "selfhosted-2"\n\n'
        '[stt.providers.selfhosted-1]\nbase_url = "https://a/v1"\nmodel = "m"\n',
    )
    with pytest.raises(config.ConfigError) as exc:
        config.load(path, environ={})
    message = str(exc.value)
    assert "selfhosted-2" in message
    assert "selfhosted-1" in message


def test_load_requires_base_url_and_model_for_custom_profiles(tmp_path):
    path = write(tmp_path / "config.toml", '[stt]\nprovider = "mine"\n\n[stt.providers.mine]\nmodel = "m"\n')
    with pytest.raises(config.ConfigError, match="needs a base_url"):
        config.load(path, environ={})

    path = write(
        tmp_path / "config2.toml",
        '[stt]\nprovider = "mine"\n\n[stt.providers.mine]\nbase_url = "https://a/v1"\n',
    )
    with pytest.raises(config.ConfigError, match="needs a model"):
        config.load(path, environ={})


def test_load_rejects_newer_schema(tmp_path):
    path = write(tmp_path / "config.toml", "version = 99\n")
    with pytest.raises(config.ConfigError, match="schema version"):
        config.load(path, environ={})


def test_load_rejects_invalid_toml(tmp_path):
    path = write(tmp_path / "config.toml", "this is not = = toml")
    with pytest.raises(config.ConfigError, match="not valid TOML"):
        config.load(path, environ={})


def test_load_reports_missing_file(tmp_path):
    with pytest.raises(config.ConfigError, match="not found"):
        config.load(tmp_path / "nope.toml", environ={})


def test_load_rejects_non_positive_limits(tmp_path):
    path = write(
        tmp_path / "config.toml",
        '[stt]\nprovider = "mine"\n\n[stt.providers.mine]\n'
        'base_url = "https://a/v1"\nmodel = "m"\nmax_upload_s = 0\n',
    )
    with pytest.raises(config.ConfigError, match="max_upload_s"):
        config.load(path, environ={})


# --------------------------------------------------------------------------- #
# Key resolution
# --------------------------------------------------------------------------- #
def test_api_keys_accept_string_and_array(tmp_path):
    path = write(
        tmp_path / "config.toml",
        '[llm]\nprovider = "groq"\n\n[llm.providers.groq]\n'
        'api_keys = []\napi_key = ["a", "b"]\nmodel = "m"\n',
    )
    assert config.load(path, environ={}).llm.active().api_keys == ("a", "b")


def test_api_key_env_wins_over_file_and_keeps_order(tmp_path):
    path = write(
        tmp_path / "config.toml",
        '[stt]\nprovider = "mine"\n\n[stt.providers.mine]\n'
        'base_url = "https://a/v1"\nmodel = "m"\n'
        'api_key = "from-file"\napi_key_env = ["FIRST", "SECOND"]\n',
    )
    env = {"FIRST": "env-1", "SECOND": "env-2"}
    endpoint = config.load(path, environ=env).stt.active()

    assert endpoint.api_keys == ("env-1", "env-2", "from-file")
    assert endpoint.key_sources == ("env:FIRST", "env:SECOND", "file")
    assert endpoint.api_key == "env-1"


def test_missing_env_var_is_skipped(tmp_path):
    path = write(
        tmp_path / "config.toml",
        '[stt]\nprovider = "mine"\n\n[stt.providers.mine]\n'
        'base_url = "https://a/v1"\nmodel = "m"\napi_key_env = "ABSENT"\n',
    )
    endpoint = config.load(path, environ={}).stt.active()
    assert endpoint.api_keys == ()
    assert not endpoint.has_key


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
def test_set_value_preserves_comments_and_adds_tables(tmp_path):
    path = tmp_path / "config.toml"
    config.create_default(path)
    before = path.read_text()

    config.set_value(path, "ui", "output_width", value=120)
    config.set_value(path, "stt", "providers", "extra", "base_url", value="https://x/v1")

    after = path.read_text()
    assert "# aitranscribe configuration" in after
    assert "output_width = 120" in after
    assert "[stt.providers.extra]" in after
    assert len(after.splitlines()) >= len(before.splitlines())


def test_set_value_restricts_permissions(tmp_path):
    path = tmp_path / "config.toml"
    config.set_value(path, "ui", "output_width", value=80)
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_create_default_is_loadable_and_documents_selfhosted(tmp_path):
    path = tmp_path / "config.toml"
    config.create_default(path, prompts_file=tmp_path / "prompts.sqlite")

    text = path.read_text()
    assert "[stt.providers.selfhosted-1]" in text  # commented example
    assert "version = 2" in text

    cfg = config.load(path, environ={})
    assert cfg.stt.provider == "groq"
    assert cfg.llm.provider == "openrouter"
    assert cfg.prompts_file == str(tmp_path / "prompts.sqlite")


# --------------------------------------------------------------------------- #
# dotenv migration
# --------------------------------------------------------------------------- #
LEGACY = """\
OPENROUTER_API_KEY='sk-or-legacy'
OPENROUTER_LLM_MODEL='google/gemini-2.5-flash'

GROQ_API_KEY='gsk_legacy'
GROQ_STT_MODEL='whisper-large-v3'

LLM_PROVIDER="groq"
GROQ_LLM_MODEL='openai/gpt-oss-120b'

# Cohere (alternative provider)
# COHERE_API_KEY="your_cohere_api_key_here"
# COHERE_LLM_MODEL="command-r"

PRE_PROCESS_MODE=raw
LAST_FILE_PATH='/home/x/audio.m4a'
VERBOSE_ERRORS="false"
OUTPUT_WIDTH="120"

PROMPTS_FILE='/home/x/prompts.sqlite'
"""

DUPLICATE_BLOCKS = LEGACY + "\n# Cohere (alternative provider)\n# COHERE_API_KEY=\"x\"\n" * 40


def test_migrate_maps_values_and_collapses_duplicates(tmp_path):
    legacy = write(tmp_path / "aitranscribe.conf", DUPLICATE_BLOCKS)
    target = tmp_path / "config.toml"

    summary = config.migrate_dotenv(legacy, target)

    assert summary["stt_provider"] == "groq"
    assert summary["llm_provider"] == "groq"
    assert not legacy.exists()  # moved out of the way
    assert summary["backup"].exists()
    assert len(target.read_text().splitlines()) < 120  # duplicates gone

    cfg = config.load(target, environ={})
    assert cfg.stt.active().api_key == "gsk_legacy"
    assert cfg.stt.active().model == "whisper-large-v3"
    assert cfg.llm.active().api_key == "gsk_legacy"
    assert cfg.llm.active().model == "openai/gpt-oss-120b"
    assert cfg.llm.profiles["openrouter"].api_key == "sk-or-legacy"
    assert cfg.ui["pre_process_mode"] == "raw"
    assert cfg.ui["output_width"] == 120
    assert cfg.prompts_file == "/home/x/prompts.sqlite"


def test_migrate_keeps_stt_and_llm_keys_apart(tmp_path):
    """A legacy shared GROQ_API_KEY lands in both scopes, then can diverge."""
    legacy = write(tmp_path / "aitranscribe.conf", LEGACY)
    target = tmp_path / "config.toml"
    config.migrate_dotenv(legacy, target)

    # Operator switches STT to a self-hosted endpoint with its own key.
    config.set_value(target, "stt", "providers", "selfhosted-1", "base_url", value="https://w/v1")
    config.set_value(target, "stt", "providers", "selfhosted-1", "model", value="large-v3")
    config.set_value(target, "stt", "providers", "selfhosted-1", "api_key", value="whisper-key")
    config.set_value(target, "stt", "provider", value="selfhosted-1")

    cfg = config.load(target, environ={})
    assert cfg.stt.active().api_key == "whisper-key"
    assert cfg.llm.active().api_key == "gsk_legacy"


def test_migrate_drops_placeholders_and_normalizes_zai(tmp_path):
    legacy = write(
        tmp_path / "aitranscribe.conf",
        'GROQ_API_KEY="your_groq_api_key_here"\nLLM_PROVIDER="z.ai"\nZAI_API_KEY="z-key"\nZAI_LLM_MODEL="glm-5"\n',
    )
    target = tmp_path / "config.toml"
    config.migrate_dotenv(legacy, target)

    cfg = config.load(target, environ={})
    assert cfg.llm.provider == "zai"
    assert cfg.llm.active().api_key == "z-key"
    assert not cfg.stt.active().has_key


def test_migrate_is_skipped_when_toml_exists(tmp_path):
    legacy = write(tmp_path / "aitranscribe.conf", LEGACY)
    target = write(tmp_path / "config.toml", MINIMAL)

    assert config.migrate_if_needed(legacy, target) is None
    assert legacy.exists()


def test_migrate_returns_none_without_legacy_file(tmp_path):
    assert config.migrate_if_needed(tmp_path / "none.conf", tmp_path / "config.toml") is None


# --------------------------------------------------------------------------- #
# Display helpers
# --------------------------------------------------------------------------- #
def test_mask_key_keeps_edges():
    assert config.mask_key("whisper-sk-gregor-2026") == "whis…2026"
    assert config.mask_key("short") == "*****"
    assert config.mask_key(None) == "<missing>"


def test_normalize_provider_id_folds_legacy_alias():
    assert config.normalize_provider_id("z.ai") == "zai"
    assert config.normalize_provider_id("  GROQ ") == "groq"

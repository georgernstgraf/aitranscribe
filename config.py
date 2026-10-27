"""TOML configuration for aitranscribe (schema version 2).

Layout::

    version = 2

    [stt]
    provider = "selfhosted-1"        # selector only

    [stt.providers.selfhosted-1]     # complete endpoint description
    base_url      = "https://…/v1"
    api_key       = "…"              # string or array
    api_key_env   = "MY_KEY_VAR"     # string or array, resolved first
    model         = "large-v3"
    max_upload_s  = 900
    max_upload_mb = 100
    description   = "…"

    [llm]
    provider = "groq"

    [llm.providers.groq]
    base_url = "https://api.groq.com/openai/v1"
    api_key  = "…"
    model    = "openai/gpt-oss-120b"

    [ui]
    pre_process_mode = "raw"
    output_width     = 80
    verbose_errors   = false
    last_file_path   = ""

    [paths]
    prompts_file = "…"

Rule: a scope table holds the selector only; everything about an endpoint
(including its model) lives in its profile. One value, one place.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2

STT = "stt"
LLM = "llm"

DEFAULT_STT_PROVIDER = "groq"
DEFAULT_LLM_PROVIDER = "openrouter"

# Chunk ceilings. 120 s is the Groq ceiling: Groq mangles `text`/`segments`
# beyond ~122 s (see core.py and docs/ai/PITFALLS.md). Self-hosted endpoints
# have no such defect and only need to stay under the proxy timeout.
DEFAULT_MAX_UPLOAD_S = 120
DEFAULT_MAX_UPLOAD_MB = 25

# Built-in defaults so a known provider id works without a base_url line.
# A profile may override every field. Unknown ids must supply base_url/model.
PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "stt_model": "whisper-large-v3-turbo",
        "llm_model": "llama-3.3-70b-versatile",
        "max_upload_s": 120,
        "max_upload_mb": 25,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "stt_model": "whisper-1",
        "llm_model": "gpt-4o-mini",
        "max_upload_s": 1500,
        "max_upload_mb": 24,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "llm_model": "anthropic/claude-3-haiku",
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "llm_model": "command-r",
    },
    "zai": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "llm_model": "glm-5",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "llm_model": "gemini-2.0-flash",
    },
    "cortecs": {
        "base_url": "https://api.cortecs.ai/v1",
        "llm_model": "qwen3.8-flash-next",
    },
}

# Legacy provider ids that are not valid slugs.
PROVIDER_ALIASES = {"z.ai": "zai", "z-ai": "zai"}

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class ConfigError(RuntimeError):
    """Raised for invalid or incomplete configuration."""


@dataclass(frozen=True)
class Endpoint:
    """One way to reach one service for one purpose."""

    name: str
    scope: str
    base_url: str
    model: str
    api_keys: tuple[str, ...] = ()
    key_sources: tuple[str, ...] = ()
    max_upload_s: int = DEFAULT_MAX_UPLOAD_S
    max_upload_mb: int = DEFAULT_MAX_UPLOAD_MB
    description: str = ""

    @property
    def has_key(self) -> bool:
        return bool(self.api_keys)

    @property
    def api_key(self) -> str | None:
        return self.api_keys[0] if self.api_keys else None

    @property
    def label(self) -> str:
        return f"{self.scope}:{self.name}"


@dataclass(frozen=True)
class Scope:
    name: str
    provider: str
    profiles: dict[str, Endpoint] = field(default_factory=dict)

    def active(self) -> Endpoint:
        endpoint = self.profiles.get(self.provider)
        if endpoint is None:  # pragma: no cover - load() validates this
            raise ConfigError(self._missing_message())
        return endpoint

    def names(self) -> list[str]:
        return sorted(self.profiles)

    def _missing_message(self) -> str:
        available = ", ".join(self.names()) or "none"
        return (
            f"{self.name}.provider = '{self.provider}' has no matching "
            f"[{self.name}.providers.{self.provider}] table (available: {available})."
        )


@dataclass(frozen=True)
class AppConfig:
    path: Path
    stt: Scope
    llm: Scope
    ui: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, Any] = field(default_factory=dict)
    version: int = SCHEMA_VERSION

    def scope(self, name: str) -> Scope:
        return self.stt if name == STT else self.llm

    def endpoint(self, name: str) -> Endpoint:
        return self.scope(name).active()

    @property
    def prompts_file(self) -> str:
        return str(self.paths.get("prompts_file") or "")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def normalize_provider_id(value: str) -> str:
    """Lowercase a provider id and fold legacy ids (`z.ai` -> `zai`)."""
    slug = (value or "").strip().lower()
    return PROVIDER_ALIASES.get(slug, slug)


def load(path: Path, *, environ: dict[str, str] | None = None) -> AppConfig:
    """Parse and validate the TOML config. Raises ConfigError."""
    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc

    version = raw.get("version", SCHEMA_VERSION)
    if not isinstance(version, int) or version > SCHEMA_VERSION:
        raise ConfigError(
            f"{path} uses config schema version {version!r}; this build supports "
            f"version {SCHEMA_VERSION}. Upgrade aitranscribe or fix the file."
        )

    env = dict(os.environ if environ is None else environ)
    return AppConfig(
        path=path,
        version=version,
        stt=_load_scope(STT, raw, env),
        llm=_load_scope(LLM, raw, env),
        ui=dict(raw.get("ui") or {}),
        paths=dict(raw.get("paths") or {}),
    )


def _load_scope(scope: str, raw: dict[str, Any], env: dict[str, str]) -> Scope:
    section = raw.get(scope) or {}
    if not isinstance(section, dict):
        raise ConfigError(f"[{scope}] must be a table.")
    fallback = DEFAULT_STT_PROVIDER if scope == STT else DEFAULT_LLM_PROVIDER
    provider = normalize_provider_id(str(section.get("provider") or fallback))

    tables = section.get("providers") or {}
    if not isinstance(tables, dict):
        raise ConfigError(f"[{scope}.providers] must be a table.")

    profiles: dict[str, Endpoint] = {}
    for name, table in tables.items():
        if not isinstance(table, dict):
            raise ConfigError(f"[{scope}.providers.{name}] must be a table.")
        profiles[name] = _load_endpoint(scope, str(name), table, env)

    if provider not in profiles:
        if provider in PROVIDER_DEFAULTS:
            # Known provider without an explicit table: built-in defaults.
            profiles[provider] = _load_endpoint(scope, provider, {}, env)
        else:
            available = ", ".join(sorted(profiles)) or "none"
            raise ConfigError(
                f"{scope}.provider = '{provider}' has no [ {scope}.providers.{provider} ] "
                f"table. Available profiles: {available}."
            )

    return Scope(name=scope, provider=provider, profiles=profiles)


def _load_endpoint(
    scope: str, name: str, table: dict[str, Any], env: dict[str, str]
) -> Endpoint:
    defaults = PROVIDER_DEFAULTS.get(normalize_provider_id(name), {})
    base_url = str(table.get("base_url") or defaults.get("base_url") or "").strip()
    if not base_url:
        raise ConfigError(
            f"[{scope}.providers.{name}] needs a base_url "
            f"(no built-in default for profile '{name}')."
        )
    model = str(table.get("model") or defaults.get(f"{scope}_model") or "").strip()
    if not model:
        raise ConfigError(
            f"[{scope}.providers.{name}] needs a model "
            f"(no built-in default for profile '{name}')."
        )

    api_keys, key_sources = _resolve_keys(table, env)
    return Endpoint(
        name=name,
        scope=scope,
        base_url=base_url,
        model=model,
        api_keys=api_keys,
        key_sources=key_sources,
        max_upload_s=_positive_int(
            table.get("max_upload_s"), int(defaults.get("max_upload_s", DEFAULT_MAX_UPLOAD_S)),
            f"[{scope}.providers.{name}].max_upload_s",
        ),
        max_upload_mb=_positive_int(
            table.get("max_upload_mb"), int(defaults.get("max_upload_mb", DEFAULT_MAX_UPLOAD_MB)),
            f"[{scope}.providers.{name}].max_upload_mb",
        ),
        description=str(table.get("description") or "").strip(),
    )


def _positive_int(value: Any, default: int, label: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} must be an integer.") from exc
    if parsed <= 0:
        raise ConfigError(f"{label} must be greater than 0.")
    return parsed


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value if str(item).strip()]
    return []


def _resolve_keys(
    table: dict[str, Any], env: dict[str, str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Resolve api_key/api_key_env. Env-referenced keys come first, duplicates dropped."""
    keys: list[str] = []
    sources: list[str] = []
    for var in _as_list(table.get("api_key_env")):
        value = (env.get(var) or "").strip()
        if value and value not in keys:
            keys.append(value)
            sources.append(f"env:{var}")
    for value in _as_list(table.get("api_key")):
        value = value.strip()
        if value and value not in keys:
            keys.append(value)
            sources.append("file")
    return tuple(keys), tuple(sources)


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
def _tomlkit():
    try:
        import tomlkit  # noqa: PLC0415 - optional dependency, imported on demand
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise ConfigError(
            "Writing the configuration requires the 'tomlkit' package "
            "(pip install tomlkit)."
        ) from exc
    return tomlkit


def set_value(path: Path, *keys: str, value: Any) -> None:
    """Write `value` at the nested key path, preserving comments and layout."""
    tomlkit = _tomlkit()
    path = Path(path)
    if path.exists():
        document = tomlkit.parse(path.read_text(encoding="utf-8"))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = tomlkit.document()

    node: Any = document
    for key in keys[:-1]:
        if key not in node:
            node[key] = tomlkit.table()
        node = node[key]
    node[keys[-1]] = value

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(tomlkit.dumps(document), encoding="utf-8")
    os.replace(tmp_path, path)
    _restrict_permissions(path)


def _restrict_permissions(path: Path) -> None:
    """Best effort 0600 — the file carries API keys."""
    if os.name == "nt":
        return
    try:
        path.chmod(0o600)
    except OSError:
        return


def mask_key(key: str | None) -> str:
    if not key:
        return "<missing>"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}…{key[-4:]}"


# --------------------------------------------------------------------------- #
# Rendering (default file + dotenv migration)
# --------------------------------------------------------------------------- #
def _toml_key(name: str) -> str:
    return name if _BARE_KEY_RE.match(name) else json.dumps(name, ensure_ascii=False)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


_SELFHOSTED_EXAMPLE = """\
# Example: a self-hosted, OpenAI-compatible endpoint (e.g. Whisper on your own
# GPU). Uncomment the table, set base_url/api_key, then point [stt].provider at
# it. Self-hosted servers have no >120 s defect, so the chunk ceiling can rise.
#
# [stt.providers.selfhosted-1]
# description   = "Whisper large-v3 on my own GPU"
# base_url      = "http://localhost:9000/v1"
# api_key       = "…"
# model         = "large-v3"
# max_upload_s  = 900
# max_upload_mb = 100
"""


def _render_profiles(scope: str, profiles: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for name, table in profiles.items():
        lines.append(f"[{scope}.providers.{_toml_key(name)}]")
        ordered = ("description", "base_url", "api_key", "api_key_env", "model",
                   "max_upload_s", "max_upload_mb")
        for field_name in ordered:
            if field_name in table and table[field_name] not in (None, ""):
                lines.append(f"{field_name} = {_toml_value(table[field_name])}")
        lines.append("")
    return lines


def render_document(
    *,
    stt_provider: str,
    stt_profiles: dict[str, dict[str, Any]],
    llm_provider: str,
    llm_profiles: dict[str, dict[str, Any]],
    ui: dict[str, Any],
    paths: dict[str, Any],
    note: list[str] | None = None,
) -> str:
    """Render a fully commented config document (default file and migration)."""
    lines: list[str] = [
        "# aitranscribe configuration — TOML, schema version 2",
        "#",
        "# Scope tables hold the selector only; everything about an endpoint",
        "# (base_url, keys, model, chunk limits) lives in its profile table.",
        "# Precedence for keys: api_key_env (environment) before api_key (this file).",
        "# This file is written by the TUI for user-adjustable settings; hand edits",
        "# keep their comments and formatting.",
        "",
        f"version = {SCHEMA_VERSION}",
        "",
    ]
    if note:
        lines.extend(f"# {line}" if line else "#" for line in note)
        lines.append("")

    lines.extend([
        "# ── Speech-to-Text ──────────────────────────────────────────────",
        f"[{STT}]",
        f"provider = {_toml_value(stt_provider)}",
        "",
        *_render_profiles(STT, stt_profiles),
        *_SELFHOSTED_EXAMPLE.splitlines(),
        "",
        "# ── LLM post-processing ─────────────────────────────────────────",
        f"[{LLM}]",
        f"provider = {_toml_value(llm_provider)}",
        "",
        *_render_profiles(LLM, llm_profiles),
        "# ── UI / runtime ────────────────────────────────────────────────",
        "[ui]",
    ])
    for key in ("pre_process_mode", "output_width", "verbose_errors", "last_file_path"):
        lines.append(f"{key} = {_toml_value(ui.get(key))}")
    lines.extend(["", "[paths]"])
    for key, value in paths.items():
        lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
    lines.append("")
    return "\n".join(lines)


def create_default(path: Path, *, prompts_file: Path | str | None = None) -> None:
    """Write a fresh config.toml with placeholder keys and a self-hosted example."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = render_document(
        stt_provider=DEFAULT_STT_PROVIDER,
        stt_profiles={
            DEFAULT_STT_PROVIDER: {
                "description": "Groq Cloud (US free tier); keys: console.groq.com",
                "base_url": PROVIDER_DEFAULTS["groq"]["base_url"],
                "api_key": "your_groq_api_key_here",
                "model": PROVIDER_DEFAULTS["groq"]["stt_model"],
                "max_upload_s": 120,
                "max_upload_mb": 25,
            }
        },
        llm_provider=DEFAULT_LLM_PROVIDER,
        llm_profiles={
            DEFAULT_LLM_PROVIDER: {
                "description": "OpenRouter (default LLM provider)",
                "base_url": PROVIDER_DEFAULTS["openrouter"]["base_url"],
                "api_key": "your_openrouter_api_key_here",
                "model": PROVIDER_DEFAULTS["openrouter"]["llm_model"],
            },
            "groq": {
                "description": "Groq Cloud; also usable for STT",
                "base_url": PROVIDER_DEFAULTS["groq"]["base_url"],
                "api_key": "your_groq_api_key_here",
                "model": PROVIDER_DEFAULTS["groq"]["llm_model"],
            },
        },
        ui={
            "pre_process_mode": "english",
            "output_width": 80,
            "verbose_errors": False,
            "last_file_path": "",
        },
        paths={"prompts_file": str(prompts_file or (path.parent / "prompts.sqlite"))},
    )
    path.write_text(document, encoding="utf-8")
    _restrict_permissions(path)


# --------------------------------------------------------------------------- #
# dotenv -> TOML migration
# --------------------------------------------------------------------------- #
# legacy provider prefix -> profile id
LEGACY_LLM_PREFIXES: dict[str, str] = {
    "OPENROUTER": "openrouter",
    "COHERE": "cohere",
    "ZAI": "zai",
    "GOOGLE": "google",
    "CORTECS": "cortecs",
    "GROQ": "groq",
}
LEGACY_PLACEHOLDERS = {"", "your_groq_api_key_here"}


def _legacy_values(conf_path: Path) -> dict[str, str]:
    from dotenv import dotenv_values  # noqa: PLC0415 - migration-only dependency

    try:
        raw = dotenv_values(conf_path)
    except OSError as exc:  # pragma: no cover - unreadable file
        raise ConfigError(f"Cannot read legacy config {conf_path}: {exc}") from exc
    return {
        str(key): str(value).strip()
        for key, value in raw.items()
        if value is not None and str(value).strip()
    }


def _legacy_key(values: dict[str, str], name: str) -> str:
    return values.get(name, "") if values.get(name, "") not in LEGACY_PLACEHOLDERS else ""


def build_migration(
    values: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Map flat dotenv values onto the v2 structure.

    A single legacy `GROQ_API_KEY` served both roles, so it is copied into the
    Groq STT profile and (when Groq was the LLM provider) the Groq LLM profile.
    """
    llm_provider = normalize_provider_id(values.get("LLM_PROVIDER") or DEFAULT_LLM_PROVIDER)
    if llm_provider not in PROVIDER_DEFAULTS:
        llm_provider = DEFAULT_LLM_PROVIDER

    llm_profiles: dict[str, dict[str, Any]] = {}
    for prefix, provider in LEGACY_LLM_PREFIXES.items():
        api_key = _legacy_key(values, f"{prefix}_API_KEY")
        model = values.get(f"{prefix}_LLM_MODEL", "")
        if not api_key and not model:
            continue
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        table: dict[str, Any] = {"base_url": defaults.get("base_url", "")}
        if api_key:
            table["api_key"] = api_key
        table["model"] = model or defaults.get("llm_model", "")
        llm_profiles[provider] = table

    if llm_provider not in llm_profiles:
        defaults = PROVIDER_DEFAULTS.get(llm_provider, {})
        llm_profiles[llm_provider] = {
            "base_url": defaults.get("base_url", ""),
            "model": defaults.get("llm_model", ""),
        }

    groq_defaults = PROVIDER_DEFAULTS["groq"]
    stt_profiles: dict[str, dict[str, Any]] = {
        "groq": {
            "description": "Groq Cloud (US free tier); keys: console.groq.com",
            "base_url": groq_defaults["base_url"],
            "model": values.get("GROQ_STT_MODEL") or groq_defaults["stt_model"],
            "max_upload_s": groq_defaults["max_upload_s"],
            "max_upload_mb": groq_defaults["max_upload_mb"],
        }
    }
    groq_key = _legacy_key(values, "GROQ_API_KEY")
    if groq_key:
        stt_profiles["groq"]["api_key"] = groq_key

    ui = {
        "pre_process_mode": (values.get("PRE_PROCESS_MODE") or "english").lower(),
        "output_width": _coerce_legacy_width(values.get("OUTPUT_WIDTH")),
        "verbose_errors": str(values.get("VERBOSE_ERRORS", "")).lower() in {"1", "true", "yes", "on"},
        "last_file_path": values.get("LAST_FILE_PATH", ""),
    }
    paths: dict[str, Any] = {}
    if values.get("PROMPTS_FILE"):
        paths["prompts_file"] = values["PROMPTS_FILE"]
    return (
        {"provider": DEFAULT_STT_PROVIDER, "profiles": stt_profiles},
        {"provider": llm_provider, "profiles": llm_profiles},
        ui,
        paths,
    )


def _coerce_legacy_width(value: str | None) -> int:
    try:
        width = int(str(value).strip())
    except (TypeError, ValueError):
        return 80
    return width if width in (0, 80, 120) else 80


def migrate_dotenv(conf_path: Path, toml_path: Path) -> dict[str, Any] | None:
    """Convert a legacy aitranscribe.conf into config.toml, then retire the old file.

    Returns a summary dict, or None when there is nothing to migrate.
    """
    conf_path = Path(conf_path)
    toml_path = Path(toml_path)
    if not conf_path.exists():
        return None
    values = _legacy_values(conf_path)
    if not values:
        return None

    stt, llm, ui, paths = build_migration(values)
    if "prompts_file" not in paths:
        paths["prompts_file"] = str(toml_path.parent / "prompts.sqlite")

    document = render_document(
        stt_provider=stt["provider"],
        stt_profiles=stt["profiles"],
        llm_provider=llm["provider"],
        llm_profiles=llm["profiles"],
        ui=ui,
        paths=paths,
        note=[
            "Migrated from aitranscribe.conf (schema version 1) on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}.",
            "Duplicated legacy blocks were collapsed; values are identical.",
            "The old file is kept next to this one as a backup.",
        ],
    )
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    toml_path.write_text(document, encoding="utf-8")
    _restrict_permissions(toml_path)

    backup = conf_path.with_name(
        f"{conf_path.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    try:
        shutil.move(str(conf_path), str(backup))
    except OSError:  # pragma: no cover - keep going, config.toml is written
        backup = conf_path

    return {
        "toml": toml_path,
        "backup": backup,
        "stt_provider": stt["provider"],
        "llm_provider": llm["provider"],
        "stt_profiles": sorted(stt["profiles"]),
        "llm_profiles": sorted(llm["profiles"]),
        "legacy_keys": len(values),
    }


def migrate_if_needed(conf_path: Path, toml_path: Path) -> dict[str, Any] | None:
    """Migrate only when the TOML file does not exist yet."""
    if Path(toml_path).exists():
        return None
    return migrate_dotenv(conf_path, toml_path)

from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def env_file() -> Path:
    """Location of the framework's key file (repo root .env by default)."""

    override = os.environ.get("HUMANIZER_ENV_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / ".env"


def load_env() -> None:
    """Load KEY=VALUE pairs from the framework's .env into os.environ.

    Real environment variables always win: values that are already set are
    never overwritten. A missing file is normal (keys may come from user-env
    or provider-specific stores instead). Safe to call repeatedly.
    """

    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        lines = env_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def env_file() -> Path:
    """Путь к файлу переменных окружения (обычно .env в корне проекта)."""
    override = os.environ.get("HUMANIZER_ENV_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / ".env"


def load_env() -> None:
    """Загружаем KEY=VALUE. Установленные переменные окружения важнее файла.

    Файл проверяется при каждом вызове. Это позволяет создавать .env после
    первого вызова, менять путь через HUMАNIZER_ENV_FILE и работать в тестах.
    """
    global _LOADED
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
    _LOADED = True

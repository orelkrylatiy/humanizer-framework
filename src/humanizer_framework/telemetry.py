from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_WRITE_LOCK = threading.Lock()


def _enabled() -> bool:
    return os.environ.get("HUMANIZER_TELEMETRY", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }


def _identifiers_enabled() -> bool:
    return os.environ.get("HUMANIZER_TELEMETRY_IDENTIFIERS", "0").strip().lower() in {
        "1",
        "true",
        "on",
        "yes",
    }


def telemetry_path() -> Path | None:
    if not _enabled():
        return None
    configured = os.environ.get("HUMANIZER_TELEMETRY_PATH")
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base / "humanizer-framework" / "telemetry.jsonl"


def _request_fields(request: Any) -> dict[str, Any]:
    context = getattr(request, "context", {}) or {}
    fields: dict[str, Any] = {
        "channel": getattr(request, "channel", None),
        "domain": getattr(request, "domain", None),
        "message_type": str(getattr(request, "message_type", "")),
        "profile": getattr(request, "profile", None),
        "language": getattr(request, "language", None),
    }
    # Идентификаторы собеседников по умолчанию НЕ записываем.
    if _identifiers_enabled():
        for output_key, context_keys in {
            "lead": ("lead", "username", "recipient", "chat"),
            "source_channel": ("source_channel",),
            "case": ("case", "scenario", "flow"),
        }.items():
            for key in context_keys:
                value = context.get(key)
                if isinstance(value, (str, int, float, bool)) and value != "":
                    fields[output_key] = value
                    break
    return fields


def provider_snapshot(provider: Any) -> dict[str, Any]:
    snapshot_method = getattr(provider, "generation_snapshot", None)
    snapshot = snapshot_method() if callable(snapshot_method) else {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    actual = getattr(provider, "last_provider", None) or provider
    name = (
        snapshot.get("provider")
        or getattr(provider, "last_provider_name", None)
        or getattr(actual, "name", type(actual).__name__)
    )
    model = (
        snapshot.get("model")
        or getattr(provider, "last_model", None)
        or getattr(actual, "model", None)
    )
    usage = snapshot.get("usage")
    if usage is None:
        usage = getattr(provider, "last_usage", None) or getattr(actual, "last_usage", None)
    errors = snapshot.get("provider_error_count")
    if errors is None:
        errors = len(getattr(provider, "last_errors", None) or [])
    result: dict[str, Any] = {"provider": str(name)[:120]}
    if model:
        result["model"] = str(model)[:120]
    # Только числовые показатели. Не переносим произвольную строку от API.
    if isinstance(usage, dict):
        result["usage"] = {
            str(key)[:50]: value
            for key, value in usage.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    if errors:
        result["provider_error_count"] = int(errors)
    return result


def write_generation_event(
    request: Any,
    *,
    started_at: datetime,
    status: str,
    provider: Any,
    elapsed_ms: int,
    calls: int,
    attempts: int,
    repair_attempted: bool,
    rewritten: bool = False,
    issues: list[Any] | None = None,
    error: BaseException | None = None,
) -> None:
    path = telemetry_path()
    if path is None:
        return
    event: dict[str, Any] = {
        "schema_version": 2,
        "event": "generation",
        "timestamp": started_at.isoformat(),
        "project": os.environ.get("HUMANIZER_PROJECT") or Path.cwd().name,
        "status": status,
        "elapsed_ms": elapsed_ms,
        "calls": calls,
        "attempts": attempts,
        "repair_attempted": repair_attempted,
        "rewritten": rewritten,
        **_request_fields(request),
        **provider_snapshot(provider),
    }
    if issues is not None:
        event["issues"] = [getattr(issue, "code", "unknown") for issue in issues]
    if error is not None:
        event["error_type"] = type(error).__name__
        # Текст исключения принципиально не сохраняем: некоторые SDK
        # включают в него URL с ключами и содержимое запроса.
        event["error"] = "details_redacted"
    try:
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
        with _WRITE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(payload + "\n")
    except (OSError, TypeError, ValueError):
        # Сбой записи телеметрии не блокирует генерацию.
        return


def now_utc() -> datetime:
    return datetime.now(UTC)

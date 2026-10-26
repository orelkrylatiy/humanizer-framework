from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_WRITE_LOCK = threading.Lock()
_REDACT_RE = re.compile(r"(?i)(bearer\s+)[^\s,]+|((?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s,]+")


def _enabled() -> bool:
    return os.environ.get("HUMANIZER_TELEMETRY", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
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


def _safe_error(exc: BaseException) -> str:
    value = _REDACT_RE.sub(lambda match: f"{match.group(1) or match.group(2)}<redacted>", str(exc))
    return value[-1200:]


def _request_fields(request: Any) -> dict[str, Any]:
    context = getattr(request, "context", {}) or {}
    fields: dict[str, Any] = {
        "channel": getattr(request, "channel", None),
        "domain": getattr(request, "domain", None),
        "message_type": str(getattr(request, "message_type", "")),
        "profile": getattr(request, "profile", None),
        "language": getattr(request, "language", None),
    }
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
    actual = getattr(provider, "last_provider", None) or provider
    model = getattr(provider, "last_model", None) or getattr(actual, "model", None)
    name = getattr(provider, "last_provider_name", None) or getattr(actual, "name", type(actual).__name__)
    usage = getattr(provider, "last_usage", None) or getattr(actual, "last_usage", None)
    errors = getattr(provider, "last_errors", None) or getattr(actual, "last_errors", None)
    result: dict[str, Any] = {"provider": name}
    if model:
        result["model"] = model
    if isinstance(usage, dict):
        result["usage"] = usage
    if errors:
        result["provider_errors"] = [str(item)[-1200:] for item in errors[-10:]]
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
        "schema_version": 1,
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
        event["issues"] = [getattr(issue, "code", str(issue)) for issue in issues]
    if error is not None:
        event["error_type"] = type(error).__name__
        event["error"] = _safe_error(error)
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
    try:
        with _WRITE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(payload + "\n")
    except OSError:
        # Observability must never break message generation.
        return


def now_utc() -> datetime:
    return datetime.now(UTC)

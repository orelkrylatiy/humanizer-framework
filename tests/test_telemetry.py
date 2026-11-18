import json
from datetime import UTC, datetime

from humanizer_framework.models import CommunicationRequest, MessageType
from humanizer_framework.telemetry import write_generation_event


def test_generation_telemetry_is_jsonl_and_does_not_store_text(monkeypatch, tmp_path):
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("HUMANIZER_TELEMETRY_PATH", str(path))
    request = CommunicationRequest(
        channel="telegram",
        domain="job_search",
        message_type=MessageType.OUTREACH,
        profile="max-react",
        context={"lead": "@hr", "vacancy": "private text"},
    )

    write_generation_event(
        request,
        started_at=datetime.now(UTC),
        status="success",
        provider=type("Provider", (), {"name": "test", "model": "test-model"})(),
        elapsed_ms=12,
        calls=1,
        attempts=1,
        repair_attempted=False,
    )

    event = json.loads(path.read_text(encoding="utf-8"))
    assert "lead" not in event
    assert event["model"] == "test-model"
    assert "private text" not in path.read_text(encoding="utf-8")


def test_telemetry_can_opt_in_to_identifiers(monkeypatch, tmp_path):
    monkeypatch.setenv("HUMANIZER_TELEMETRY_PATH", str(tmp_path / "ids.jsonl"))
    monkeypatch.setenv("HUMANIZER_TELEMETRY_IDENTIFIERS", "1")
    request = CommunicationRequest(
        channel="telegram",
        domain="generic",
        message_type="chat_reply",
        context={"lead": "@hr"},
    )
    write_generation_event(
        request,
        started_at=datetime.now(UTC),
        status="success",
        provider=type("P", (), {"name": "mock"})(),
        elapsed_ms=1,
        calls=1,
        attempts=1,
        repair_attempted=False,
    )
    data = json.loads((tmp_path / "ids.jsonl").read_text(encoding="utf-8"))
    assert data["lead"] == "@hr"


def test_telemetry_never_logs_provider_error_or_exception_secrets(monkeypatch, tmp_path):
    path = tmp_path / "safe.jsonl"
    monkeypatch.setenv("HUMANIZER_TELEMETRY_PATH", str(path))
    monkeypatch.delenv("HUMANIZER_TELEMETRY_IDENTIFIERS", raising=False)
    request = CommunicationRequest(
        channel="telegram",
        domain="generic",
        message_type="chat_reply",
        context={"lead": "@secret-person", "vacancy": "private text"},
    )

    class Broken:
        name = "harness"
        last_errors = ["zai-http: Authorization Bearer super-secret-api-key"]
        last_usage = {"total_tokens": 10, "debug": "Bearer secret"}

    write_generation_event(
        request,
        started_at=datetime.now(UTC),
        status="error",
        provider=Broken(),
        elapsed_ms=1,
        calls=1,
        attempts=1,
        repair_attempted=False,
        error=RuntimeError("super-secret-api-key"),
    )
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert "super-secret-api-key" not in raw
    assert "@secret-person" not in raw
    assert "private text" not in raw
    assert "Bearer secret" not in raw
    assert data["error"] == "details_redacted"
    assert data["provider_error_count"] == 1
    assert data["usage"] == {"total_tokens": 10}

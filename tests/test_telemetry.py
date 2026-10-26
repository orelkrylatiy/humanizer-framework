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
    assert event["lead"] == "@hr"
    assert event["model"] == "test-model"
    assert "private text" not in path.read_text(encoding="utf-8")

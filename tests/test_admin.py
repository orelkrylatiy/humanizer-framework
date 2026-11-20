from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from humanizer_framework import admin
from humanizer_framework.models import CommunicationRequest


def _client(monkeypatch):
    monkeypatch.setenv(
        "HUMANIZER_ADMIN_ALLOWED_HOSTS",
        "localhost,127.0.0.1,::1,testclient,testserver",
    )
    monkeypatch.delenv("HUMANIZER_ADMIN_TOKEN", raising=False)
    return TestClient(admin.create_app())


def test_options_exposes_existing_message_types(monkeypatch):
    response = _client(monkeypatch).get("/api/options")
    assert response.status_code == 200
    modes = {item["value"] for item in response.json()["modes"]}
    assert modes == {
        "outreach",
        "application",
        "channel_post",
        "chat_reply",
        "follow_up",
        "scheduling",
        "objection",
    }


def test_preview_uses_prepare_and_includes_operator_goal(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/api/preview",
        json={
            "prompt": "Напиши короткое сообщение о занятиях по Python",
            "message_type": "channel_post",
            "domain": "generic",
            "channel": "telegram",
            "language": "ru",
            "source_text": "Нужен текст для начинающих.",
            "context": {"subject": "Python"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["action"] == "pitch"
    system_messages = [item["content"] for item in data["messages"] if item["role"] == "system"]
    assert any(
        "Цель сообщения - Напиши короткое сообщение о занятиях по Python" in item
        for item in system_messages
    )
    assert any("Нужен текст для начинающих." in item["content"] for item in data["messages"])


def test_generate_maps_prompt_and_context_to_core_request(monkeypatch):
    captured = {}

    class FakeFramework:
        provider = SimpleNamespace(name="test-provider", model="test-model")

        def generate(self, request):
            captured["request"] = request
            plan = SimpleNamespace(
                act=SimpleNamespace(value="disclosure"),
                stage=SimpleNamespace(value="new"),
                action=SimpleNamespace(value="pitch"),
                target_length=SimpleNamespace(value="long"),
                ask_question=False,
                allow_cta=True,
                max_chars=1400,
                rationale="test",
            )
            return SimpleNamespace(
                text="Готовый текст",
                valid=True,
                provider="test-provider",
                rewritten=False,
                issues=[],
                plan=plan,
            )

    monkeypatch.setattr(admin, "CommunicationFramework", FakeFramework)
    client = _client(monkeypatch)
    response = client.post(
        "/api/generate",
        json={
            "prompt": "Напиши публикацию",
            "message_type": "channel_post",
            "domain": "generic",
            "channel": "generic",
            "language": "ru",
            "profile": "writer",
            "source_text": "Исходная заметка",
            "context": {"topic": "образование"},
            "business_rules": ["Не используй рекламные обещания"],
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Готовый текст"
    request = captured["request"]
    assert isinstance(request, CommunicationRequest)
    assert request.business_rules[0] == "Цель сообщения - Напиши публикацию"
    assert request.conversation[0].content == "Исходная заметка"
    assert request.context["topic"] == "образование"
    assert request.business_rules[1] == "Не используй рекламные обещания"


def test_remote_api_requires_token(monkeypatch):
    monkeypatch.setenv("HUMANIZER_ADMIN_ALLOWED_HOSTS", "localhost,127.0.0.1,::1,testserver")
    monkeypatch.setenv("HUMANIZER_ADMIN_TOKEN", "test-secret")
    app = admin.create_app()
    client = TestClient(app, client=("192.0.2.10", 12345))
    response = client.get("/api/health", headers={"host": "localhost"})
    assert response.status_code == 401
    response = client.get(
        "/api/health",
        headers={"host": "localhost", "authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200


def test_activity_does_not_return_unapproved_telemetry_fields(monkeypatch, tmp_path):
    path = tmp_path / "telemetry.jsonl"
    path.write_text(
        json.dumps(
            {
                "event": "generation",
                "timestamp": "2026-11-20T00:00:00+00:00",
                "status": "success",
                "message_type": "channel_post",
                "prompt": "secret prompt",
                "generated_text": "secret output",
                "lead": "@private",
                "provider": "mock",
                "elapsed_ms": 12,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HUMANIZER_TELEMETRY_PATH", str(path))
    monkeypatch.setenv("HUMANIZER_TELEMETRY", "1")
    client = _client(monkeypatch)
    monkeypatch.setattr(admin, "telemetry_path", lambda: path)
    response = client.get("/api/activity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["provider"] == "mock"
    assert "prompt" not in payload["items"][0]
    assert "generated_text" not in payload["items"][0]
    assert "lead" not in payload["items"][0]


def test_api_responses_have_security_headers(monkeypatch):
    response = _client(monkeypatch).get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"

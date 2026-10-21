from unittest.mock import patch

from humanizer_framework import (
    CommunicationFramework,
    GenerationValidationError,
    Message,
    MessageType,
    MockProvider,
    tutoring_request,
)
from humanizer_framework.providers import ZaiAnthropicProvider
import pytest


def test_generate_retries_when_first_answer_contains_forbidden_cta():
    provider = MockProvider(
        [
            "Давайте начнем с пробного: когда вам удобно?",
            "Понял) Тогда в основном домашки и будем разбирать.",
        ]
    )
    framework = CommunicationFramework(provider)
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )
    result = framework.generate(request)
    assert isinstance(result, str)
    assert result.rewritten is True
    assert result.valid
    assert result.text == "Понял) Тогда в основном домашки и будем разбирать."
    assert len(provider.calls) == 2


def test_zero_config_default_provider_is_zai_http():
    framework = CommunicationFramework()
    assert isinstance(framework.provider, ZaiAnthropicProvider)
    assert framework.provider.name == "zai-http"


def test_zero_config_generate_resolves_key_from_env(monkeypatch):
    for var in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "ZAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "secret-value")

    captured = {}

    def fake_post(url, payload, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers)
        return {
            "content": [
                {"type": "text", "text": "Понял) Тогда в основном домашки и будем разбирать."}
            ]
        }

    framework = CommunicationFramework()
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )
    with patch.object(ZaiAnthropicProvider, "_post", staticmethod(fake_post)):
        result = framework.generate(request)

    assert result.valid
    assert result.provider == "zai-http"
    assert captured["url"].endswith("/v1/messages")
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert captured["headers"]["Authorization"] == "Bearer secret-value"


def test_generate_never_returns_text_with_hard_validation_issues():
    provider = MockProvider(
        [
            "Давайте начнем с пробного: когда вам удобно?",
            "Когда вам удобно начать пробное занятие?",
        ]
    )
    framework = CommunicationFramework(provider, provider_attempts=1)
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )

    with pytest.raises(GenerationValidationError) as caught:
        framework.generate(request)

    assert caught.value.last_text
    assert any(issue.hard for issue in caught.value.issues)


class _FlakyProvider:
    name = "flaky"

    def __init__(self):
        self.calls = 0

    def generate(self, messages, *, temperature=0.4, max_tokens=300):
        del messages, temperature, max_tokens
        self.calls += 1
        if self.calls == 1:
            raise OSError("temporary failure")
        return "Понял) Тогда в основном домашки и будем разбирать."


def test_generate_retries_provider_failures_inside_framework():
    provider = _FlakyProvider()
    framework = CommunicationFramework(provider, retry_delay_seconds=0)
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )

    text = framework.generate(request)

    assert text == "Понял) Тогда в основном домашки и будем разбирать."
    assert provider.calls == 2


def test_prepare_works_without_provider():
    framework = CommunicationFramework()
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="chinese",
        conversation=[],
    )
    package = framework.prepare(request)
    assert package.plan.action == "pitch"

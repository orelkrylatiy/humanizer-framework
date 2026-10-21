import pytest

from humanizer_framework import (
    ClaudeCodeCLIProvider,
    MockProvider,
    ProviderExecutionError,
    VoiceProfile,
    default_provider,
    write,
)
from humanizer_framework.providers import HarnessProvider
from humanizer_framework.providers import claude_cli as claude_cli_module


def test_write_returns_validated_text_and_sends_goal():
    long_enough = (
        "Здравствуйте, Ольга! Занимаюсь математикой с учениками 5-9 классов, "
        "готовлю по школьной программе и олимпиадам. На первом занятии разберём "
        "пробелы и составим план подготовки.\n\nКогда удобно начать?"
    )
    provider = MockProvider([long_enough])
    result = write(
        "Первый отклик репетитора математики: показать релевантность",
        channel="profi",
        domain="tutoring",
        message_type="outreach",
        language="ru",
        facts={"client_name": "Ольга"},
        provider=provider,
    )
    assert isinstance(result, str)
    assert result.valid
    assert "математик" in result
    goal_block = "\n".join(m["content"] for m in provider.calls[0])
    assert "Message goal: Первый отклик репетитора математики" in goal_block


def test_write_maps_dialogue_roles():
    provider = MockProvider(["Отвечаю по делу, без лишних деталей."])
    write(
        "Ответить на вопрос клиента о цене",
        channel="profi",
        dialogue=[("user", "Сколько стоит занятие?"), ("me", "Здравствтуйте!"), "Ок"],
        provider=provider,
    )
    roles = [m["role"] for m in provider.calls[0] if m["role"] in {"user", "assistant"}]
    # trailing "user" is the fixed final instruction turn appended by build_prompt
    assert roles == ["user", "assistant", "user", "user"]


def test_write_respects_message_type_and_facts_flow():
    provider = MockProvider(["Хорошо, тогда жду ваше сообщение с деталями."])
    write(
        "Подтвердить договорённость",
        message_type="chat_reply",
        facts={"subject": "химия"},
        voice=VoiceProfile(id="maxim", description="short", examples=["Начнём?"]),
        provider=provider,
    )
    joined = "\n".join(m["content"] for m in provider.calls[0])
    assert "химия" in joined and "Начнём?" in joined


def test_default_provider_chain_order():
    chain = default_provider()
    assert isinstance(chain, HarnessProvider)
    legs = [(type(p).__name__, getattr(p, "model", None)) for p in chain.providers]
    assert legs == [
        ("OpenCodeCLIProvider", "openai/gpt-5.6-luna-fast"),
        ("ZaiAnthropicProvider", "glm-5.3-flash"),
        ("OpenCodeCLIProvider", "openai-api/gpt-4.1-mini"),
    ]


def test_default_provider_opencode_model_override(monkeypatch):
    monkeypatch.setenv("HUMANIZER_OPENCODE_MODEL", "openai/gpt-6-mini")
    chain = default_provider()
    assert chain.providers[0].model == "openai/gpt-6-mini"


def test_claude_cli_command_build():
    provider = ClaudeCodeCLIProvider(model="sonnet")
    assert provider.command == ["claude", "-p", "--output-format", "text", "--model", "sonnet"]
    assert ClaudeCodeCLIProvider().command == ["claude", "-p", "--output-format", "text"]


def test_claude_cli_empty_response_fails(monkeypatch):
    import subprocess

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, returncode=0, stdout="   ", stderr="")

    monkeypatch.setattr(claude_cli_module, "_run_command", fake_run)
    provider = ClaudeCodeCLIProvider()
    with pytest.raises(ProviderExecutionError):
        provider.generate([{"role": "user", "content": "hi"}])


def test_claude_cli_returns_text(monkeypatch):
    import subprocess

    def fake_run(command, **kwargs):
        assert "SYSTEM" in kwargs["prompt"]
        return subprocess.CompletedProcess(command, returncode=0, stdout="Готовый ответ\n")

    monkeypatch.setattr(claude_cli_module, "_run_command", fake_run)
    out = ClaudeCodeCLIProvider().generate(
        [{"role": "system", "content": "policy"}, {"role": "user", "content": "задача"}]
    )
    assert out == "Готовый ответ"

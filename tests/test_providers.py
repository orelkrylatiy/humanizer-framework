import json
import subprocess
import urllib.error
from unittest.mock import patch

import pytest

from humanizer_framework.config import ProviderConfig, provider_from_config
from humanizer_framework.providers import (
    HarnessProvider,
    LiteLLMProvider,
    OpenCodeCLIProvider,
    ProviderPool,
    openai_api_provider,
    zai_api_provider,
)
from humanizer_framework.providers.cli import (
    _extract_opencode_usage,
    _parse_opencode_jsonl,
)


def test_provider_specs_are_lazy_and_constructible():
    assert LiteLLMProvider("zai/glm-4.7").model == "zai/glm-4.7"
    assert OpenCodeCLIProvider(model="openai/gpt-6-luna").command[:2] == [
        "opencode",
        "run",
    ]


def test_provider_factory_supports_glm_via_litellm():
    provider = provider_from_config(ProviderConfig(kind="litellm", model="zai/glm-4.7"))
    assert isinstance(provider, LiteLLMProvider)


def test_litellm_reserved_fields_cannot_be_overridden():
    with pytest.raises(ValueError):
        LiteLLMProvider("some-model", kwargs={"messages": []})


def test_provider_factory_supports_opencode_backend():
    opencode = provider_from_config(
        ProviderConfig(kind="opencode-cli", model="anthropic/claude-sonnet-4-5")
    )

    assert opencode.model == "anthropic/claude-sonnet-4-5"


def test_opencode_jsonl_parser_returns_only_assistant_text():
    output = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            '{"type":"text","part":{"type":"text","text":"Готовый "}}',
            '{"type":"text","part":{"type":"text","text":"ответ"}}',
            '{"type":"step_finish","part":{"type":"step-finish"}}',
        ]
    )

    assert _parse_opencode_jsonl(output) == "Готовый ответ"


def test_opencode_jsonl_extracts_nested_step_usage_and_sums_steps():
    output = "\n".join(
        [
            json.dumps(
                {
                    "type": "step_finish",
                    "part": {
                        "type": "step-finish",
                        "cost": 0.01,
                        "tokens": {
                            "input": 120,
                            "output": 30,
                            "reasoning": 10,
                            "total": 160,
                            "cache": {"read": 40, "write": 5},
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "type": "step_finish",
                    "part": {
                        "type": "step-finish",
                        "cost": 0.02,
                        "tokens": {
                            "input": 80,
                            "output": 20,
                            "reasoning": 5,
                            "total": 105,
                            "cache": {"read": 10, "write": 0},
                        },
                    },
                }
            ),
        ]
    )

    assert _extract_opencode_usage(output) == {
        "cost": 0.03,
        "input_tokens": 200,
        "output_tokens": 50,
        "reasoning_tokens": 15,
        "total_tokens": 265,
        "cache_read_tokens": 50,
        "cache_write_tokens": 5,
    }


def test_opencode_requires_explicit_provider_and_model():
    with pytest.raises(TypeError):
        OpenCodeCLIProvider()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="provider/model"):
        OpenCodeCLIProvider(model="gpt-6-luna")


def test_opencode_passes_variant_and_credential_without_storing_secret(monkeypatch):
    monkeypatch.setenv("HUMANIZER_OPENAI_KEY_1", "secret-value")
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"type":"text","part":{"text":"ответ"}}',
        stderr="",
    )
    provider = OpenCodeCLIProvider(
        model="openai/gpt-6-luna",
        variant="high",
        credential_source_env="HUMANIZER_OPENAI_KEY_1",
        credential_target_env="OPENAI_API_KEY",
        opencode_config={"provider": {"custom": {"name": "Custom"}}},
    )
    with (
        patch("humanizer_framework.providers.cli._resolve_executable", return_value="opencode"),
        patch("humanizer_framework.providers.cli._run_command", return_value=completed) as run,
    ):
        assert provider.generate([{"role": "user", "content": "Ответь"}]) == "ответ"

    command = run.call_args.args[0]
    environment = run.call_args.kwargs["env"]
    assert command[command.index("--variant") + 1] == "high"
    assert environment["OPENAI_API_KEY"] == "secret-value"
    assert environment["OPENCODE_DB"].endswith("opencode.db")
    config = json.loads(environment["OPENCODE_CONFIG_CONTENT"])
    assert config["provider"]["custom"]["name"] == "Custom"
    assert config["permission"] == {"*": "deny"}
    assert "secret-value" not in repr(provider.__dict__)


def test_opencode_reads_credential_from_json_file_without_storing_it(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"env":{"TOKEN":"file-secret"}}', encoding="utf-8")
    provider = OpenCodeCLIProvider(
        model="zai-coding/glm-5.3-flash",
        credential_source_file=settings,
        credential_source_json_path="env.TOKEN",
        credential_target_env="ZAI_API_KEY",
    )

    assert provider._load_credential() == "file-secret"
    assert "file-secret" not in repr(provider.__dict__)


def test_explicit_openai_and_zai_api_factories():
    gpt = openai_api_provider(credential_source_env="HUMANIZER_OPENAI_KEY_1")
    glm = zai_api_provider(
        credential_source_file="~/.claude/settings.json",
        credential_source_json_path="env.ANTHROPIC_AUTH_TOKEN",
    )

    assert gpt.model == "openai-api/gpt-4.1-mini"
    assert gpt.credential_target_env == "OPENAI_API_KEY"
    assert glm.model == "zai-coding/glm-5.3-flash"
    assert glm.credential_target_env == "ZAI_API_KEY"
    harness = HarnessProvider.opencode_provider_pool([gpt, glm])
    assert isinstance(harness.providers[0], ProviderPool)

    assert openai_api_provider().credential_source_env == "OPENAI_API_KEY"
    assert zai_api_provider().credential_source_env == "ZAI_API_KEY"


def test_provider_pool_round_robins_and_harness_falls_back():
    class Stub:
        def __init__(self, name, result=None):
            self.name = name
            self.result = result

        def generate(self, messages, **kwargs):
            del messages, kwargs
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

    first = Stub("first", "one")
    second = Stub("second", "two")
    pool = ProviderPool([first, second])
    assert pool.generate([]) == "one"
    assert pool.generate([]) == "two"

    harness = HarnessProvider([Stub("broken", RuntimeError("down")), second])
    assert harness.generate([]) == "two"


def test_provider_factory_builds_opencode_first_harness():
    provider = provider_from_config(
        ProviderConfig(
            kind="harness",
            model="openai/gpt-6-luna",
        )
    )
    assert isinstance(provider, HarnessProvider)
    assert isinstance(provider.providers[0], OpenCodeCLIProvider)


def test_opencode_harness_has_no_non_opencode_fallbacks_by_default():
    provider = HarnessProvider.opencode_first("openai/gpt-6-luna")
    assert len(provider.providers) == 1
    assert isinstance(provider.providers[0], OpenCodeCLIProvider)


def test_opencode_pool_rotates_models_and_factory_supports_it():
    provider = provider_from_config(
        ProviderConfig(
            kind="opencode-pool",
            options={
                "backends": [
                    {"model": "openai/gpt-6-luna"},
                    {"model": "zai-coding/glm-5.3-flash"},
                ]
            },
        )
    )
    assert isinstance(provider, HarnessProvider)
    pool = provider.providers[0]
    assert isinstance(pool, ProviderPool)
    assert [item.model for item in pool.providers] == [
        "openai/gpt-6-luna",
        "zai-coding/glm-5.3-flash",
    ]


# --- ZaiAnthropicProvider (direct HTTP) ----------------------------------------


def test_zai_http_factory_and_defaults():
    from humanizer_framework.providers import ZaiAnthropicProvider

    provider = provider_from_config(ProviderConfig(kind="zai-http", model="glm-5.3-flash"))
    assert isinstance(provider, ZaiAnthropicProvider)
    assert provider.model == "glm-5.3-flash"
    assert provider.base_url == "https://api.z.ai/api/anthropic"


def test_zai_http_resolves_key_from_env_chain_without_exposing_it(monkeypatch):
    from humanizer_framework.providers import ZaiAnthropicProvider

    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    provider = ZaiAnthropicProvider()
    with pytest.raises(Exception, match="ANTHROPIC_AUTH_TOKEN"):
        provider._resolve_key()
    monkeypatch.setenv("ZAI_API_KEY", "secret-value")
    assert provider._resolve_key() == "secret-value"


def test_zai_http_generate_posts_anthropic_payload_and_extracts_text(monkeypatch):
    from humanizer_framework.providers import ZaiAnthropicProvider

    monkeypatch.setenv("ZAI_API_KEY", "secret-value")
    captured = {}

    def fake_post(url, payload, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers)
        return {"content": [{"type": "text", "text": "Готовый ответ"}]}

    provider = ZaiAnthropicProvider(api_key_env=("ZAI_API_KEY",), max_tokens_floor=3000)
    with patch.object(ZaiAnthropicProvider, "_post", staticmethod(fake_post)):
        text = provider.generate(
            [
                {"role": "system", "content": "правила"},
                {"role": "user", "content": "задача"},
            ],
            max_tokens=300,
        )
    assert text == "Готовый ответ"
    assert captured["url"].endswith("/v1/messages")
    assert captured["payload"]["thinking"] == {"type": "enabled"}
    assert captured["payload"]["max_tokens"] == 3000
    assert captured["payload"]["model"] == "glm-5.3-flash"
    assert captured["headers"]["Authorization"] == "Bearer secret-value"
    assert "system" in captured["payload"]
    assert "правила" in captured["payload"]["system"]


def test_zai_http_empty_text_and_http_errors_raise_provider_error(monkeypatch):
    from humanizer_framework.errors import ProviderExecutionError
    from humanizer_framework.providers import ZaiAnthropicProvider

    monkeypatch.setenv("ZAI_API_KEY", "secret-value")
    provider = ZaiAnthropicProvider(api_key_env=("ZAI_API_KEY",))

    def empty_post(url, payload, headers, timeout):
        return {"content": []}

    with (
        patch.object(ZaiAnthropicProvider, "_post", staticmethod(empty_post)),
        pytest.raises(ProviderExecutionError, match="empty text"),
    ):
        provider.generate([{"role": "user", "content": "задача"}])

    def broken_post(url, payload, headers, timeout):
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)

    with (
        patch.object(ZaiAnthropicProvider, "_post", staticmethod(broken_post)),
        pytest.raises(ProviderExecutionError, match="zai-http request failed"),
    ):
        provider.generate([{"role": "user", "content": "задача"}])

from humanizer_framework.config import ProviderConfig, provider_from_config
from humanizer_framework.providers import ClaudeCLIProvider, CodexCLIProvider, LiteLLMProvider


def test_provider_specs_are_lazy_and_constructible():
    assert LiteLLMProvider("zai/glm-4.7").model == "zai/glm-4.7"
    assert CodexCLIProvider().command[:2] == ["codex", "exec"]
    assert ClaudeCLIProvider().command[:2] == ["claude", "-p"]


def test_provider_factory_supports_glm_via_litellm():
    provider = provider_from_config(ProviderConfig(kind="litellm", model="zai/glm-4.7"))
    assert isinstance(provider, LiteLLMProvider)

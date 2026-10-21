from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .providers import (
    HarnessProvider,
    LiteLLMProvider,
    OpenCodeCLIProvider,
)
from .providers.base import Provider


@dataclass(slots=True)
class ProviderConfig:
    kind: str = "litellm"
    model: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FrameworkConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    strict: bool = False


def load_config(path: str | Path) -> FrameworkConfig:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    provider = data.get("provider", {})
    if not isinstance(provider, dict):
        raise ValueError("[provider] must be a TOML table")
    options = provider.get("options", {})
    if not isinstance(options, dict):
        raise ValueError("[provider.options] must be a TOML table")
    model = provider.get("model")
    if model is not None and not isinstance(model, str):
        raise ValueError("provider.model must be a string")
    return FrameworkConfig(
        provider=ProviderConfig(
            kind=str(provider.get("kind", "litellm")),
            model=model,
            options=dict(options),
        ),
        strict=bool(data.get("strict", False)),
    )


def provider_from_config(config: ProviderConfig) -> Provider:
    kind = config.kind.lower()
    if kind == "litellm":
        if not config.model:
            raise ValueError("LiteLLM provider requires a model")
        return LiteLLMProvider(config.model, kwargs=config.options)
    if kind == "opencode-cli":
        if not config.model:
            raise ValueError("OpenCode provider requires a provider/model")
        options = dict(config.options)
        options.setdefault("model", config.model)
        return OpenCodeCLIProvider(**options)
    if kind == "harness":
        if not config.model:
            raise ValueError("Harness provider requires an OpenCode provider/model")
        return HarnessProvider.opencode_first(config.model, **dict(config.options))
    if kind == "opencode-pool":
        options = dict(config.options)
        backends = options.pop("backends", None)
        if options:
            raise ValueError("OpenCode pool only accepts the backends option")
        if not isinstance(backends, list):
            raise ValueError("OpenCode pool requires a backends list")
        return HarnessProvider.opencode_pool(backends)
    raise ValueError(f"Unknown provider kind {config.kind!r}")

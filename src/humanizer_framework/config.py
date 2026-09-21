from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .providers import ClaudeCLIProvider, CodexCLIProvider, LiteLLMProvider
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
    return FrameworkConfig(
        provider=ProviderConfig(
            kind=str(provider.get("kind", "litellm")),
            model=provider.get("model"),
            options=dict(provider.get("options", {})),
        ),
        strict=bool(data.get("strict", False)),
    )


def provider_from_config(config: ProviderConfig) -> Provider:
    kind = config.kind.lower()
    if kind == "litellm":
        if not config.model:
            raise ValueError("LiteLLM provider requires a model")
        return LiteLLMProvider(config.model, kwargs=config.options)
    if kind == "codex-cli":
        return CodexCLIProvider(**config.options)
    if kind == "claude-cli":
        return ClaudeCLIProvider(**config.options)
    raise ValueError(f"Unknown provider kind {config.kind!r}")

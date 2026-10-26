from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Any

from ..errors import ProviderExecutionError
from .base import Provider
from .cli import OpenCodeCLIProvider


class ProviderPool:
    """Round-robin pool that also fails over to the remaining providers."""

    name = "provider-pool"

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("ProviderPool requires at least one provider")
        self.providers = list(providers)
        self._next = 0
        self._lock = threading.Lock()
        self.last_provider: Provider | None = None
        self.last_provider_name: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_errors: list[str] = []

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        with self._lock:
            start = self._next
            self._next = (self._next + 1) % len(self.providers)

        errors: list[str] = []
        self.last_errors = []
        for offset in range(len(self.providers)):
            provider = self.providers[(start + offset) % len(self.providers)]
            try:
                result = provider.generate(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
                self.last_errors = errors
                self.last_provider = provider
                self.last_provider_name = getattr(provider, "name", type(provider).__name__)
                self.last_model = getattr(provider, "last_model", None) or getattr(provider, "model", None)
                self.last_usage = getattr(provider, "last_usage", None)
                return result
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', type(provider).__name__)}: {exc}")
        self.last_errors = errors
        raise ProviderExecutionError("All providers in pool failed: " + " | ".join(errors))


class HarnessProvider:
    """Ordered agent-harness fallback, normally OpenCode first."""

    name = "harness"

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("HarnessProvider requires at least one provider")
        self.providers = list(providers)
        self.last_provider: Provider | None = None
        self.last_provider_name: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_errors: list[str] = []

    @classmethod
    def opencode_first(
        cls,
        model: str,
        *,
        opencode_options: dict[str, object] | None = None,
        credentials: Sequence[dict[str, str]] | None = None,
    ) -> HarnessProvider:
        common = dict(opencode_options or {})
        opencode_providers: list[Provider] = []
        if credentials:
            for credential in credentials:
                opencode_providers.append(
                    OpenCodeCLIProvider(model=model, **common, **credential)
                )
        else:
            opencode_providers.append(OpenCodeCLIProvider(model=model, **common))

        first: Provider
        if len(opencode_providers) == 1:
            first = opencode_providers[0]
        else:
            first = ProviderPool(opencode_providers)

        return cls([first])

    @classmethod
    def opencode_pool(
        cls, backends: Sequence[dict[str, object]]
    ) -> HarnessProvider:
        """Build a rotating/failover pool containing only OpenCode processes."""

        providers: list[Provider] = []
        for backend in backends:
            options = dict(backend)
            model = options.pop("model", None)
            if not isinstance(model, str):
                raise ValueError("Every OpenCode backend requires a model")
            providers.append(OpenCodeCLIProvider(model=model, **options))
        return cls([ProviderPool(providers)])

    @classmethod
    def opencode_provider_pool(
        cls, providers: Sequence[OpenCodeCLIProvider]
    ) -> HarnessProvider:
        """Build a pool from preconfigured OpenCode API providers."""

        return cls([ProviderPool(providers)])

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        errors: list[str] = []
        self.last_errors = []
        for provider in self.providers:
            try:
                result = provider.generate(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
                self.last_errors = errors
                self.last_provider = provider
                self.last_provider_name = getattr(provider, "last_provider_name", None) or getattr(provider, "name", type(provider).__name__)
                self.last_model = getattr(provider, "last_model", None) or getattr(provider, "model", None)
                self.last_usage = getattr(provider, "last_usage", None)
                return result
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', type(provider).__name__)}: {exc}")
        self.last_errors = errors
        raise ProviderExecutionError("Every harness backend failed: " + " | ".join(errors))

from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Any

from ..errors import ProviderExecutionError
from .base import Provider
from .cli import OpenCodeCLIProvider


def _safe_failure(provider: Provider, exc: Exception) -> str:
    # Не включаем произвольный текст исключения: там могут быть ключи и данные.
    name = getattr(provider, "name", type(provider).__name__)
    return f"{name} ({type(exc).__name__})"


def _diagnostics(provider: Provider, errors: list[str]) -> dict[str, Any]:
    nested = getattr(provider, "generation_snapshot", None)
    snapshot = nested() if callable(nested) else None
    if not isinstance(snapshot, dict):
        snapshot = {}
    return {
        "provider": snapshot.get("provider")
        or getattr(provider, "name", type(provider).__name__),
        "model": snapshot.get("model") or getattr(provider, "model", None),
        "usage": snapshot.get("usage")
        if snapshot.get("usage") is not None
        else getattr(provider, "last_usage", None),
        "provider_error_count": len(errors) + int(snapshot.get("provider_error_count", 0)),
    }


class ProviderPool:
    """Пул с чередованием стартового провайдера и резервными вариантами."""

    name = "provider-pool"

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("ProviderPool requires at least one provider")
        self.providers = list(providers)
        self._next = 0
        self._lock = threading.Lock()
        self._generate_lock = threading.RLock()
        self._local = threading.local()
        self.last_provider: Provider | None = None
        self.last_provider_name: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_errors: list[str] = []

    def generation_snapshot(self) -> dict[str, Any]:
        """Диагностика именно этого потока, а не соседней генерации."""
        return dict(getattr(self._local, "snapshot", {}))

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        # Сериализация вызова защищает last_usage вложенных провайдеров.
        with self._generate_lock:
            with self._lock:
                start = self._next
                self._next = (self._next + 1) % len(self.providers)
            errors: list[str] = []
            self._local.snapshot = {}
            self.last_errors = []
            for offset in range(len(self.providers)):
                provider = self.providers[(start + offset) % len(self.providers)]
                try:
                    result = provider.generate(
                        messages, temperature=temperature, max_tokens=max_tokens
                    )
                    snapshot = _diagnostics(provider, errors)
                    self._local.snapshot = snapshot
                    self.last_errors = errors
                    self.last_provider = provider
                    self.last_provider_name = snapshot["provider"]
                    self.last_model = snapshot["model"]
                    self.last_usage = snapshot["usage"]
                    return result
                except Exception as exc:
                    errors.append(_safe_failure(provider, exc))
            self.last_errors = errors
            self._local.snapshot = {
                "provider": self.name,
                "provider_error_count": len(errors),
            }
            raise ProviderExecutionError(
                "Ни один провайдер пула не ответил: " + ", ".join(errors)
            )


class HarnessProvider:
    """Упорядоченная цепочка резервных провайдеров."""

    name = "harness"

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("HarnessProvider requires at least one provider")
        self.providers = list(providers)
        self._generate_lock = threading.RLock()
        self._local = threading.local()
        self.last_provider: Provider | None = None
        self.last_provider_name: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_errors: list[str] = []

    def generation_snapshot(self) -> dict[str, Any]:
        return dict(getattr(self._local, "snapshot", {}))

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
    def opencode_pool(cls, backends: Sequence[dict[str, object]]) -> HarnessProvider:
        """Пул процессов OpenCode с чередованием стартового варианта."""
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
        """Пул предварительно настроенных OpenCode-провайдеров."""
        return cls([ProviderPool(providers)])

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        with self._generate_lock:
            errors: list[str] = []
            self.last_errors = []
            self._local.snapshot = {}
            for provider in self.providers:
                try:
                    result = provider.generate(
                        messages, temperature=temperature, max_tokens=max_tokens
                    )
                    snapshot = _diagnostics(provider, errors)
                    self._local.snapshot = snapshot
                    self.last_errors = errors
                    self.last_provider = provider
                    self.last_provider_name = snapshot["provider"]
                    self.last_model = snapshot["model"]
                    self.last_usage = snapshot["usage"]
                    return result
                except Exception as exc:
                    errors.append(_safe_failure(provider, exc))
            self.last_errors = errors
            self._local.snapshot = {
                "provider": self.name,
                "provider_error_count": len(errors),
            }
            raise ProviderExecutionError(
                "Не удалось получить ответ от резервных провайдеров: "
                + ", ".join(errors)
            )

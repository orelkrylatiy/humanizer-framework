from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..env import load_env
from ..errors import ProviderExecutionError

_DEFAULT_KEY_ENV_VARS = ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "ZAI_API_KEY")


@dataclass(slots=True)
class ZaiAnthropicProvider:
    """Direct-HTTP provider for the Anthropic-compatible Z.AI endpoint.

    Talks straight to ``{base_url}/v1/messages`` (no subprocess), enables
    GLM thinking for models that require it, and resolves
    the key from the first set env var in ``api_key_env``. Never logs or
    embeds the key value in errors.
    """

    model: str = "glm-5.3-flash"
    base_url: str = "https://api.z.ai/api/anthropic"
    api_key_env: tuple[str, ...] = _DEFAULT_KEY_ENV_VARS
    api_key: str | None = None
    timeout_seconds: int = 120
    max_tokens_floor: int = 3000
    name: str = "zai-http"

    def _resolve_key(self) -> str:
        if self.api_key:
            return self.api_key
        load_env()
        for var in self.api_key_env:
            value = os.environ.get(var)
            if value:
                return value
        names = ", ".join(self.api_key_env)
        raise ProviderExecutionError(f"zai-http: no API key found (checked env vars: {names})")

    @staticmethod
    def _post(url: str, payload: dict, headers: dict[str, str], timeout: int) -> dict:
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        key = self._resolve_key()
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        rest = [m for m in messages if m["role"] != "system"]
        user = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in rest)
        payload = {
            "model": self.model,
            "system": system,
            "max_tokens": max(self.max_tokens_floor, max_tokens),
            "temperature": temperature,
            "messages": [{"role": "user", "content": user}],
            # Current GLM models may reject thinking=disabled. Keep the
            # provider's default usable without per-project overrides.
            "thinking": {"type": "enabled"},
        }
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "Authorization": f"Bearer {key}",
        }
        try:
            data = self._post(
                self.base_url.rstrip("/") + "/v1/messages", payload, headers, self.timeout_seconds
            )
        except ProviderExecutionError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(f"zai-http request failed: {exc}") from exc
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ).strip()
        if not text:
            raise ProviderExecutionError(f"zai-http returned empty text for model {self.model}")
        return text

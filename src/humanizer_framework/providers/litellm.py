from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_RESERVED_KWARGS = {"model", "messages", "temperature", "max_tokens"}


@dataclass(slots=True)
class LiteLLMProvider:
    """Optional provider backed by LiteLLM."""

    model: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    name: str = "litellm"
    last_usage: dict | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        conflicts = sorted(_RESERVED_KWARGS & self.kwargs.keys())
        if conflicts:
            joined = ", ".join(conflicts)
            raise ValueError(
                f"LiteLLMProvider kwargs cannot override framework-owned fields: {joined}"
            )

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        try:
            from litellm import completion
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("LiteLLM is optional. Install humanizer-framework[llm].") from exc

        response = completion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **self.kwargs,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            if isinstance(usage, dict):
                self.last_usage = usage
            elif hasattr(usage, "model_dump"):
                self.last_usage = usage.model_dump()
            else:
                self.last_usage = {
                    key: getattr(usage, key)
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                    if getattr(usage, key, None) is not None
                }
        else:
            self.last_usage = None
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LiteLLM provider returned an empty response")
        return content.strip()

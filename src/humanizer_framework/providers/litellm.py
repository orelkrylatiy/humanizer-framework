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
            raise RuntimeError(
                "LiteLLM is optional. Install humanizer-framework[llm]."
            ) from exc

        response = completion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **self.kwargs,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LiteLLM provider returned an empty response")
        return content.strip()

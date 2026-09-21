from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LiteLLMProvider:
    """Optional provider backed by LiteLLM.

    Examples of model strings include OpenAI, Anthropic, Gemini, Ollama and
    Z.AI/GLM models such as zai/glm-4.7. The framework deliberately does
    not hardcode a model catalog because provider model names change faster
    than the communication API.
    """

    model: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    name: str = "litellm"

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

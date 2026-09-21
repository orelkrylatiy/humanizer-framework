from __future__ import annotations

from typing import Protocol


class Provider(Protocol):
    name: str

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str: ...

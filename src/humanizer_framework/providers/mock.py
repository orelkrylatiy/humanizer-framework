from __future__ import annotations


class MockProvider:
    name = "mock"

    def __init__(self, outputs: str | list[str]):
        self.outputs = [outputs] if isinstance(outputs, str) else list(outputs)
        self.calls: list[list[dict[str, str]]] = []

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        del temperature, max_tokens
        self.calls.append(messages)
        if not self.outputs:
            raise RuntimeError("MockProvider has no outputs left")
        return self.outputs.pop(0)

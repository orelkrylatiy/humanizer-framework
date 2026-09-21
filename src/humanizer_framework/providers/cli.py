from __future__ import annotations

import subprocess
from dataclasses import dataclass


def _flatten_messages(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(
        f"{message.get('role', 'user').upper()}\n{message.get('content', '')}"
        for message in messages
    )


@dataclass(slots=True)
class CommandProvider:
    command: list[str]
    name: str = "command"
    timeout_seconds: int = 120
    use_stdin: bool = True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        del temperature, max_tokens
        prompt = _flatten_messages(messages)
        cmd = list(self.command)
        if self.use_stdin:
            completed = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                check=True,
                timeout=self.timeout_seconds,
            )
        else:
            completed = subprocess.run(
                [*cmd, prompt],
                text=True,
                capture_output=True,
                check=True,
                timeout=self.timeout_seconds,
            )
        output = completed.stdout.strip()
        if not output:
            raise RuntimeError(f"{self.name} returned an empty response")
        return output


class CodexCLIProvider(CommandProvider):
    def __init__(self, *, timeout_seconds: int = 120):
        super().__init__(
            command=["codex", "exec", "--ephemeral", "-"],
            name="codex-cli",
            timeout_seconds=timeout_seconds,
            use_stdin=True,
        )


class ClaudeCLIProvider(CommandProvider):
    def __init__(self, *, timeout_seconds: int = 120):
        super().__init__(
            command=["claude", "-p", "--output-format", "text"],
            name="claude-cli",
            timeout_seconds=timeout_seconds,
            use_stdin=False,
        )

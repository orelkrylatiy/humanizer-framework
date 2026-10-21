from __future__ import annotations

import tempfile
from pathlib import Path

from ..errors import ProviderExecutionError
from .cli import _flatten_messages, _replace_executable, _run_command


class ClaudeCodeCLIProvider:
    """Claude Code CLI adapter using non-interactive print mode.

    Spawns ``claude -p`` in an isolated working directory so caller project
    context (CLAUDE.md, settings) never leaks into generation. Credentials
    come from the CLI's own configuration; nothing is stored here.
    """

    name = "claude-cli"

    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: int = 120,
        executable: str = "claude",
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.executable = executable

    @property
    def command(self) -> list[str]:
        command = [self.executable, "-p", "--output-format", "text"]
        if self.model:
            command.extend(["--model", self.model])
        return command

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        del temperature, max_tokens
        prompt = _flatten_messages(messages)
        with tempfile.TemporaryDirectory(prefix="humanizer-claude-") as directory:
            completed = _run_command(
                _replace_executable(self.command),
                prompt=prompt,
                timeout_seconds=self.timeout_seconds,
                cwd=Path(directory),
                check=True,
            )
        output = completed.stdout.strip()
        if not output:
            raise ProviderExecutionError("Claude CLI returned an empty response")
        return output

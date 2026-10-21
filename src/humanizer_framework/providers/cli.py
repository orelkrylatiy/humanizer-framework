from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..errors import ProviderExecutionError


def _flatten_messages(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(
        f"{message.get('role', 'user').upper()}\n{message.get('content', '')}"
        for message in messages
    )


def _resolve_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise ProviderExecutionError(f"CLI executable {name!r} was not found on PATH")
    return resolved


def _run_command(
    command: list[str],
    *,
    prompt: str,
    timeout_seconds: int,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=check,
            timeout=timeout_seconds,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderExecutionError(
            f"CLI provider timed out after {timeout_seconds} seconds"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = stderr[-1000:] if stderr else f"exit code {exc.returncode}"
        raise ProviderExecutionError(f"CLI provider failed: {detail}") from exc
    except OSError as exc:
        raise ProviderExecutionError(f"Could not start CLI provider: {exc}") from exc


@dataclass(slots=True)
class CommandProvider:
    """Generic command adapter for callers with an existing text-only CLI."""

    command: list[str]
    name: str = "command"
    timeout_seconds: int = 120
    use_stdin: bool = True
    parser: Callable[[str], str] | None = None

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        del temperature, max_tokens
        prompt = _flatten_messages(messages)
        command = list(self.command) if self.use_stdin else [*self.command, prompt]
        completed = _run_command(
            command,
            prompt=prompt if self.use_stdin else "",
            timeout_seconds=self.timeout_seconds,
        )
        output = completed.stdout.strip()
        if self.parser is not None:
            output = self.parser(output).strip()
        if not output:
            raise ProviderExecutionError(f"{self.name} returned an empty response")
        return output


class OpenCodeCLIProvider:
    """OpenCode agent-harness adapter using non-interactive JSONL mode.

    ``model`` is intentionally required. OpenCode otherwise falls back to its
    configured default, which may select a different provider than the caller
    expects. A credential can be injected from a named environment variable;
    its value is never stored in framework configuration.
    """

    name = "opencode-cli"

    def __init__(
        self,
        *,
        model: str,
        agent: str | None = None,
        variant: str | None = None,
        timeout_seconds: int = 120,
        executable: str = "opencode",
        credential_source_env: str | None = None,
        credential_source_file: str | Path | None = None,
        credential_source_json_path: str | None = None,
        credential_target_env: str | None = None,
        isolate_credentials: bool = True,
        opencode_config: dict[str, object] | None = None,
    ) -> None:
        if "/" not in model:
            raise ValueError("OpenCode model must use the provider/model format")
        source_count = int(bool(credential_source_env)) + int(bool(credential_source_file))
        if source_count > 1:
            raise ValueError("Use only one credential source")
        if bool(source_count) != bool(credential_target_env):
            raise ValueError(
                "A credential source and credential_target_env must be set together"
            )
        if credential_source_file and not credential_source_json_path:
            raise ValueError(
                "credential_source_json_path is required with credential_source_file"
            )
        self.model = model
        self.agent = agent
        self.variant = variant
        self.timeout_seconds = timeout_seconds
        self.executable = executable
        self.credential_source_env = credential_source_env
        self.credential_source_file = credential_source_file
        self.credential_source_json_path = credential_source_json_path
        self.credential_target_env = credential_target_env
        self.isolate_credentials = isolate_credentials
        self.opencode_config = dict(opencode_config or {})

    @property
    def command(self) -> list[str]:
        command = [self.executable, "run", "--standalone", "--format", "json"]
        command.extend(["--model", self.model])
        if self.agent:
            command.extend(["--agent", self.agent])
        if self.variant:
            command.extend(["--variant", self.variant])
        return command

    @property
    def use_stdin(self) -> bool:
        return True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        del temperature, max_tokens
        prompt = _flatten_messages(messages)
        environment = os.environ.copy()
        config = dict(self.opencode_config)
        config["permission"] = {"*": "deny"}
        environment["OPENCODE_CONFIG_CONTENT"] = json.dumps(
            config, separators=(",", ":")
        )
        credential = self._load_credential()
        if credential is not None and self.credential_target_env:
            environment[self.credential_target_env] = credential
        with tempfile.TemporaryDirectory(prefix="humanizer-opencode-") as directory:
            if credential is not None and self.isolate_credentials:
                environment["OPENCODE_DB"] = str(Path(directory) / "opencode.db")
            completed = _run_command(
                _replace_executable(self.command),
                prompt=prompt,
                timeout_seconds=self.timeout_seconds,
                cwd=directory,
                env=environment,
                check=False,
            )
        output = _parse_opencode_jsonl(completed.stdout)
        if not output:
            raise ProviderExecutionError("OpenCode CLI returned no assistant text")
        return output

    def _load_credential(self) -> str | None:
        if self.credential_source_env:
            credential = os.environ.get(self.credential_source_env)
            if not credential:
                raise ProviderExecutionError(
                    f"Credential environment variable {self.credential_source_env!r} is not set"
                )
            return credential
        if self.credential_source_file and self.credential_source_json_path:
            try:
                value: object = json.loads(
                    Path(self.credential_source_file)
                    .expanduser()
                    .read_text(encoding="utf-8")
                )
                for key in self.credential_source_json_path.split("."):
                    if not isinstance(value, dict):
                        raise KeyError(key)
                    value = value[key]
            except (OSError, json.JSONDecodeError, KeyError) as exc:
                raise ProviderExecutionError(
                    "Could not load the configured OpenCode credential source"
                ) from exc
            if not isinstance(value, str) or not value:
                raise ProviderExecutionError(
                    "The configured OpenCode credential source is empty"
                )
            return value
        return None


def _replace_executable(command: list[str]) -> list[str]:
    if not command:
        raise ProviderExecutionError("CLI provider command is empty")
    return [_resolve_executable(command[0]), *command[1:]]


def _parse_opencode_jsonl(output: str) -> str:
    chunks: list[str] = []
    provider_error: str | None = None
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProviderExecutionError("OpenCode CLI returned invalid JSONL output") from exc
        part = event.get("part", {})
        if event.get("type") == "text" and isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text:
                chunks.append(text)
        if event.get("type") == "error":
            error = event.get("error", {})
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message:
                    provider_error = message[-1000:]
    if provider_error and not chunks:
        raise ProviderExecutionError(f"OpenCode provider failed: {provider_error}")
    return "".join(chunks).strip()

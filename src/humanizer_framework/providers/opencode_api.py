from __future__ import annotations

from pathlib import Path

from .cli import OpenCodeCLIProvider


def openai_api_provider(
    model: str = "gpt-4.1-mini",
    *,
    credential_source_env: str | None = None,
    credential_source_file: str | Path | None = None,
    credential_source_json_path: str | None = None,
    timeout_seconds: int = 120,
) -> OpenCodeCLIProvider:
    """Create an isolated OpenCode backend for the OpenAI API."""

    credential_source_env = credential_source_env or (
        None if credential_source_file else "OPENAI_API_KEY"
    )
    return OpenCodeCLIProvider(
        model=f"openai-api/{model}",
        timeout_seconds=timeout_seconds,
        credential_source_env=credential_source_env,
        credential_source_file=credential_source_file,
        credential_source_json_path=credential_source_json_path,
        credential_target_env="OPENAI_API_KEY",
        opencode_config={
            "provider": {
                "openai-api": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "OpenAI API",
                    "options": {
                        "baseURL": "https://api.openai.com/v1",
                        "apiKey": "{env:OPENAI_API_KEY}",
                    },
                    "models": {model: {"name": model}},
                }
            }
        },
    )


def zai_api_provider(
    model: str = "glm-5.3-flash",
    *,
    credential_source_env: str | None = None,
    credential_source_file: str | Path | None = None,
    credential_source_json_path: str | None = None,
    timeout_seconds: int = 120,
) -> OpenCodeCLIProvider:
    """Create an isolated OpenCode backend for the Z.AI Coding API."""

    credential_source_env = credential_source_env or (
        None if credential_source_file else "ZAI_API_KEY"
    )
    return OpenCodeCLIProvider(
        model=f"zai-coding/{model}",
        timeout_seconds=timeout_seconds,
        credential_source_env=credential_source_env,
        credential_source_file=credential_source_file,
        credential_source_json_path=credential_source_json_path,
        credential_target_env="ZAI_API_KEY",
        opencode_config={
            "provider": {
                "zai-coding": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Z.AI Coding",
                    "options": {
                        "baseURL": "https://api.z.ai/api/coding/paas/v4",
                        "apiKey": "{env:ZAI_API_KEY}",
                    },
                    "models": {model: {"name": model}},
                }
            }
        },
    )

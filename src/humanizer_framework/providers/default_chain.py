from __future__ import annotations

import os

from .base import Provider
from .cli import OpenCodeCLIProvider
from .harness import HarnessProvider
from .opencode_api import openai_api_provider
from .zai_http import ZaiAnthropicProvider

_DEFAULT_OPENCODE_MODEL = "openai/gpt-5.6-luna-fast"
_DEFAULT_OPENAI_API_MODEL = "gpt-4.1-mini"


def default_provider() -> Provider:
    """Ordered fallback chain used as the framework's generation backend.

    OpenCode (OpenAI model, subscription auth) first, then the Z.AI endpoint
    (GLM), then the OpenAI API directly (``OPENAI_API_KEY``). Every backend
    resolves its own credentials from the environment at call time; a missing
    key or binary fails that leg only and the next one takes over.
    """

    opencode_model = os.environ.get("HUMANIZER_OPENCODE_MODEL", _DEFAULT_OPENCODE_MODEL)
    openai_api_model = os.environ.get("HUMANIZER_OPENAI_API_MODEL", _DEFAULT_OPENAI_API_MODEL)
    return HarnessProvider(
        [
            OpenCodeCLIProvider(model=opencode_model),
            ZaiAnthropicProvider(),
            openai_api_provider(openai_api_model, credential_source_env="OPENAI_API_KEY"),
        ]
    )

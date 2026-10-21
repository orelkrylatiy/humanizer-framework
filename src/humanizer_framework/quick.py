from __future__ import annotations

from typing import Any

from .framework import CommunicationFramework
from .models import CommunicationRequest, CommunicationResult, Message, MessageType, VoiceProfile
from .providers import Provider, default_provider


_ASSISTANT_ROLES = {"me", "assistant", "bot", "seller", "agent", "я", "бот"}


def _as_message(item: Any) -> Message:
    """Accept Message, (role, text) pairs or bare strings as incoming turns."""

    if isinstance(item, Message):
        return item
    if isinstance(item, (tuple, list)) and len(item) == 2:
        role, text = item
        normalized = str(role).strip().lower()
        side = "assistant" if normalized in _ASSISTANT_ROLES else "user"
        return Message(side, str(text))
    return Message("user", str(item))


def write(
    what: str,
    *,
    channel: str = "generic",
    domain: str = "generic",
    message_type: MessageType | str = MessageType.CHAT_REPLY,
    language: str = "ru",
    profile: str = "default",
    facts: dict[str, Any] | None = None,
    dialogue: list[Any] | None = None,
    business_rules: list[str] | None = None,
    voice: VoiceProfile | None = None,
    provider: Provider | None = None,
    framework: CommunicationFramework | None = None,
) -> CommunicationResult:
    """One-call generation: describe the goal, get ready validated text.

    ``what`` is a plain-language description of what this message should
    achieve. The default backend is the ordered fallback chain from
    :func:`humanizer_framework.providers.default_provider`.
    """

    active = framework
    if active is None:
        active = CommunicationFramework(provider if provider is not None else default_provider())
    rules = [f"Message goal: {what}", *(business_rules or [])]
    request = CommunicationRequest(
        channel=channel,
        domain=domain,
        message_type=MessageType(message_type),
        language=language,
        profile=profile,
        conversation=[_as_message(item) for item in (dialogue or [])],
        context=dict(facts or {}),
        business_rules=rules,
        voice=voice,
    )
    return active.generate(request)

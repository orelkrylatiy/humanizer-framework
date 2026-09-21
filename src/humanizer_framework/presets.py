from __future__ import annotations

from .models import CommunicationRequest, Message, MessageType, VoiceProfile


def tutoring_request(
    *,
    channel: str,
    message_type: MessageType | str,
    profile: str,
    conversation: list[Message],
    context: dict | None = None,
    business_rules: list[str] | None = None,
    voice: VoiceProfile | None = None,
    language: str = "ru",
) -> CommunicationRequest:
    return CommunicationRequest(
        channel=channel,
        domain="tutoring",
        message_type=message_type,
        language=language,
        profile=profile,
        conversation=conversation,
        context=context or {},
        business_rules=business_rules or [],
        voice=voice,
    )


def job_search_request(
    *,
    channel: str,
    message_type: MessageType | str,
    profile: str,
    conversation: list[Message],
    context: dict | None = None,
    business_rules: list[str] | None = None,
    voice: VoiceProfile | None = None,
    language: str = "ru",
) -> CommunicationRequest:
    return CommunicationRequest(
        channel=channel,
        domain="job_search",
        message_type=message_type,
        language=language,
        profile=profile,
        conversation=conversation,
        context=context or {},
        business_rules=business_rules or [],
        voice=voice,
    )

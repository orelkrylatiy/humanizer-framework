from __future__ import annotations

import re

from .models import (
    CommunicationRequest,
    ConversationAct,
    ConversationStage,
    MessageType,
    Plan,
    ReplyAction,
    TargetLength,
)

_SCHEDULING_PATTERNS = {
    "default": re.compile(
        r"(когда\s+(?:вам\s+)?удобно|во\s+сколько|можно\s+(?:сегодня|завтра)|"
        r"(?:сегодня|завтра)\s+(?:в|после|до)|(?:понедельник|вторник|сред[ау]|четверг|"
        r"пятниц[ау]|суббот[ау]|воскресень[ея])\s+(?:в|после|до)|\bв\s+\d{1,2}(?::\d{2})?\b|"
        r"\b(schedule|availability|available|tomorrow\s+at|today\s+at|when\s+are\s+you\s+available)\b)",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"(cu[aá]ndo\s+(?:te|le|os)?\s*(?:viene\s+bien|conviene)|a\s+qu[eé]\s+hora|"
        r"disponibilidad|(?:hoy|mañana)\s+(?:a\s+las?|despu[eé]s\s+de|antes\s+de))",
        re.IGNORECASE,
    ),
    "zh": re.compile(r"(什么时候|几点|今天.{0,8}点|明天.{0,8}点|哪天方便|什么时间方便)"),
}

_OBJECTION_PATTERNS = {
    "default": re.compile(
        r"\b(дорого|не уверен|не уверена|сомнева|не подходит|не хочу|слишком|expensive|"
        r"not sure|doesn.t work|too much)\b",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"\b(caro|cara|demasiado|no\s+estoy\s+segur[oa]|no\s+me\s+conviene|no\s+quiero)\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(r"(太贵|不确定|不太确定|不合适|不想|太多)"),
}

_AGREEMENT_PATTERNS = {
    "default": re.compile(
        r"^\s*(да|давайте|ок|окей|хорошо|согласен|согласна|подходит|yes|ok|okay|sounds good)\b",
        re.IGNORECASE,
    ),
    "es": re.compile(r"^\s*(s[ií]|vale|de\s+acuerdo|perfecto|perfecta|me\s+parece\s+bien)\b", re.IGNORECASE),
    "zh": re.compile(r"^\s*(好|好的|可以|行|没问题|同意)"),
}


def _latest_user_text(request: CommunicationRequest) -> str:
    for message in reversed(request.conversation):
        if message.role.lower() in {"user", "client", "human"}:
            return message.content.strip()
    return ""


def _language_key(language: str) -> str:
    return language.lower().split("-", 1)[0].split("_", 1)[0]


def _matches(patterns: dict[str, re.Pattern[str]], text: str, language: str) -> bool:
    lang = _language_key(language)
    return bool(patterns["default"].search(text) or patterns.get(lang, re.compile(r"(?!x)x")).search(text))


def _is_question(text: str, language: str) -> bool:
    if "?" in text or "？" in text:
        return True
    if _language_key(language) == "zh":
        return bool(re.search(r"(吗|么|呢)\s*[。！!]?\s*$", text))
    return False


def _target_length(text: str, message_type: MessageType) -> TargetLength:
    if message_type in {MessageType.OUTREACH, MessageType.APPLICATION}:
        return TargetLength.MEDIUM
    if len(text) <= 80:
        return TargetLength.VERY_SHORT
    if len(text) <= 220:
        return TargetLength.SHORT
    return TargetLength.MEDIUM


def plan(request: CommunicationRequest) -> Plan:
    message_type = MessageType(request.message_type)
    latest = _latest_user_text(request)

    if message_type == MessageType.OUTREACH:
        max_chars = 420 if request.domain == "tutoring" else 520
        return Plan(
            act=ConversationAct.UNKNOWN,
            stage=ConversationStage.NEW,
            action=ReplyAction.PITCH,
            target_length=TargetLength.MEDIUM,
            ask_question=True,
            allow_cta=True,
            max_chars=max_chars,
            rationale="first contact may explain relevance and invite a reply",
        )

    if message_type == MessageType.APPLICATION:
        return Plan(
            act=ConversationAct.UNKNOWN,
            stage=ConversationStage.NEW,
            action=ReplyAction.PITCH,
            target_length=TargetLength.MEDIUM,
            ask_question=False,
            allow_cta=False,
            max_chars=700,
            rationale="job application should be tailored but not force a chat CTA",
        )

    if message_type == MessageType.FOLLOW_UP:
        return Plan(
            act=ConversationAct.UNKNOWN,
            stage=ConversationStage.QUALIFIED,
            action=ReplyAction.FOLLOW_UP,
            target_length=TargetLength.SHORT,
            ask_question=False,
            allow_cta=True,
            max_chars=260,
            rationale="follow-up should be easy to ignore and easy to answer",
        )

    if message_type == MessageType.SCHEDULING or _matches(
        _SCHEDULING_PATTERNS, latest, request.language
    ):
        return Plan(
            act=ConversationAct.SCHEDULING,
            stage=ConversationStage.SCHEDULING,
            action=ReplyAction.SCHEDULE,
            target_length=TargetLength.SHORT,
            ask_question=True,
            allow_cta=True,
            max_chars=260,
            rationale="the user is discussing timing or logistics",
        )

    if message_type == MessageType.OBJECTION or _matches(
        _OBJECTION_PATTERNS, latest, request.language
    ):
        return Plan(
            act=ConversationAct.OBJECTION,
            stage=ConversationStage.DISCOVERY,
            action=ReplyAction.HANDLE_OBJECTION,
            target_length=TargetLength.SHORT,
            ask_question=False,
            allow_cta=False,
            max_chars=280,
            rationale="address the specific concern before advancing the conversation",
        )

    if latest and _is_question(latest, request.language):
        return Plan(
            act=ConversationAct.QUESTION,
            stage=ConversationStage.DISCOVERY,
            action=ReplyAction.ANSWER,
            target_length=_target_length(latest, message_type),
            ask_question=False,
            allow_cta=False,
            max_chars=320 if len(latest) > 120 else 220,
            rationale="answer the current question before adding any next step",
        )

    if _matches(_AGREEMENT_PATTERNS, latest, request.language):
        return Plan(
            act=ConversationAct.AGREEMENT,
            stage=ConversationStage.READY,
            action=ReplyAction.ACKNOWLEDGE,
            target_length=TargetLength.VERY_SHORT,
            ask_question=False,
            allow_cta=True,
            max_chars=180,
            rationale="acknowledge agreement without over-explaining",
        )

    return Plan(
        act=ConversationAct.DISCLOSURE,
        stage=ConversationStage.DISCOVERY,
        action=ReplyAction.ACKNOWLEDGE,
        target_length=_target_length(latest, message_type),
        ask_question=False,
        allow_cta=False,
        max_chars=180 if len(latest) <= 120 else 260,
        rationale="a disclosure usually needs a direct acknowledgement, not another sales block",
    )

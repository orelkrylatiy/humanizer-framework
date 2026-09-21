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

_SCHEDULING_RE = re.compile(
    r"\b(когда|во сколько|время|сегодня|завтра|понедельник|вторник|сред[ау]|четверг|"
    r"пятниц|суббот|воскрес|schedule|when|time|tomorrow|today)\b",
    re.IGNORECASE,
)
_OBJECTION_RE = re.compile(
    r"\b(дорого|не уверен|не уверена|сомнева|не подходит|не хочу|слишком|expensive|"
    r"not sure|doesn.t work|too much)\b",
    re.IGNORECASE,
)
_AGREEMENT_RE = re.compile(
    r"^\s*(да|давайте|ок|окей|хорошо|согласен|согласна|подходит|yes|ok|okay|sounds good)\b",
    re.IGNORECASE,
)


def _latest_user_text(request: CommunicationRequest) -> str:
    for message in reversed(request.conversation):
        if message.role in {"user", "client", "human"}:
            return message.content.strip()
    return ""


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

    if message_type == MessageType.SCHEDULING or _SCHEDULING_RE.search(latest):
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

    if message_type == MessageType.OBJECTION or _OBJECTION_RE.search(latest):
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

    if latest and "?" in latest:
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

    if _AGREEMENT_RE.search(latest):
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

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    OUTREACH = "outreach"
    APPLICATION = "application"
    CHAT_REPLY = "chat_reply"
    FOLLOW_UP = "follow_up"
    SCHEDULING = "scheduling"
    OBJECTION = "objection"


class ConversationAct(StrEnum):
    DISCLOSURE = "disclosure"
    QUESTION = "question"
    OBJECTION = "objection"
    AGREEMENT = "agreement"
    SCHEDULING = "scheduling"
    UNKNOWN = "unknown"


class ConversationStage(StrEnum):
    NEW = "new"
    DISCOVERY = "discovery"
    QUALIFIED = "qualified"
    READY = "ready"
    SCHEDULING = "scheduling"
    CLOSED = "closed"


class ReplyAction(StrEnum):
    PITCH = "pitch"
    ACKNOWLEDGE = "acknowledge"
    ANSWER = "answer"
    CLARIFY = "clarify"
    HANDLE_OBJECTION = "handle_objection"
    SCHEDULE = "schedule"
    FOLLOW_UP = "follow_up"


class TargetLength(StrEnum):
    VERY_SHORT = "very_short"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


@dataclass(slots=True)
class Message:
    role: str
    content: str


@dataclass(slots=True)
class VoiceProfile:
    id: str = "default"
    description: str = ""
    prefer: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StyleConstraints:
    max_chars: int = 320
    max_questions: int = 1
    forbid_em_dash: bool = True
    forbid_colon: bool = False
    replace_yo: bool = True
    similarity_threshold: float = 0.86
    max_voice_examples: int = 3


@dataclass(slots=True)
class CommunicationRequest:
    channel: str
    domain: str
    message_type: MessageType | str
    language: str = "ru"
    profile: str = "default"
    conversation: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    business_rules: list[str] = field(default_factory=list)
    voice: VoiceProfile | None = None
    constraints: StyleConstraints | None = None


@dataclass(slots=True)
class Plan:
    act: ConversationAct
    stage: ConversationStage
    action: ReplyAction
    target_length: TargetLength
    ask_question: bool
    allow_cta: bool
    max_chars: int
    rationale: str = ""


@dataclass(slots=True)
class PromptPackage:
    system: str
    messages: list[dict[str, str]]
    plan: Plan
    constraints: StyleConstraints
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    hard: bool = False


@dataclass(slots=True)
class CommunicationResult:
    text: str
    plan: Plan
    issues: list[ValidationIssue]
    rewritten: bool
    provider: str | None = None
    prompt_version: str = "v0.1"

    @property
    def valid(self) -> bool:
        return not any(issue.hard for issue in self.issues)

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import CommunicationRequest, Plan, StyleConstraints, ValidationIssue

_CHATBOT_RESIDUE = (
    "great question",
    "i hope this helps",
    "let me know if",
    "would you like me to",
    "отличный вопрос",
    "надеюсь, это поможет",
)
_STAGED_OPENERS = (
    "давайте разберемся",
    "давайте разберёмся",
    "вот что важно",
    "честно говоря",
    "let's dive in",
    "here's what you need to know",
)
_CTA_MARKERS = (
    "когда вам удобно",
    "когда удобно",
    "давайте начнем с пробного",
    "давайте начнём с пробного",
    "пробном занятии",
    "пробном уроке",
    "when would be convenient",
    "when are you available",
)


def _replace_stylistic_colons(text: str) -> str:
    # Keep time separators and URL schemes intact. Only prose colons are style-normalized.
    return re.sub(r"(?<!\d):(?!\d|//)", ",", text)


def _has_stylistic_colon(text: str) -> bool:
    return re.search(r"(?<!\d):(?!\d|//)", text) is not None


def normalize_output(text: str, constraints: StyleConstraints, language: str) -> str:
    value = text.strip()
    if constraints.replace_yo and language.lower().startswith("ru"):
        value = value.replace("ё", "е").replace("Ё", "Е")
    if constraints.forbid_em_dash:
        value = value.replace("—", "-").replace("–", "-")
    if constraints.forbid_colon:
        value = _replace_stylistic_colons(value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r" {2,}", " ", value)
    return value.strip()


def _skeleton(text: str) -> str:
    value = text.lower()
    value = re.sub(r"https?://\S+", "<url>", value)
    value = re.sub(r"\b\d+[\d\s:.,-]*\b", "<num>", value)
    value = re.sub(r"[^\w\s<>]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _recent_assistant_messages(request: CommunicationRequest) -> list[str]:
    assistant_roles = {"assistant", "seller", "agent", "bot"}
    return [
        m.content
        for m in request.conversation[-20:]
        if m.role.lower() in assistant_roles
    ]


def _question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def validate_output(
    text: str,
    request: CommunicationRequest,
    plan: Plan,
    constraints: StyleConstraints,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    lower = text.lower()

    if not text.strip():
        issues.append(ValidationIssue("empty_message", "generated message is empty", hard=True))
        return issues

    if len(text) > constraints.max_chars:
        issues.append(
            ValidationIssue(
                "too_long",
                f"message has {len(text)} characters, budget is {constraints.max_chars}",
                hard=True,
            )
        )
    questions = _question_count(text)
    if questions > constraints.max_questions:
        issues.append(ValidationIssue("too_many_questions", "too many questions", hard=True))
    if not plan.ask_question and questions:
        issues.append(
            ValidationIssue(
                "unplanned_question",
                "planner did not request a question",
                hard=True,
            )
        )
    if constraints.forbid_em_dash and ("—" in text or "–" in text):
        issues.append(ValidationIssue("forbidden_dash", "contains a forbidden long dash", hard=True))
    if constraints.forbid_colon and _has_stylistic_colon(text):
        issues.append(ValidationIssue("forbidden_colon", "contains a forbidden prose colon", hard=True))
    if constraints.replace_yo and request.language.lower().startswith("ru") and re.search(r"[ёЁ]", text):
        issues.append(ValidationIssue("yo_not_normalized", "contains yo character", hard=True))
    if any(marker in lower for marker in _CHATBOT_RESIDUE):
        issues.append(ValidationIssue("chatbot_residue", "contains a generic chatbot wrapper"))
    if any(marker in lower for marker in _STAGED_OPENERS):
        issues.append(ValidationIssue("staged_opener", "contains a staged opener"))
    if not plan.allow_cta and any(marker in lower for marker in _CTA_MARKERS):
        issues.append(ValidationIssue("unplanned_cta", "contains a CTA that the planner did not allow", hard=True))

    client_name = str(request.context.get("client_name", "")).strip()
    if (
        str(request.message_type) == "outreach"
        and request.domain == "tutoring"
        and client_name
        and client_name.lower() not in lower
    ):
        issues.append(
            ValidationIssue(
                "missing_client_name",
                "known client name is missing from first tutoring outreach",
                hard=True,
            )
        )
    if (
        str(request.message_type) == "outreach"
        and client_name
        and lower.count(client_name.lower()) > 1
    ):
        issues.append(
            ValidationIssue(
                "repeated_client_name",
                "known client name is repeated in first outreach",
            )
        )
    if (
        str(request.message_type) == "outreach"
        and len(text) >= 180
        and "\n\n" not in text
    ):
        issues.append(
            ValidationIssue(
                "dense_outreach",
                "long first outreach should use whitespace between distinct ideas",
            )
        )

    current = _skeleton(text)
    for previous in _recent_assistant_messages(request):
        previous_skeleton = _skeleton(previous)
        ratio = SequenceMatcher(None, current, previous_skeleton).ratio()
        if (
            ratio >= constraints.similarity_threshold
            and min(len(current), len(previous_skeleton)) >= 30
        ):
            issues.append(
                ValidationIssue(
                    "template_similarity",
                    f"too similar to a recent outgoing message ({ratio:.2f})",
                )
            )
            break
    return issues

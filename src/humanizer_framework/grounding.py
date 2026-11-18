"""Осторожные проверки фактов для автономной переписки.

Это НЕ универсальная верификация правды. Проверки находят отдельные виды
неподтвержденных утверждений, а источником истины служит контекст продукта.
"""

from __future__ import annotations

import json
import re

from .models import CommunicationRequest, ValidationIssue

_DIGITS = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?::\d{2})?(?![\w])")
_URL_EMAIL = re.compile(r"(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.\w+")
_NUMBER_WORDS = {
    "один": "1",
    "одна": "1",
    "одно": "1",
    "два": "2",
    "две": "2",
    "три": "3",
    "четыре": "4",
    "пять": "5",
    "пяти": "5",
    "шесть": "6",
    "шести": "6",
    "семь": "7",
    "семи": "7",
    "восемь": "8",
    "восьми": "8",
    "девять": "9",
    "девяти": "9",
    "десять": "10",
    "десяти": "10",
    "двенадцать": "12",
    "двенадцати": "12",
}
_METRIC_WORDS = re.compile(
    r"\b(" + "|".join(_NUMBER_WORDS) + r")\s+"
    r"(?:лет|год(?:а|ов)?|месяц(?:ев|а)?|час(?:ов|а)?|"
    r"ученик(?:ов|а)?|клиент(?:ов|а)?|проект(?:ов|а)?|"
    r"сотрудник(?:ов|а)?|человек|рубл(?:ей|я|ь)|тысяч(?:и)?|"
    r"заняти(?:й|я)|урок(?:ов|а)?)\b",
    re.IGNORECASE,
)
_AVAILABILITY = re.compile(
    r"\b(?:могу|смогу|свободен|свободна|доступен|доступна)\b"
    r"[^.!?\n]{0,50}\b(?:сегодня|завтра|послезавтра|"
    r"в\s+\d{1,2}(?::\d{2})?|в\s+(?:понедельник|вторник|среду|четверг|"
    r"пятницу|субботу|воскресенье))\b",
    re.IGNORECASE,
)
_HIGH_RISK_CLAIMS = (
    re.compile(r"\b(?:руководил[аи]?|управлял[аи]?|сертифицирован[а]?|"
               r"лицензирован[а]?|гарантирую|гарантируем)\b", re.IGNORECASE),
)
_SCHEDULE_KEYS = ("availability", "slots", "schedule", "free_times", "confirmed_time", "calendar")


def _norm(text: str) -> str:
    return text.casefold().replace("ё", "е")


def _numeric_facts(text: str) -> set[str]:
    text = _URL_EMAIL.sub(" ", _norm(text))
    found = set(_DIGITS.findall(text))
    for match in _METRIC_WORDS.finditer(text):
        found.add(_NUMBER_WORDS[match.group(1)])
    return found


def validate_grounding(text: str, request: CommunicationRequest) -> list[ValidationIssue]:
    """Не отправлять непроверенные числа, опыт и обещания расписания."""
    if not text.strip():
        return []

    try:
        trusted = json.dumps(request.context, ensure_ascii=False, default=str)
    except (ValueError, TypeError):
        trusted = ""
    trusted += "\n" + "\n".join(request.business_rules)
    # Число из вопроса можно повторить, но нельзя выдумать новое.
    quoted = "\n".join(
        msg.content
        for msg in request.conversation
        if msg.role.lower() in {"user", "client", "human"}
    )
    known_numbers = _numeric_facts(trusted + "\n" + quoted)
    unexpected = _numeric_facts(text) - known_numbers

    issues: list[ValidationIssue] = []
    if unexpected:
        issues.append(
            ValidationIssue(
                "unsupported_number",
                "В ответе есть число, которого нет в переданных данных",
                hard=True,
            )
        )

    if _AVAILABILITY.search(_norm(text)) and not any(
        request.context.get(key) for key in _SCHEDULE_KEYS
    ):
        issues.append(
            ValidationIssue(
                "unverified_availability",
                "Обещание свободного времени без подтвержденного расписания",
                hard=True,
            )
        )

    for pattern in _HIGH_RISK_CLAIMS:
        claims = pattern.findall(_norm(text))
        # Глаголы руководства, сертификаты и гарантии должны быть в
        # доверенных фактах, а не только в тексте клиента.
        if any(not re.search(re.escape(_norm(claim)), _norm(trusted)) for claim in claims):
            issues.append(
                ValidationIssue(
                    "unsupported_claim",
                    "Неподтвержденное достижение, полномочие или гарантия",
                    hard=True,
                )
            )
            break
    return issues

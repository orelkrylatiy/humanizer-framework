# A/B эксперимент: текущий пайплайн profi-worker vs humanizer-framework.
# Одна модель (glm-5.3-flash через anthropic-прокси из .env profi-worker),
# одни заявки из info2.db, честное сравнение промпт-пайплайнов.
from __future__ import annotations

import json
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Maxim\Desktop\profi-worker\src")
sys.path.insert(0, r"C:\Users\Maxim\Desktop\humanizer-framework\src")

from profi.copy_style import outreach_variant_prompt
from profi.fastpath import normalize_reply_text
from profi.llm import client as llm
from profi.main import (
    TRIAGE_SYSTEM,
    _llm_order_payload,
    _recipient_hint,
    _style_variation,
)

from humanizer_framework import CommunicationFramework
from humanizer_framework.models import VoiceProfile
from humanizer_framework.presets import tutoring_request
from humanizer_framework.providers.base import Provider

PROFI_DB = r"C:\Users\Maxim\Desktop\profi-worker\data\info2.db"
ORDER_IDS = ["94201370", "94198879", "94183599", "94197896", "94060693"]

random.seed(42)  # воспроизводимость _style_variation ветки A

# --- Провайдер для humanizer: тот же endpoint/ключ/модель, что у ветки A ---


class ProfiGlmProvider(Provider):
    name = "glm-5.3-flash"

    def generate(self, messages, *, temperature=0.4, max_tokens=300):
        # glm-5.3 — reasoning-модель: бюджет уходит на «обдумывание», дефолтные
        # 400 фреймворка дают пустой text-блок. Даём как у прод-пайплайна (3000).
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        rest = [m for m in messages if m["role"] != "system"]
        user = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in rest)
        budget = max(3000, max_tokens)
        for attempt in range(2):  # пустой ответ = reasoning съел бюджет, ретрай
            raw = llm.chat(system, user, temperature=temperature, max_tokens=budget)
            if raw.strip():
                return raw
            budget += 1500
        return raw


# --- Данные заявок ---

con = sqlite3.connect(PROFI_DB)
con.row_factory = sqlite3.Row
orders = {}
voice_examples = []
for row in con.execute(
    "SELECT order_id, details_json, draft_text, draft_source, prompt_variant, first_reply_text "
    "FROM candidates WHERE order_id IN (%s)" % ",".join("?" * len(ORDER_IDS)),
    ORDER_IDS,
):
    orders[str(row["order_id"])] = dict(row)
for row in con.execute(
    "SELECT draft_text FROM candidates WHERE draft_source='llm' AND send_status='sent' "
    "AND draft_text IS NOT NULL AND order_id NOT IN (%s) ORDER BY draft_generated_at DESC LIMIT 12"
    % ",".join("?" * len(ORDER_IDS)),
    ORDER_IDS,
):
    t = (row["draft_text"] or "").strip()
    if len(t) > 120 and t not in voice_examples:
        voice_examples.append(t)
voice_examples = voice_examples[:6]

BUSINESS_RULES = [
    "Цену и ставку не называть: никаких «₽», «рублей», «в час», «за занятие». Длительность занятия не указывать.",
    "В тексте запрещены ссылки, телефоны, e-mail, мессенджеры — только обычный текст.",
    "Не выдумывать опыт, достижения, участие в олимпиадах, отзывы.",
    "Не пересказывать заявку и не повторять то, что клиент и так знает про себя.",
    "Обращаться к читателю сообщения (обычно родитель); ученика называть по имени.",
    "Цель — договориться на пробное занятие; формат занятий дистанционный.",
]

VOICE = VoiceProfile(
    id="profi-info",
    description="Репетитор, живой короткий чат-стиль без канцелярита",
    prefer=[
        "простые живые слова и короткие предложения разной длины",
        "одна конкретная детель из заказа по делу",
        "разговорный тон мессенджера",
    ],
    avoid=[
        "канцелярит и пафос («важно отметить», «данный подход»)",
        "«не просто X, а Y», риторические тройки, списки, эмодзи",
        "комплименты заказу и дежурные концовки («Буду рад помочь!»)",
        "ИИ-штампы: «задача понятна», «step by step», «шаг за шагом»",
        "длинное тире «—»",
    ],
    examples=voice_examples,
)


def run_current(row):
    """Ветка A: точная копия пайплайна decide_reply для outreach."""
    details = json.loads(row["details_json"])
    variant = row["prompt_variant"] or "B"
    system = TRIAGE_SYSTEM + _style_variation() + outreach_variant_prompt(variant)
    user = _llm_order_payload(details) + "\n\n" + _recipient_hint(details)
    raw = llm.chat(system, user, temperature=0.4, max_tokens=3000)
    verdict = llm.json_reply(raw)
    action = str(verdict.get("verdict") or "").strip().lower()
    text, invalid = normalize_reply_text(str(verdict.get("text") or ""))
    return {
        "variant": variant,
        "verdict": action,
        "reason": verdict.get("reason"),
        "text": text if not invalid else f"[отклонён: {invalid}] {text}",
        "chars": len(text),
    }


def run_humanizer(row):
    """Ветка B: humanizer-framework generate() на той же модели."""
    d = json.loads(row["details_json"])
    client_name = (d.get("client_block_dom") or {}).get("name") or ""
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="profi-info",
        conversation=[],
        context={
            "client_name": client_name,
            "student_name": d.get("student") or "",
            "order": {
                "subject": d.get("subject"),
                "description": d.get("description"),
                "wishes": d.get("wishes"),
                "student": d.get("student"),
                "remote": d.get("remote"),
                "address": d.get("address"),
                "competition_position": d.get("competition_position"),
            },
            "profile_facts": [
                "репетитор информатики и программирования: ЕГЭ/ОГЭ, олимпиады",
                "занятия дистанционно",
                "по основной работе — разработчик, алгоритмы и Python ежедневно",
            ],
        },
        business_rules=BUSINESS_RULES,
        voice=VOICE,
        language="ru",
    )
    fw = CommunicationFramework(provider=ProfiGlmProvider())
    result = fw.generate(request)
    return {
        "text": result.text,
        "chars": len(result.text),
        "plan": f"{result.plan.action}/{result.plan.target_length.value}"
        f"/max={result.plan.max_chars}/q={result.plan.ask_question}",
        "issues": [f"{'HARD' if i.hard else 'soft'}:{i.code}" for i in result.issues] or None,
        "rewritten": result.rewritten,
    }


def main():
    out = ["# A/B: profi-worker (текущий) vs humanizer-framework — 2026-09-22", ""]
    out.append(
        f"Модель у обеих веток: `{llm._model('anthropic')}` (anthropic-прокси из .env profi-worker)."
    )
    out.append(
        f"Voice-примеры для humanizer: {len(voice_examples)} реальных отправленных LLM-откликов воркера."
    )
    out.append("")
    for oid in ORDER_IDS:
        row = orders.get(oid)
        if not row:
            out.append(f"## {oid}: НЕ НАЙДЕН")
            continue
        details = json.loads(row["details_json"])
        out.append(f"## Заказ {oid} — {details.get('subject')}")
        brief = " | ".join(
            str(x)
            for x in [
                details.get("description"),
                details.get("student"),
                details.get("remote"),
                details.get("wishes"),
            ]
            if x
        )
        out.append(f"**Заявка:** {brief[:220]}")
        out.append("")
        out.append(f"**1. Реально отправленный отклик воркера (из БД, {row['draft_source']}):**")
        out.append(f"> {row['draft_text']}")
        out.append("")
        try:
            a = run_current(row)
            out.append(
                f"**2. [A] Текущий пайплайн, свежий прогон** (вариант {a['variant']}, verdict={a['verdict']}, {a['chars']} симв.):"
            )
            out.append(f"> {a['text']}")
        except Exception as exc:
            out.append(f"**2. [A] Текущий пайплайн — СБОЙ:** `{exc}`")
        out.append("")
        try:
            b = run_humanizer(row)
            out.append(
                f"**3. [B] humanizer-framework** ({b['chars']} симв.; план {b['plan']}; "
                f"issues {b['issues']}; rewrite={b['rewritten']}):"
            )
            out.append(f"> {b['text']}")
        except Exception as exc:
            out.append(f"**3. [B] humanizer-framework — СБОЙ:** `{exc}`")
        out.append("")
        print(f"{oid} готов", flush=True)
    Path(__file__).with_name("experiment_results_2026-09-22.md").write_text(
        "\n".join(out), encoding="utf-8"
    )
    print("OK -> experiment_results_2026-09-22.md")


if __name__ == "__main__":
    main()

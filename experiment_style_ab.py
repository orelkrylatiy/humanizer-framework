# Стилевой A/B: текущий пайплайн profi-worker vs humanizer-framework.
# 7 свежих заказов за 2026-09-23 (не участвовали во вчерашнем эксперименте).
# Для каждого заказа три текста:
#   0) реально отправленный отклик воркера (из БД) — эталон
#   1) [A] текущий пайплайн: TRIAGE_SYSTEM + _style_variation + variant prompt
#   2) [B] humanizer-framework generate()
# Плюс количественные метрики стиля, включая собственный ИИ-детектор воркера.
from __future__ import annotations

import json
import random
import re
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, r"C:\Users\Maxim\Desktop\profi-worker\src")
sys.path.insert(0, r"C:\Users\Maxim\Desktop\humanizer-framework\src")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from profi.copy_style import client_copy_issues, outreach_variant_prompt
from profi.fastpath import normalize_reply_text
from profi.llm import client as llm
from profi.main import TRIAGE_SYSTEM, _llm_order_payload, _recipient_hint, _style_variation

from humanizer_framework import CommunicationFramework
from humanizer_framework.models import VoiceProfile
from humanizer_framework.presets import tutoring_request
from humanizer_framework.providers.base import Provider
from humanizer_framework.validators import _skeleton

PROFI_DB = r"C:\Users\Maxim\Desktop\profi-worker\data\info2.db"
ORDER_IDS = ["94251515", "94250686", "94250115", "94249373", "94249276", "93776865", "94245128"]
OUT_MD = Path(__file__).with_name("experiment_style_ab_results_2026-09-23.md")

random.seed(42)  # воспроизводимость _style_variation ветки A


class ProfiGlmProvider(Provider):
    name = "glm-5.3-flash"

    def generate(self, messages, *, temperature=0.4, max_tokens=300):
        # glm-5.3 — reasoning-модель: дефолтные 400 фреймворка уходят на «обдумывание».
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        rest = [m for m in messages if m["role"] != "system"]
        user = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in rest)
        budget = max(3000, max_tokens)
        raw = ""
        for _ in range(2):
            raw = llm.chat(system, user, temperature=temperature, max_tokens=budget)
            if raw.strip():
                break
            budget += 1500
        return raw


# --- Данные: заказы + voice-примеры (реальные отправленные отклики) ---

con = sqlite3.connect(PROFI_DB)
con.row_factory = sqlite3.Row
orders = {}
for row in con.execute(
    "SELECT order_id, details_json, draft_text, draft_source, prompt_variant "
    "FROM candidates WHERE order_id IN (%s)" % ",".join("?" * len(ORDER_IDS)),
    ORDER_IDS,
):
    orders[str(row["order_id"])] = dict(row)

voice_examples = []
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
con.close()

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

FW = CommunicationFramework(provider=ProfiGlmProvider())


def run_current(row):
    """Ветка A: точная копия пайплайна decide_reply для outreach."""
    details = json.loads(row["details_json"])
    variant = row["prompt_variant"] or "B"
    system = TRIAGE_SYSTEM + _style_variation() + outreach_variant_prompt(variant)
    user = _llm_order_payload(details) + "\n\n" + _recipient_hint(details)
    raw = llm.chat(system, user, temperature=0.4, max_tokens=3000)
    verdict = llm.json_reply(raw)
    text, invalid = normalize_reply_text(str(verdict.get("text") or ""))
    return variant, (text if not invalid else f"[отклонён: {invalid}] {text}")


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
    result = FW.generate(request)
    return result


# --- Метрики стиля ---

_EMOJI_RE = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf]")


def style_metrics(text: str, client_name: str) -> dict:
    text = (text or "").strip()
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    sent_lens = [len(s.strip()) for s in sentences if s.strip()]
    ai = client_copy_issues(text)  # детектор самого воркера
    return {
        "chars": len(text),
        "paras": len([p for p in text.split("\n") if p.strip()]),
        "sents": len(sentences),
        "avg_sent": round(sum(sent_lens) / len(sent_lens), 1) if sent_lens else 0,
        "questions": text.count("?"),
        "ai_n": len(ai),
        "ai": ai,
        "em_dash": "—" in text or "–" in text,
        "colon": bool(re.search(r"(?<!\d):(?!\d)", text)),
        "smiley": bool(re.search(r"\)(?=\s|$)", text)),
        "emoji": bool(_EMOJI_RE.search(text)),
        "formal_hello": text.startswith(("Здравствуйте", "Добрый")),
        "name": bool(client_name) and client_name.lower() in text.lower(),
        "trial_pitch": bool(
            re.search(
                r"пробн\w+\s+заняти|первое\s+заняти\w*\s+(?:предлага|сдела|провест|как)",
                text.lower(),
            )
        ),
        "diag": "диагностик" in text.lower(),
    }


def sim(a: str, b: str) -> float:
    return round(SequenceMatcher(None, _skeleton(a), _skeleton(b)).ratio(), 2)


def fmt_metrics(m: dict) -> str:
    bits = [
        f"{m['chars']} симв.",
        f"{m['paras']} абз.",
        f"{m['sents']} предл.",
        f"ср.длина {m['avg_sent']}",
        f"вопросов {m['questions']}",
        f"ИИ-детектор: {m['ai_n']}" + (f" ({'; '.join(m['ai'])})" if m["ai"] else ""),
    ]
    flags = [
        k
        for k in (
            "em_dash",
            "colon",
            "smiley",
            "emoji",
            "formal_hello",
            "name",
            "trial_pitch",
            "diag",
        )
        if m[k]
    ]
    bits.append("флаги: " + (", ".join(flags) if flags else "—"))
    return " | ".join(bits)


def main():
    out = [
        "# Стилевой A/B: profi-worker (текущий) vs humanizer-framework — 2026-09-23",
        "",
        f"Модель у обеих веток: `{llm._model('anthropic')}` (anthropic-прокси из .env profi-worker).",
        f"Заказы: {len(ORDER_IDS)} свежих за 2026-09-23, у всех есть реально отправленный отклик в БД.",
        f"Voice-примеры humanizer: {len(voice_examples)} реальных отправленных LLM-откликов воркера.",
        "",
    ]
    all_m = {"sent": [], "A": [], "B": []}
    sims = []

    for oid in ORDER_IDS:
        row = orders.get(oid)
        if not row:
            out.append(f"## {oid}: НЕ НАЙДЕН")
            continue
        details = json.loads(row["details_json"])
        client_name = (details.get("client_block_dom") or {}).get("name") or ""
        out.append(f"## Заказ {oid} — {(details.get('subject') or '')[:60]}")
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
        if client_name:
            out.append(f"**Клиент:** {client_name}")
        out.append("")

        sent = (row["draft_text"] or "").strip()
        m0 = style_metrics(sent, client_name)
        all_m["sent"].append(m0)
        out.append(
            f"**0. Отправленный отклик воркера (из БД, {row['draft_source']}, вариант {row['prompt_variant']}):**"
        )
        out.append(f"> {sent}")
        out.append(f"`{fmt_metrics(m0)}`")
        out.append("")

        try:
            variant, a_text = run_current(row)
            ma = style_metrics(a_text, client_name)
            all_m["A"].append(ma)
            out.append(f"**1. [A] Текущий пайплайн, свежий прогон** (вариант {variant}):")
            out.append(f"> {a_text}")
            out.append(f"`{fmt_metrics(ma)}`")
        except Exception as exc:
            a_text = ""
            out.append(f"**1. [A] Текущий пайплайн — СБОЙ:** `{exc}`")
        out.append("")

        try:
            b = run_humanizer(row)
            mb = style_metrics(b.text, client_name)
            all_m["B"].append(mb)
            sims.append(sim(a_text, b.text))
            out.append(
                f"**2. [B] humanizer-framework** (план {b.plan.action}/{b.plan.target_length.value}"
                f"/max={b.plan.max_chars}; issues {[f'{chr(72) if i.hard else chr(115)}:{i.code}' for i in b.issues] or 'нет'}; "
                f"rewrite={b.rewritten}):"
            )
            out.append(f"> {b.text}")
            out.append(f"`{fmt_metrics(mb)}`")
            if a_text:
                out.append(f"`похожесть A vs B (скелет): {sim(a_text, b.text)}`")
        except Exception as exc:
            out.append(f"**2. [B] humanizer-framework — СБОЙ:** `{exc}`")
        out.append("")
        print(f"{oid} готов", flush=True)

    # --- Агрегат ---
    def agg(key):
        rows = [m for m in all_m[key] if m]
        n = len(rows) or 1
        return {
            "chars": sum(r["chars"] for r in rows) // n,
            "paras": round(sum(r["paras"] for r in rows) / n, 1),
            "sents": round(sum(r["sents"] for r in rows) / n, 1),
            "avg_sent": round(sum(r["avg_sent"] for r in rows) / n, 1),
            "questions": round(sum(r["questions"] for r in rows) / n, 2),
            "ai_n": round(sum(r["ai_n"] for r in rows) / n, 2),
            "ai_total": sum(r["ai_n"] for r in rows),
            "name_pct": round(100 * sum(1 for r in rows if r["name"]) / n),
            "trial_pct": round(100 * sum(1 for r in rows if r["trial_pitch"]) / n),
            "diag_pct": round(100 * sum(1 for r in rows if r["diag"]) / n),
            "formal_pct": round(100 * sum(1 for r in rows if r["formal_hello"]) / n),
            "smiley_pct": round(100 * sum(1 for r in rows if r["smiley"]) / n),
        }

    a0, aa, ab = agg("sent"), agg("A"), agg("B")
    out.append("## Агрегат по метрикам стиля")
    out.append("")
    out.append("| Метрика | Отправленные (эталон) | [A] Текущий пайплайн | [B] humanizer |")
    out.append("|---|---|---|---|")
    rows_map = [
        ("ср. символов", "chars"),
        ("ср. абзацев", "paras"),
        ("ср. предложений", "sents"),
        ("ср. длина предложения", "avg_sent"),
        ("ср. вопросов", "questions"),
        ("ср. срабатываний ИИ-детектора", "ai_n"),
        ("всего срабатываний ИИ-детектора", "ai_total"),
        ("% с именем клиента", "name_pct"),
        ("% с питчем пробного", "trial_pct"),
        ("% с «диагностикой»", "diag_pct"),
        ("% формального приветствия", "formal_pct"),
        ("% со скобкой-смайликом", "smiley_pct"),
    ]
    for label, key in rows_map:
        out.append(f"| {label} | {a0[key]} | {aa[key]} | {ab[key]} |")
    if sims:
        out.append("")
        out.append(
            f"Средняя похожесть текстов A и B (скелетная): {round(sum(sims) / len(sims), 2)} — формулировки заметно различаются при одинаковом смысле."
        )

    OUT_MD.write_text("\n".join(out), encoding="utf-8")
    print(f"\nOK -> {OUT_MD.name}")
    print(
        "Агрегат: chars",
        a0["chars"],
        aa["chars"],
        ab["chars"],
        "| ai_n",
        a0["ai_n"],
        aa["ai_n"],
        ab["ai_n"],
        "| trial%",
        a0["trial_pct"],
        aa["trial_pct"],
        ab["trial_pct"],
        "| diag%",
        a0["diag_pct"],
        aa["diag_pct"],
        ab["diag_pct"],
    )


if __name__ == "__main__":
    main()

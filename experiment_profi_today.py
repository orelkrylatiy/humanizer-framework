# Свежий прогон humanizer-framework на РЕАЛЬНЫХ заказах дня (24.09).
# «До» — реально отправленный воркером отклик (draft_text из БД profi-worker).
# «После» — humanizer-framework generate() на той же модели (glm-5.3-flash,
# anthropic-прокси из .env profi-worker). Отклики не отправляются — это тест.
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\Maxim\Desktop\profi-worker\src")
sys.path.insert(0, r"C:\Users\Maxim\Desktop\humanizer-framework\src")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from profi.llm import client as llm

from humanizer_framework import CommunicationFramework
from humanizer_framework.models import VoiceProfile
from humanizer_framework.presets import tutoring_request
from humanizer_framework.providers.base import Provider

REPO = Path(r"C:\Users\Maxim\Desktop\profi-worker")
TODAY0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
PER_ACCOUNT = 2  # заказов на аккаунт

PROFILE_FACTS = {
    "lang": [
        "репетитор английского языка: ЕГЭ, разговорная практика, английский для работы",
        "занятия дистанционно",
    ],
    "info": [
        "репетитор информатики и программирования: ЕГЭ/ОГЭ, олимпиады",
        "занятия дистанционно",
        "по основной работе — разработчик, алгоритмы и Python ежедневно",
    ],
}

BUSINESS_RULES = [
    "Цену и ставку не называть: никаких «₽», «рублей», «в час», «за занятие». Длительность занятия не указывать.",
    "В тексте запрещены ссылки, телефоны, e-mail, мессенджеры — только обычный текст.",
    "Не выдумывать опыт, достижения, участие в олимпиадах, отзывы.",
    "Не пересказывать заявку и не повторять то, что клиент и так знает про себя.",
    "Обращаться к читателю сообщения (обычно родитель); ученика называть по имени.",
    "Цель — договориться на пробное занятие; формат занятий дистанционный.",
]

VOICE = VoiceProfile(
    id="profi-live",
    description="Репетитор, живой короткий чат-стиль без канцелярита",
    prefer=[
        "простые живые слова и короткие предложения разной длины",
        "одна конкретная деталь из заказа по делу",
        "разговорный тон мессенджера",
    ],
    avoid=[
        "канцелярит и пафос («важно отметить», «данный подход»)",
        "«не просто X, а Y», риторические тройки, списки, эмодзи",
        "комплименты заказу и дежурные концовки («Буду рад помочь!»)",
        "ИИ-штампы: «задача понятна», «step by step», «шаг за шагом»",
        "длинное тире «—»",
    ],
)


class ProfiGlmProvider(Provider):
    name = "glm-5.3-flash"

    def generate(self, messages, *, temperature=0.4, max_tokens=300):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        rest = [m for m in messages if m["role"] != "system"]
        user = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in rest)
        budget = max(3000, max_tokens)
        for _ in range(2):
            raw = llm.chat(system, user, temperature=temperature, max_tokens=budget)
            if raw.strip():
                return raw
            budget += 1500
        return raw


def load_sent_today(db: Path) -> list[dict]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT order_id, details_json, draft_text FROM candidates "
        "WHERE send_status='sent' AND draft_source='llm' AND draft_text IS NOT NULL "
        "AND sent_at >= ? ORDER BY sent_at DESC LIMIT ?",
        (TODAY0, PER_ACCOUNT),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def run_humanizer(row: dict, facts_key: str) -> dict:
    d = json.loads(row["details_json"])
    client_name = (d.get("client_block_dom") or {}).get("name") or ""
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="profi-info",
        conversation=[],
        context={
            "client_name": client_name,
            "order": {
                "subject": d.get("subject"),
                "description": d.get("description"),
                "wishes": d.get("wishes"),
                "student": d.get("student"),
                "remote": d.get("remote"),
                "competition_position": d.get("competition_position"),
            },
            "profile_facts": PROFILE_FACTS[facts_key],
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
        "plan": f"{result.plan.action}/{result.plan.target_length.value}/max={result.plan.max_chars}/q={result.plan.ask_question}",
        "issues": [f"{'HARD' if i.hard else 'soft'}:{i.code}" for i in result.issues] or None,
        "rewritten": result.rewritten,
    }


def main() -> None:
    out = ["# Humanizer на реальных заказах дня — 24.09", ""]
    out.append(
        "Модель обеих веток: glm-5.3-flash (anthropic-прокси profi-worker). «До» — реально отправленный отклик из БД; «после» — humanizer-framework, отклик НЕ отправлялся."
    )
    total = ok = 0
    for acc, key in (("lang", "lang"), ("info2", "info"), ("info3", "info")):
        db = REPO / "data" / f"{acc}.db"
        rows = load_sent_today(db)
        out += ["", f"## {acc} — {len(rows)} заказ(ов)", ""]
        for row in rows:
            total += 1
            d = json.loads(row["details_json"])
            subj = d.get("subject") or "?"
            student = d.get("student") or ""
            out += [
                f"### #{row['order_id']} — {subj}" + (f" | {student}" if student else ""),
                f"**Заявка:** {d.get('goal') or '—'} | {d.get('description') or ''} | «{d.get('wishes') or '—'}»",
                "",
                "**ДО (отправлено воркером):**",
                f"> {(row['draft_text'] or '').strip()}",
                "",
            ]
            try:
                b = run_humanizer(row, key)
                ok += 1
                out += [
                    "**ПОСЛЕ (humanizer, не отправлено):**",
                    f"> {b['text']}",
                    "",
                    f"`{b['chars']} симв. | план {b['plan']} | issues {b['issues']} | rewrite={b['rewritten']}`",
                ]
            except Exception as exc:
                out += [f"**ПОСЛЕ — СБОЙ:** `{exc}`"]
            out.append("")
        out.append("")
    out.insert(1, f"Итог: человайзер собрался на {ok}/{total} заказов.")
    report = Path(__file__).with_name("experiment_profi_today_results.md")
    report.write_text("\n".join(out), encoding="utf-8")
    print(f"готово: {report} ({ok}/{total})")


if __name__ == "__main__":
    main()

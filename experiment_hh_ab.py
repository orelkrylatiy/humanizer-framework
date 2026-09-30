# A/B для hh-ops: текущий пайплайн сопроводительных писем vs humanizer-framework.
# Ветка [A] — точная реплика apply-пайплайна hh-ops:
#   system = prompts/cover_letter_frontend.txt (с ${HH_NAME}/${HH_TELEGRAM}),
#   user   = дефолтный --message-prompt + инструкция из _build_cover_letter + контекст,
#   temperature=0.0 (дефолт ChatOpenAI в hh-ops).
# Ветка [B] — humanizer_framework.generate(), домен job_search, тип application.
# Транспорт у веток одинаковый: profi.llm.client.chat на glm-5.3-flash.
# Резюме — реальное (career-ops/output/cv-base/cv-maxim-agafonov-react-ru.json),
# контекст собирается в формате _build_cover_letter_context/_analyze_resume_heavy hh-ops.
# Метрики: клише, конструкции «X, что Y-эффект», тире, самопохожесть писем ветки.
from __future__ import annotations

import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, r"C:\Users\Maxim\Desktop\profi-worker\src")
sys.path.insert(0, r"C:\Users\Maxim\Desktop\humanizer-framework\src")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ.setdefault("HH_NAME", "Максим")
os.environ.setdefault("HH_TELEGRAM", "@maxxwway")

from humanizer_framework import CommunicationFramework
from humanizer_framework.models import VoiceProfile
from humanizer_framework.presets import job_search_request
from humanizer_framework.providers.base import Provider
from humanizer_framework.validators import _skeleton
from profi.llm import client as llm

FW_DIR = Path(r"C:\Users\Maxim\Desktop\humanizer-framework")
HH_DIR = Path(r"C:\Users\Maxim\Desktop\hh-ops")
RESUME_JSON = Path(
    r"C:\Users\Maxim\Desktop\career-ops\output\cv-base\archive\agafonov-persona-20260925\cv-maxim-agafonov-react-ru.json"
)
OUT_MD = FW_DIR / "experiment_hh_ab_results_2026-09-28.md"

MESSAGE_PROMPT = (
    "Сгенерируй сопроводительное письмо не более 5-7 предложений от моего имени для вакансии"
)
BUILD_INSTRUCTION = (
    "Напиши уникальное сопроводительное письмо под эту конкретную вакансию. "
    "Не ограничивайся повторением названия вакансии. Используй только факты из контекста, "
    "не выдумывай опыт и не используй placeholder'ы."
)
RESUME_TITLE = "Frontend-разработчик (ReactJS, TypeScript, Redux)"


class HhGlmProvider(Provider):
    name = "glm-5.3-flash"

    @staticmethod
    def _looks_truncated(text: str) -> bool:
        # Обрыв на кириллической строчной («…разработчика») или на цифре
        # («…упала на 35») — явная середина слова/числа. Латинская строчная
        # допустима: письмо может кончаться на "@maxxwway".
        if not text:
            return False
        last = text[-1]
        return last.isdigit() or (last.islower() and re.match(r"[а-яё]", last, re.IGNORECASE))

    def generate(self, messages, *, temperature=0.4, max_tokens=300):
        # glm-5.3 — reasoning-модель: дефолтные 400 токенов уходят на размышления.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        rest = [m for m in messages if m["role"] != "system"]
        user = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in rest)
        budget = max(3000, max_tokens)
        raw = ""
        for _ in range(4):
            try:
                raw = llm.chat(system, user, temperature=temperature, max_tokens=budget).strip()
            except Exception:
                raw = ""
            if len(raw) >= 300 and not self._looks_truncated(raw):
                return raw
            budget += 2000
        return raw


FW = CommunicationFramework(provider=HhGlmProvider())

# Кэш успешных генераций: повторный запуск не перегенерирует удачные письма.
CACHE = FW_DIR / "experiment_hh_ab_cache.json"
_CACHE: dict = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def _cache_get(key: str):
    return _CACHE.get(key)


def _cache_set(key: str, value) -> None:
    _CACHE[key] = value
    CACHE.write_text(json.dumps(_CACHE, ensure_ascii=False, indent=1), encoding="utf-8")


# --- Реальное резюме, отрендеренное как _analyze_resume_heavy в hh-ops ---

RESUME = json.loads(RESUME_JSON.read_text(encoding="utf-8"))
_exp = RESUME["experience"][0]


def render_resume_heavy() -> str:
    parts = [f"Должность: {RESUME_TITLE}"]
    parts.append("\n---------- О СЕБЕ ----------")
    parts.append(RESUME["summary"])
    parts.append("\n---------- НАВЫКИ ----------")
    parts.append(", ".join(RESUME["competencies"]))
    parts.append("\n---------- ОПЫТ РАБОТЫ ----------")
    parts.append(f"\n- {_exp['company']}")
    parts.append(f" Должность: {_exp['role']}")
    parts.append(f" Период: {_exp['dates']}")
    parts.append(" Описание:")
    parts.append(" " + "\n ".join(_exp["bullets"]))
    return "\n".join(parts)


RESUME_HEAVY = render_resume_heavy()


# --- Вакансии: сильное совпадение, среднее, слабое (как в реальных прогонах) ---

VACANCIES = [
    {
        "id": "vue-terminal",
        "name": "Frontend-разработчик (Vue 3)",
        "employer": {"name": "Финтех-платформа (торговый терминал)"},
        "area": {"name": "Москва"},
        "employment": {"name": "Полная занятость"},
        "schedule": {"name": "Удалённая работа"},
        "experience": {"name": "От 3 до 6 лет"},
        "salary": {"from": 300000, "to": 420000, "currency": "RUR"},
        "description": (
            "Мы развиваем торговый веб-терминал для частных инвесторов. Ищем фронтендера "
            "в команду интерактивных виджетов: графики, стакан, виджеты портфеля. "
            "Задачи: поддержка и развитие интерактивных виджетов, новые фичи, постепенная "
            "миграция legacy-модулей на Vue 3, оптимизация производительности. "
            "Стек: Vue 3, TypeScript, Pinia, WebSocket, Vite. Будет плюсом опыт с "
            "потоковыми данными и highload-интерфейсами."
        ),
        "key_skills": [{"name": n} for n in ["Vue 3", "TypeScript", "Pinia", "WebSocket", "Vite"]],
    },
    {
        "id": "teaboom",
        "name": "Верстальщик (HTML/CSS)",
        "employer": {"name": "Teaboom"},
        "area": {"name": "Москва"},
        "employment": {"name": "Частичная занятость"},
        "schedule": {"name": "Удалённая работа"},
        "experience": {"name": "От 1 года до 3 лет"},
        "salary": {"from": None, "to": None, "currency": None},
        "description": (
            "Интернет-магазин чая Teaboom.ru ищет верстальщика на проектную работу. "
            "Задачи: верстка страниц и блоков по макетам из Figma, развитие внешнего вида "
            "сайта, приведение интерфейса к единому стилю, аккуратные правки в существующем "
            "коде. Требования: HTML5, CSS3, базовый JavaScript, адаптивная верстка, Git. "
            "Опыт с интернет-магазинами приветствуется."
        ),
        "key_skills": [
            {"name": n} for n in ["HTML", "CSS", "JavaScript", "Figma", "Адаптивная верстка"]
        ],
    },
    {
        "id": "react-fintech",
        "name": "React-разработчик (Senior)",
        "employer": {"name": "Инвестиционная платформа"},
        "area": {"name": "Москва"},
        "employment": {"name": "Полная занятость"},
        "schedule": {"name": "Удалённая работа"},
        "experience": {"name": "От 3 до 6 лет"},
        "salary": {"from": 350000, "to": 500000, "currency": "RUR"},
        "description": (
            "Разрабатываем веб-терминал для инвесторов: котировки в реальном времени, "
            "портфель, аналитика. Задачи: слой потоковых данных (WebSocket), оптимизация "
            "подписок и производительности, сложное клиентское состояние, разработка "
            "дизайн-системы. Стек: React, TypeScript, Redux Toolkit, RTK Query, RxJS, "
            "WebSocket, Node.js. Ждём опыт highload real-time интерфейсов."
        ),
        "key_skills": [
            {"name": n} for n in ["React", "TypeScript", "Redux Toolkit", "RxJS", "WebSocket"]
        ],
    },
    {
        "id": "react-ecom",
        "name": "Frontend-разработчик (React)",
        "employer": {"name": "E-commerce платформа"},
        "area": {"name": "Санкт-Петербург"},
        "employment": {"name": "Полная занятость"},
        "schedule": {"name": "Сменный график"},
        "experience": {"name": "От 3 до 6 лет"},
        "salary": {"from": 250000, "to": 320000, "currency": "RUR"},
        "description": (
            "Развиваем кабинет продавца маркетплейса: таблицы заказов, аналитика, "
            "интеграции. Задачи: новые модули кабинета, рефакторинг легаси, работа с "
            "REST API. Стек: React, TypeScript, Redux, Webpack, REST."
        ),
        "key_skills": [{"name": n} for n in ["React", "TypeScript", "Redux", "REST", "Webpack"]],
    },
    {
        "id": "js-widgets",
        "name": "JavaScript-разработчик (веб-виджеты)",
        "employer": {"name": "SaaS-сервис отзывов"},
        "area": {"name": "Москва"},
        "employment": {"name": "Полная занятость"},
        "schedule": {"name": "Удалённая работа"},
        "experience": {"name": "От 1 года до 3 лет"},
        "salary": {"from": None, "to": 250000, "currency": "RUR"},
        "description": (
            "Делаем встраиваемые виджеты для сайтов клиентов: отзывы, чат, формы. "
            "Задачи: развитие SDK-виджета, независимая доставка кода, работа с "
            "чужими страницами, производительность загрузки. Стек: JavaScript, "
            "Web Components, CSS, сборка (Vite)."
        ),
        "key_skills": [{"name": n} for n in ["JavaScript", "Web Components", "CSS", "Vite"]],
    },
    {
        "id": "angular-crm",
        "name": "Frontend-разработчик (Angular)",
        "employer": {"name": "Разработчик CRM"},
        "area": {"name": "Москва"},
        "employment": {"name": "Полная занятость"},
        "schedule": {"name": "Полный день"},
        "experience": {"name": "От 3 до 6 лет"},
        "salary": {"from": 280000, "to": 360000, "currency": "RUR"},
        "description": (
            "Корпоративная CRM на Angular. Задачи: развитие модулей системы, работа с "
            "сложными формами и таблицами, интеграции по REST. Стек: Angular, TypeScript, "
            "RxJS, NgRx."
        ),
        "key_skills": [{"name": n} for n in ["Angular", "TypeScript", "RxJS", "NgRx"]],
    },
]


# --- Контекст вакансии ровно как _build_cover_letter_context в hh-ops ---


def build_context_a(vac: dict) -> str:
    parts: list[str] = []
    parts.append(f"Вакансия: {vac['name']}")
    parts.append(f"Компания: {vac['employer']['name']}")
    parts.append(f"Локация: {vac['area']['name']}")
    parts.append(f"Формат занятости: {vac['employment']['name']}")
    parts.append(f"График: {vac['schedule']['name']}")
    parts.append(f"Опыт: {vac['experience']['name']}")
    salary = vac["salary"]
    if salary.get("from") or salary.get("to"):
        parts.append(
            "Зарплата: "
            f"от {salary.get('from') or ''} "
            f"до {salary.get('to') or ''} "
            f"{salary.get('currency') or ''}".strip()
        )
    parts.append(f"Описание вакансии:\n{vac['description'][:4000]}")
    parts.append(
        "Ключевые навыки вакансии: "
        + ", ".join(s["name"] for s in vac["key_skills"] if s.get("name"))
    )
    parts.append(f"Название моего резюме: {RESUME_TITLE}")
    parts.append(f"Контекст моего резюме:\n{RESUME_HEAVY[:4000]}")
    return "\n\n".join(parts)


def load_prompt(path: Path) -> str:
    # Реплика hh_applicant_tool.utils.misc.load_prompt для существующего файла:
    # прочитать и развернуть ${VAR} через os.path.expandvars.
    return os.path.expandvars(path.read_text(encoding="utf-8"))


def chat_letter(system: str, user: str) -> str:
    """llm.chat с ретраем на пустой/обрезанный ответ (glm reasoning съедает бюджет).

    В самом hh-ops такого ретрая нет: пустой ответ там тихо падает в статический
    fallback-шаблон. Здесь ретрай нужен, чтобы сравнивать качество текстов,
    а не стабильность транспорта.
    """
    raw = ""
    budget = 3000
    for _ in range(4):
        try:
            raw = llm.chat(system, user, temperature=0.0, max_tokens=budget).strip()
        except Exception:
            raw = ""
        if len(raw) >= 300 and not HhGlmProvider._looks_truncated(raw):
            return raw
        budget += 2000
    return raw


def run_current(vac: dict) -> str:
    """Ветка A: точная реплика генерации письма hh-ops (temperature=0.0)."""
    key = f"A:{vac['id']}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    system = load_prompt(HH_DIR / "prompts" / "cover_letter_frontend.txt")
    user = MESSAGE_PROMPT + "\n\n" + BUILD_INSTRUCTION + "\n\n" + build_context_a(vac)
    text = chat_letter(system, user)
    if len(text) >= 300:
        _cache_set(key, text)
    return text


# --- Ветка B: humanizer-framework ---

BUSINESS_RULES = [
    "Используй только факты кандидата из context. Не выдумывай опыт, проекты, цифры, технологии.",
    "Это сопроводительное письмо на hh.ru в ответ на вакансию. Пиши от первого лица, сразу по делу, без приветствия и без формальной подписи.",
    "Не указывай желаемую зарплату.",
    "Контакт Telegram @maxxwway можно один раз добавить в самом конце; если он не к месту, не добавляй.",
]

VOICE = VoiceProfile(
    id="maxim-frontend",
    description="Фронтенд-инженер, живой деловой тон, короткие фразы разной длины",
    prefer=[
        "простые слова и предложения разной длины",
        "одна-две конкретные детали опыта, релевантные именно этой вакансии",
        "спокойный деловой тон без продаж",
    ],
    avoid=[
        "клише «Готов обсудить», «отлично подходит», «подходит для ваших задач», «Уверенно работаю», «Буду рад»",
        "канцелярит: «данный», «осуществляю», «обладаю навыками»",
        "конструкции «X, что повышало/снижало/ускоряло Y»",
        "риторические тройки и искусственные списки из трёх пунктов",
        "длинное тире «—», эмодзи, пафосные итоговые выводы",
    ],
    examples=[],
)


def build_context_b(vac: dict) -> dict:
    return {
        "vacancy": {
            "name": vac["name"],
            "company": vac["employer"]["name"],
            "location": vac["area"]["name"],
            "employment": vac["employment"]["name"],
            "schedule": vac["schedule"]["name"],
            "experience_required": vac["experience"]["name"],
            "description": vac["description"][:1200],
            "key_skills": [s["name"] for s in vac["key_skills"]],
        },
        "resume": {
            "title": RESUME_TITLE,
            "summary": RESUME["summary"],
            "stack": RESUME["competencies"],
            "experience": [
                {
                    "company": _exp["company"],
                    "role": _exp["role"],
                    "dates": _exp["dates"],
                    "facts": _exp["bullets"],
                }
            ],
            "education": [f"{e['title']}, {e['org']}, {e['year']}" for e in RESUME["education"]],
        },
    }


def run_humanizer(vac: dict) -> dict:
    key = f"B:{vac['id']}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    request = job_search_request(
        channel="hh",
        message_type="application",
        profile="frontend-react",
        conversation=[],
        context=build_context_b(vac),
        business_rules=BUSINESS_RULES,
        voice=VOICE,
        language="ru",
    )
    res = FW.generate(request)
    out = {
        "text": res.text,
        "issues": [f"{'H' if i.hard else 's'}:{i.code}" for i in res.issues],
        "rewritten": res.rewritten,
        "plan": f"{res.plan.action}/{res.plan.target_length.value}/max={res.plan.max_chars}",
    }
    _cache_set(key, out)
    return out


# --- Реальные отправленные письма (эталон текущего качества, из переписки) ---

REAL_SENT = [
    "Опыт в реальном времени и сложной архитектуре frontend отлично подходит для ваших задач по поддержке и развитию интерактивных виджетов и новых фич. В торговом терминале я отвечал за потоковые данные, оптимизировал подписки и снижал нагрузку на WebSocket, что резало время отклика и повышало стабильность. Также занимался рефакторингом и улучшением интеграций через Web Components с независимой доставкой, что уменьшило даунтайм и ускорило загрузки. Готов обсудить, как мой опыт в React и TypeScript поможет в миграции и поддержке ваших Vue-проектов.",
    "У меня есть опыт работы с HTML5, CSS3 и базовым JavaScript, а также уверен в адаптивной верстке и работе с Git, что подходит для задач по развитию внешнего вида сайта Teaboom.ru. В текущем проекте я часто разбираюсь в существующем коде и оптимизирую интерфейсные решения, что помогает аккуратно встраивать новые элементы без поломок. Готов обсудить, как могу помочь с версткой страниц и блоков по макетам из Figma и привести интерфейс к единому стилю. Telegram @maxxwway.",
]


# --- Метрики ---

_CLICHES = [
    "готов обсудить",
    "буду рад",
    "с уважением",
    "отлично подходит",
    "подходит для ваших задач",
    "подходит для задач",
    "уверенно работаю",
    "заинтересовала вакансия",
    "прошу рассмотреть",
    "с нетерпением",
    "коммуникабельн",
    "стрессоустойчив",
    "имею опыт",
    "есть опыт работы",
    "готов рассмотреть",
    "могу быть полезен",
    "не просто ",
    "дело не только",
    "важно отметить",
    "данным подход",
]
_EFFECT_RE = re.compile(
    r"что\s+(?:резал\w*|снижал\w*|повышал\w*|уменьшал\w*|ускорял\w*|улучшал\w*"
    r"|снижает|повышает|уменьшает|ускоряет|улучшает|позволит|помогает)"
)
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf]")


def style_metrics(text: str) -> dict:
    text = (text or "").strip()
    lower = text.lower()
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    sent_lens = [len(s.strip()) for s in sentences if s.strip()]
    cliche = [c for c in _CLICHES if c in lower]
    return {
        "chars": len(text),
        "sents": len(sentences),
        "avg_sent": round(sum(sent_lens) / len(sent_lens), 1) if sent_lens else 0,
        "cliche_n": len(cliche),
        "cliche": cliche,
        "effect_n": len(_EFFECT_RE.findall(lower)),
        "em_dash": "—" in text or "–" in text,
        "tg": "@maxxwway" in lower,
        "emoji": bool(_EMOJI_RE.search(text)),
        "first3": " ".join(text.split()[:3]),
    }


def fmt_metrics(m: dict) -> str:
    bits = [
        f"{m['chars']} симв.",
        f"{m['sents']} предл.",
        f"ср.длина {m['avg_sent']}",
        f"клише: {m['cliche_n']}" + (f" ({'; '.join(m['cliche'])})" if m["cliche"] else ""),
        f"«что-эффект»: {m['effect_n']}",
    ]
    flags = [k for k in ("em_dash", "tg", "emoji") if m[k]]
    bits.append("флаги: " + (", ".join(flags) if flags else "—"))
    return " | ".join(bits)


def sim(a: str, b: str) -> float:
    return round(SequenceMatcher(None, _skeleton(a), _skeleton(b)).ratio(), 2)


def templatedness(texts: list[str]) -> dict:
    """Средняя попарная похожесть писем внутри ветки: насколько они близки к шаблону."""
    pairs = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            pairs.append(sim(texts[i], texts[j]))
    starts = {t["first3"].lower() for t in (style_metrics(x) for x in texts)}
    return {
        "pairs": len(pairs),
        "avg_pair_sim": round(sum(pairs) / len(pairs), 2) if pairs else 0,
        "distinct_starts": len(starts),
    }


def main():
    out = [
        "# A/B: hh-ops (текущий пайплайн) vs humanizer-framework — 2026-09-28",
        "",
        f"Модель у обеих веток: `{llm._model('anthropic')}` (z.ai-прокси из .env profi-worker).",
        "Ветка [A] — реплика пайплайна hh-ops: system `prompts/cover_letter_frontend.txt` + дефолтный `--message-prompt`, temperature=0.0.",
        "Ветка [B] — humanizer `generate()`, домен job_search / канал hh / тип application (max 700 знаков, без CTA), голос и правила из конфига эксперимента.",
        f"Резюме: реальное ({RESUME_JSON.name}), рендер `_analyze_resume_heavy` для A и структурированный JSON для B.",
        f"Вакансий: {len(VACANCIES)} (сильное/среднее/слабое совпадение). Плюс 2 реально отправленных письма как эталон текущего качества.",
        "",
    ]

    letters = {"A": [], "B": []}
    b_issues_total: list[str] = []

    for vac in VACANCIES:
        out.append(f"## {vac['id']} — {vac['name']} ({vac['employer']['name']})")
        out.append("")
        try:
            a_text = run_current(vac)
            ma = style_metrics(a_text)
            letters["A"].append(a_text)
            out.append("**[A] hh-ops:**")
            out.append(f"> {a_text}")
            out.append(f"`{fmt_metrics(ma)}`")
        except Exception as exc:
            out.append(f"**[A] hh-ops — СБОЙ:** `{exc}`")
        out.append("")
        try:
            b = run_humanizer(vac)
            mb = style_metrics(b["text"])
            letters["B"].append(b["text"])
            b_issues_total.extend(b["issues"])
            out.append(
                f"**[B] humanizer** (план {b['plan']}; issues {b['issues'] or 'нет'}; rewrite={b['rewritten']}):"
            )
            out.append(f"> {b['text']}")
            out.append(f"`{fmt_metrics(mb)}`")
        except Exception as exc:
            out.append(f"**[B] humanizer — СБОЙ:** `{exc}`")
        out.append("")
        print(f"{vac['id']} готов", flush=True)

    # Детерминизм ветки A: два свежих прогона первой вакансии при temperature=0.
    try:
        system = load_prompt(HH_DIR / "prompts" / "cover_letter_frontend.txt")
        user0 = MESSAGE_PROMPT + "\n\n" + BUILD_INSTRUCTION + "\n\n" + build_context_a(VACANCIES[0])
        rep1 = chat_letter(system, user0)
        rep2 = chat_letter(system, user0)
        out.append("## Детерминизм ветки A (temperature=0.0, два свежих прогона vacancy 1)")
        out.append("")
        if len(rep1) >= 300 and len(rep2) >= 300:
            out.append(f"> {rep1}")
            out.append("")
            out.append(f"> {rep2}")
            out.append("")
            out.append(
                f"`похожесть двух прогонов (скелет): {sim(rep1, rep2)}; длины: {len(rep1)}/{len(rep2)}`"
            )
        else:
            out.append(
                f"Прокси вернул пустой/обрезанный ответ (длины {len(rep1)}/{len(rep2)}) — "
                "прогон детерминизма не показателен, транспорт нестабилен."
            )
        out.append("")
    except Exception as exc:
        out.append(f"Детерминизм-прогон упал: `{exc}`")
        out.append("")

    out.append("## Реально отправленные письма (эталон текущего качества)")
    out.append("")
    for i, letter in enumerate(REAL_SENT, 1):
        m = style_metrics(letter)
        out.append(f"**Письмо {i}:**")
        out.append(f"> {letter}")
        out.append(f"`{fmt_metrics(m)}`")
        out.append("")
    out.append(
        f"`похожесть двух реальных писем между собой (скелет): {sim(REAL_SENT[0], REAL_SENT[1])}`"
    )
    out.append("")

    # Агрегат
    def agg(texts: list[str]) -> dict:
        rows = [style_metrics(t) for t in texts]
        n = len(rows) or 1
        return {
            "chars": sum(r["chars"] for r in rows) // n,
            "sents": round(sum(r["sents"] for r in rows) / n, 1),
            "avg_sent": round(sum(r["avg_sent"] for r in rows) / n, 1),
            "cliche_n": round(sum(r["cliche_n"] for r in rows) / n, 2),
            "cliche_total": sum(r["cliche_n"] for r in rows),
            "effect_n": round(sum(r["effect_n"] for r in rows) / n, 2),
            "em_dash_pct": round(100 * sum(1 for r in rows if r["em_dash"]) / n),
            "tg_pct": round(100 * sum(1 for r in rows if r["tg"]) / n),
            "ready_discuss_pct": round(
                100 * sum(1 for r in rows if "готов обсудить" in r["cliche"]) / n
            ),
        }

    a0, aa, ab = agg(REAL_SENT), agg(letters["A"]), agg(letters["B"])
    t_a, t_b = templatedness(letters["A"]), templatedness(letters["B"])

    out.append("## Агрегат")
    out.append("")
    out.append("| Метрика | Реальные письма (n=2) | [A] hh-ops (n=6) | [B] humanizer (n=6) |")
    out.append("|---|---|---|---|")
    rows_map = [
        ("ср. символов", "chars"),
        ("ср. предложений", "sents"),
        ("ср. длина предложения", "avg_sent"),
        ("ср. клише на письмо", "cliche_n"),
        ("всего клише", "cliche_total"),
        ("ср. «что-эффект» на письмо", "effect_n"),
        ("% с «Готов обсудить»", "ready_discuss_pct"),
        ("% с длинным тире", "em_dash_pct"),
        ("% с Telegram", "tg_pct"),
    ]
    for label, key in rows_map:
        out.append(f"| {label} | {a0[key]} | {aa[key]} | {ab[key]} |")
    out.append("")
    out.append("| Шаблонность ветки | [A] hh-ops | [B] humanizer |")
    out.append("|---|---|---|")
    out.append(
        f"| средняя попарная похожесть писем (скелет) | {t_a['avg_pair_sim']} | {t_b['avg_pair_sim']} |"
    )
    out.append(
        f"| различных начал (из {len(letters['A'])}) | {t_a['distinct_starts']} | {t_b['distinct_starts']} |"
    )
    if b_issues_total:
        out.append("")
        out.append(
            f"Валидатор humanizer суммарно: {len(b_issues_total)} замечаний ({', '.join(b_issues_total)})."
        )

    OUT_MD.write_text("\n".join(out), encoding="utf-8")
    print(f"\nOK -> {OUT_MD.name}")
    print(
        "Агрегат: клише",
        a0["cliche_total"],
        aa["cliche_total"],
        ab["cliche_total"],
        "| эфф.",
        a0["effect_n"],
        aa["effect_n"],
        ab["effect_n"],
        "| самопохожесть",
        t_a["avg_pair_sim"],
        t_b["avg_pair_sim"],
    )


if __name__ == "__main__":
    main()

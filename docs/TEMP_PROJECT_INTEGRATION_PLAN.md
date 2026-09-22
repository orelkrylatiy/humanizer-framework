# Humanizer Framework

# План интеграции в реальные проекты AI max

Документ фиксирует конкретный план подключения Humanizer Framework к текущим репозиториям.

Состояние изучено по актуальным веткам `main` на 22 сентября 2026 года.

## Зафиксированные ревизии

- `humanizer-framework` `18d7181e750f1d92310e3aac4ab574d7afe7cc51`
- `profi-worker` `f97ae861ac3afa65a602531f16a762fef07f624f`
- `repetit-worker` `c63eee64c273198b856275c782e5d200aed5fe0e`
- `career-ops` `e3167f28c4d38aaadf566a75e2b4fda0a1dc70b3`
- `tg-ops` `ff772c7d3e2bebfde064266b8a1f7cb478f360d5`
- `hh-ops` `47c2eb47aa0c1776dd306cef0ee56237e7138e4a`

Этот документ нужно обновлять перед каждой реальной интеграцией, если соответствующий проект успел существенно измениться.

---

# 1. Главный принцип интеграции

Humanizer Framework не должен становиться новым монолитным агентом, который знает всю внутреннюю архитектуру каждого проекта.

Он должен быть общим communication layer.

Каждый проект по-прежнему сам решает

- что искать
- что фильтровать
- с кем работать
- какой профиль использовать
- можно ли отправлять сообщение
- какой аккаунт использовать
- какие side effects разрешены
- когда отправлять
- каким API или браузером отправлять
- как хранить состояние
- как делать dedup
- как обрабатывать rate limits
- когда нужен человек

Framework получает уже подготовленный communication context и решает

- что нужно сказать в текущем ходе
- насколько длинным должен быть ответ
- нужен ли вопрос
- допустим ли CTA
- какой message type сейчас используется
- какой channel style нужен
- какой voice использовать
- как сформировать prompt
- как проверить результат
- нужен ли один repair pass

Итоговая схема

```text
project
  |
  | business decision + facts + conversation
  v
Humanizer Framework
  |
  | planner
  | policy composition
  | prompt
  | LLM
  | validators
  v
final outgoing text
  |
  v
project transport and send safety
```

Самое важное разделение

```text
решение можно ли что-то делать
остается в проекте

решение что сказать сейчас
переходит во framework

формулировка сообщения
переходит во framework

фактическая отправка
остается в проекте
```

---

# 2. Что не надо переносить во framework

Нельзя превращать framework в копию всех текущих проектов.

Во framework не должны переезжать

- Playwright
- Telethon
- HeadHunter API
- Profi DOM logic
- Repetit API capture
- vacancy discovery
- hard filters
- resume routing
- browser sessions
- Telegram permissions
- HITL state
- SQLite конкретного продукта
- cron
- send locks
- anti duplicate send logic
- vacancy scoring
- job ranking
- CV tailoring
- application form interpretation
- marketplace payment logic

Framework должен оставаться тонким и переиспользуемым.

---

# 3. Что переезжает во framework

Общие communication responsibilities

- first outreach wording
- application message wording
- ongoing chat wording
- follow up wording
- scheduling wording
- objection wording
- recruiter reply wording
- tutoring client reply wording
- message length planning
- question planning
- CTA planning
- channel tone
- output language
- voice profile
- relevant voice examples
- anti AI patterns
- repeated CTA detection
- repeated structure detection
- deterministic punctuation normalization
- basic template similarity
- prompt boundaries
- one focused rewrite
- communication evals

---

# 4. Как подключать framework технически

## 4.1 Python проекты

Для Python проектов не нужно копировать исходники framework.

Нужно установить его как зависимость.

На раннем этапе лучше pin на commit.

Пример PEP 508

```toml
dependencies = [
    "humanizer-framework @ git+https://github.com/orelkrylatiy/humanizer-framework.git@18d7181e750f1d92310e3aac4ab574d7afe7cc51",
]
```

После появления versioned releases лучше перейти на обычную версию.

```toml
"humanizer-framework>=0.2,<0.3"
```

## 4.2 Два режима интеграции

Первый режим безопасный

```python
package = framework.prepare(request)
```

Проект продолжает использовать свой LLM client.

Framework только

- строит plan
- собирает system policy
- ограничивает history
- выбирает voice examples
- задает constraints

Это лучший первый шаг для уже работающего production проекта.

Второй режим полный

```python
result = framework.generate(request)
```

Framework дополнительно сам вызывает provider и делает validation плюс repair.

Переходить на него нужно только после regression tests.

## 4.3 JavaScript и TypeScript проекты

Текущий framework написан на Python.

`career-ops` написан в основном на Node.js и TypeScript.

Поэтому прямой Python import там невозможен.

Для таких проектов нужен один официальный bridge в самом Humanizer Framework.

Рекомендуемый контракт

```text
POST /v1/prepare
POST /v1/generate
POST /v1/validate
```

Либо CLI JSON bridge

```bash
humanizer-framework prepare --json request.json
humanizer-framework generate --json request.json
```

HTTP вариант предпочтительнее для long running web части Career Ops.

CLI вариант полезен для agent modes и локальных one shot процессов.

Нельзя переписывать planner и validators отдельно на JavaScript. Иначе снова появятся две реализации framework.

---

# 5. Что нужно добавить в framework до полной интеграции всех проектов

Текущая версия 0.1 уже достаточна для первого этапа Profi и Repetit.

Для всех проектов вместе нужны еще несколько extension points.

## 5.1 Async generation

`tg-ops` полностью async.

Текущий `CommunicationFramework.generate()` синхронный.

Нужно добавить один из вариантов

```python
await framework.agenerate(request)
```

или async provider protocol.

Без этого на первом этапе TG Ops должен использовать `prepare()` и свой текущий async LiteLLM client.

## 5.2 Finalize или validate prepared output

При `prepare()` проект получает prompt, но сейчас framework не предоставляет публичный удобный метод, который принимает внешний LLM output и возвращает normalized result.

Нужен API примерно такой

```python
result = framework.finalize(
    request=request,
    package=package,
    text=raw_text,
)
```

Он должен

- normalize output
- validate
- вернуть issues
- при необходимости отдельно позволить repair

Это особенно важно для Profi, Repetit и TG Ops, потому что у них уже есть свои provider fallback chains.

## 5.3 Trusted owner instruction

В TG Ops есть важный кейс

```text
владелец говорит
скажи что завтра после шести удобно
```

Это доверенная инструкция владельца.

Она не должна смешиваться с untrusted conversation text.

Нужно добавить отдельное поле

```python
trusted_instruction
```

или аналог.

Не стоит запихивать это просто в `context`, потому что context сейчас специально трактуется как untrusted factual data.

## 5.4 Дополнительные channels для Career Ops

Текущие built in channels

- profi
- repetit
- hh
- telegram
- generic

Career Ops реально использует также

- email
- linkedin
- job_board_chat
- boss или generic China job chat
- ats_form

Их лучше добавить как официальные channel policies.

## 5.5 Дополнительные message types для Career Ops

Текущие типы

- outreach
- application
- chat_reply
- follow_up
- scheduling
- objection

Для полного Career Ops дополнительно понадобятся

- cover_letter
- application_email
- application_answer
- referral_request
- process_recovery
- thank_you

Не обязательно делать все сразу.

## 5.6 Structured output

Для обычного чата достаточно одного `text`.

Для email часто нужно

```json
{
  "subject": "...",
  "body": "..."
}
```

Для application answers иногда нужно несколько независимых answers.

Поэтому framework позже нужен optional structured output contract.

Нельзя ломать основной простой `CommunicationResult.text`.

Лучше добавить optional artifact schema.

## 5.7 Rich conversation state

Для первого этапа хватает recent history.

Дальше желательно принимать caller supplied state

```json
{
  "known_facts": {},
  "already_discussed": [],
  "last_cta": null,
  "conversation_stage": "discovery"
}
```

Это позволит точнее избегать повторных вопросов и повторных продаж.

---

# 6. Profi Worker

## 6.1 Текущее назначение

`profi-worker` автоматизирует

```text
feed
-> hard filters
-> full order
-> semantic triage
-> first outreach
-> Profi send
```

и отдельно

```text
incoming chat
-> ownership checks
-> LLM reply
-> Profi send
```

Это первый и самый важный consumer Humanizer Framework, потому что именно здесь были обнаружены основные проблемы AI общения.

## 6.2 Текущие communication точки

Основные файлы

```text
src/profi/main.py
src/profi/fastpath.py
src/profi/llm/__init__.py
src/profi/llm/client.py
src/profi/copy_style.py
src/profi/profiles.py
personas/info.md
personas/lang.md
profiles/info.toml
profiles/languages.toml
docs/HUMAN_STYLE.md
```

### Первое сообщение

В `src/profi/main.py` используется `TRIAGE_SYSTEM`.

Он сейчас одновременно делает две задачи

- semantic decision respond или skip
- генерацию текста

Цель прямо зашита как договориться на пробное занятие.

Это нормально как broad business objective для первого outreach, но не должно использоваться для ongoing chat.

### Chat

В `src/profi/main.py`

```python
_answer_open_dialog(...)
```

вызывает LLM с

```python
CHAT_SYSTEM + _style_variation()
```

Дальше `src/profi/llm/__init__.py` еще раз добавляет

```python
CHAT_STYLE_OVERRIDE + style_variation("chat")
```

Получается несколько независимых style layers.

Это нужно убрать после интеграции.

### Локальный humanizer

`src/profi/copy_style.py` содержит

- outreach variants
- chat style override
- AI phrase detector
- style retry
- random chat composition

Большая часть этого должна стать ответственностью Humanizer Framework.

### Profiles

`profiles/info.toml`

- информатика
- программирование

`profiles/languages.toml`

- английский
- испанский

Это business profiles.

Они должны остаться в Profi Worker.

Framework получает selected profile id и только нужные факты.

### Personas

`personas/info.md` и `personas/lang.md` сейчас смешивают

- факты
- voice
- business restrictions

После интеграции их нужно разделить.

Факты остаются в Profi.

Voice уходит в `VoiceProfile`.

Platform specific business rules передаются отдельно.

## 6.3 Целевая архитектура Profi

```text
feed
-> hard filters
-> order facts
-> local triage decision
-> if respond
     Humanizer Framework
       domain tutoring
       channel profi
       message_type outreach
       profile info or languages
-> local contact guard
-> local payment and send gates
-> Profi UI send
```

Chat

```text
incoming Profi message
-> current turn ownership checks
-> Humanizer Framework
     domain tutoring
     channel profi
     message_type chat_reply
     selected profile
     recent conversation
-> local contact guard
-> recheck turn ownership
-> Profi UI send
```

## 6.4 Что должно остаться в Profi Worker

Обязательно оставить локально

- feed capture
- hard filters
- payment gates
- response price logic
- browser ownership
- work hours
- account mode
- send locks
- cooldown state
- chat unread detection
- exact turn ownership recheck
- Telegram control bot
- contact and URL safety guard
- profile selection
- account mapping
- fallback decision when LLM unavailable
- storage and logs

Framework не должен знать ничего о Profi DOM.

## 6.5 Что переносится из Profi во framework

После успешной миграции можно удалить или значительно сократить

```text
TRIAGE_SYSTEM communication style section
CHAT_SYSTEM communication style section
_HUMAN_STYLE
_style_variation()
CHAT_STYLE_OVERRIDE
OUTREACH_STYLE_OVERRIDE
_CHAT_SHAPES
client_copy_issues()
chat_retry_instruction()
style_retry_instruction()
```

Но это делать только после regression parity.

## 6.6 Как маппить Profi profile

Для `info`

```python
request = tutoring_request(
    channel="profi",
    message_type="outreach",
    profile="info",
    conversation=[],
    context={
        "client_name": order.client_name,
        "student_name": order.student_name,
        "order": public_order_context,
        "profile_facts": {
            "subjects": ["информатика", "программирование"],
            "work": "разработчик",
            "practice": ["Python", "алгоритмы"],
            "format": "онлайн",
        },
    },
    business_rules=[
        "Не выдумывать опыт, достижения и отзывы",
        "Не публиковать контакты и ссылки",
        "Не указывать цену в первом отклике",
    ],
    voice=info_voice,
)
```

Для языкового аккаунта

```python
profile="languages"
```

или в будущем отдельные runtime subprofiles

```text
english
spanish
chinese
```

Framework не должен предполагать предмет по channel.

Предмет всегда приходит из проекта.

## 6.7 Первый этап Profi

Использовать `prepare()`.

Причина

Profi уже имеет сложный собственный provider layer

```text
GLM
OpenAI compatible
Anthropic compatible
model fallback
API key fallback
cooldown
```

Его не надо менять одновременно с communication behavior.

Для этого Profi LLM client стоит расширить до messages API, чтобы он принимал `package.messages` без обратной склейки в две строки.

## 6.8 Второй этап Profi

Перевести generation на framework provider abstraction только если это даст реальную пользу.

Не обязательно делать это сразу.

Если существующий provider fallback лучше, можно долго оставаться на

```text
framework.prepare
+
profi provider transport
+
framework.finalize
```

Это нормальная архитектура.

## 6.9 Важное изменение первого outreach

Сейчас triage и writing связаны.

Лучше разделить.

Текущий conceptual flow

```text
LLM decides respond
+
LLM writes message
```

Целевой

```text
hard filters
-> semantic eligibility decision
-> if respond
     framework writes outreach
```

Так communication framework не будет отвечать за то, стоит ли вообще платить за отклик на конкретный Profi order.

## 6.10 Важное изменение chat

`CHAT_SYSTEM` больше не должен содержать глобальную установку, что каждый ход ведет к пробному.

Вместо этого business objective остается background context.

Planner определяет текущий turn.

Пример

```text
клиент
Задача делать домашки

planner
act disclosure
action acknowledge
allow_cta false
ask_question false
max_chars 180
```

Framework генерирует короткую реакцию.

Только когда conversation реально дошел до scheduling, planner разрешает следующий шаг.

## 6.11 Тесты Profi после интеграции

Обязательные новые tests

```text
test_framework_outreach_info_profile
test_framework_outreach_languages_profile
test_framework_chat_short_disclosure_no_cta
test_framework_chat_question_direct_answer
test_framework_chat_scheduling_allows_question
test_framework_does_not_repeat_trial_cta
test_framework_does_not_repeat_profile_intro
test_framework_name_in_first_outreach
test_framework_no_name_requirement_in_chat
test_framework_contact_guard_still_runs
test_framework_turn_revalidation_still_runs
test_framework_provider_failure_does_not_send
```

Существующие critical browser tests должны остаться без изменений.

## 6.12 Rollout Profi

1. Добавить dependency pinned на framework commit
2. Добавить `communication.py` adapter внутри Profi
3. Добавить request builders
4. Подключить только shadow generation
5. Сравнить старые и новые drafts на сохраненных fixtures
6. Подключить first outreach
7. Наблюдать реальные результаты
8. Подключить chat reply
9. Удалить local random style injection
10. Удалить duplicated copy style только после стабильных evals

---

# 7. Repetit Worker

## 7.1 Текущее назначение

`repetit-worker` сейчас автоматизирует только первый отклик.

Flow

```text
feed
-> hard filters
-> LLM triage
-> first message
-> exact chat state check
-> send
```

Контур ответов в существующих чатах пока не реализован.

Это делает интеграцию проще, чем в Profi.

## 7.2 Текущие communication точки

```text
src/repetit/integration/triage.py
src/repetit/llm/client.py
src/repetit/config.py
personas/maxim.md
docs/reference/HUMAN_STYLE.md
```

`integration/triage.py` сейчас содержит большой `_RULES`.

Он одновременно

- объясняет security
- определяет respond или skip
- задает message style
- задает first outreach objective

После этого `_style_variation()` случайно добавляет `)` примерно в 40 процентах сообщений.

Это нужно убрать.

## 7.3 Целевая архитектура Repetit

```text
feed capture
-> hard filters
-> semantic eligibility
-> if respond
     Humanizer Framework
       domain tutoring
       channel repetit
       message_type outreach
       profile informatics
-> local textguard
-> exact empty chat validation
-> send
```

## 7.4 Что остается локально

- Repetit feed capture
- order viewed protection
- hard filters
- budget filter
- work hours
- daily send limit
- worker lock
- chat state HTTP validation
- send ambiguity handling
- DOM confirmation
- screenshots
- Telegram alerts
- contact guard

## 7.5 Что переносится во framework

Можно убрать после migration

- human writing section из `_RULES`
- `_style_variation()`
- random smile injection
- duplicated humanizer reference
- local message length strategy, если она полностью покрыта constraints

Security instructions можно сократить, потому что framework уже имеет trust boundary.

Но platform contact prohibition лучше оставить и локальным deterministic guard.

## 7.6 Persona mapping

`personas/maxim.md` сейчас содержит реальные факты и tone rules.

Нужно разделить.

Trusted facts

```text
informatica
programming
Python
C++
C#
OGE
EGE
online
Moscow
```

Voice

```text
спокойный
короткий
конкретный
без рекламной гладкости
```

Business rules

```text
не выдумывать достижения
не давать контакты
не обещать баллы
```

## 7.7 Первый этап Repetit

Лучший вариант

```text
local semantic triage
+
framework.prepare
+
existing LLM provider
+
framework.finalize
```

Не менять provider layer сразу.

## 7.8 Будущий Контур Б

Когда в Repetit появятся ответы на входящие client messages, новый код сразу должен идти через framework.

Не надо копировать Profi `CHAT_SYSTEM`.

Нужно использовать

```python
channel="repetit"
message_type="chat_reply"
domain="tutoring"
```

## 7.9 Tests Repetit

```text
test_framework_first_outreach
test_framework_uses_client_name_when_known
test_framework_no_random_smile
test_framework_no_contacts
test_framework_does_not_invent_price
test_framework_preserves_first_message_budget
test_existing_chat_prevents_send_even_with_valid_framework_text
test_framework_failure_never_bypasses_send_guards
```

---

# 8. TG Ops

## 8.1 Текущее назначение

`tg-ops` уже концептуально очень близок к Humanizer Framework.

README прямо фиксирует разделение

```text
external agent decides intent
internal LLM owns final wording
deterministic policy owns permissions
```

Это почти та же архитектура, к которой мы пришли.

Поэтому TG Ops не нужно переписывать.

Нужно заменить его локальный communication engine общим framework.

## 8.2 Текущие communication точки

```text
src/tg_agent/agent/llm.py
src/tg_agent/agent/prompts.py
src/tg_agent/agent/reply.py
src/tg_agent/agent/sanitizer.py

prompts/system.ru.txt
prompts/persona.ru.txt
prompts/style.ru.txt
prompts/safety.ru.txt
prompts/reply/default.txt
prompts/reply/<chat_id>.txt
prompts/outreach/default.txt
prompts/outreach/<channel_id>.txt
```

Текущая архитектура уже разделяет

- provider
- prompts
- reply generation
- deterministic policy
- send

Это хороший consumer.

## 8.3 Что остается в TG Ops

Нельзя переносить

- Telethon
- aiogram control bot
- MCP
- DRAFT AUTO WATCH OFF
- trusted chat logic
- cooldown
- owner takeover
- sensitive topic review
- HITL
- SQLite
- vacancy scanner
- outreach dedup
- rate limits
- user validation
- MessageSender
- typing simulation
- Telegram send audit

Все это продуктовая execution logic.

## 8.4 Что заменяет framework

В перспективе можно удалить или сильно сократить

```text
PromptManager
prompts/system.ru.txt
prompts/style.ru.txt
prompts/safety.ru.txt
prompts/reply/default.txt
prompts/outreach/default.txt
clean_reply style heuristics
```

Но per chat и per channel behavior остается полезным.

Его нужно преобразовать в project supplied overrides.

## 8.5 Reply mapping

Текущий `ReplyGenerator.generate(...)` должен собирать

```python
CommunicationRequest(
    domain="generic" or "job_search",
    channel="telegram",
    message_type="chat_reply",
    profile=current_profile,
    conversation=history,
    context=known_facts,
    trusted_instruction=owner_instruction,
    voice=voice,
)
```

Если чат связан с job search

```text
domain job_search
```

Если это обычный личный диалог

```text
domain generic
```

## 8.6 Outreach mapping

Текущий vacancy outreach

```text
new vacancy
-> extract contact
-> draft Telegram outreach
```

должен использовать

```python
domain="job_search"
channel="telegram"
message_type="outreach"
```

Framework не решает, можно ли писать этому контакту.

Это по-прежнему решают monitored channel config, dedup, hourly limit, human user requirement и send policy.

## 8.7 Главный технический нюанс TG Ops

TG Ops использует async LiteLLM.

Framework 0.1 sync.

Поэтому нельзя сразу заменить `LLMClient`.

Первый этап

```text
framework.prepare
-> existing LLMClient.generate_reply
-> framework.finalize
```

После появления `agenerate()` можно решить, стоит ли переносить provider ownership.

## 8.8 Owner instructions

Текущий TG Ops поддерживает trusted instruction.

Правильная схема

```text
conversation text
untrusted

owner instruction
trusted

policy
trusted

voice examples
untrusted style only
```

## 8.9 Per chat overrides

Сейчас `prompts/reply/<chat_id>.txt` могут задавать relationship specific behavior.

После migration их лучше преобразовать в structured config.

Например

```yaml
chat_overrides:
  "12345":
    register: casual
    relation: friend
    preferred_length: very_short
    avoid:
      - formal greeting
```

Это потом превращается в `VoiceProfile` или trusted project rules.

Нельзя позволять таким overrides ослаблять safety.

## 8.10 Sanitizer

Текущий `clean_reply()` делает

- dash normalization
- greeting stripping
- repeated small talk question stripping

Часть должна переехать в framework validators.

Но Telegram specific greeting stripping может остаться channel specific validator.

Не все sanitizer rules должны становиться global.

## 8.11 Tests TG Ops

```text
test_framework_reply_uses_existing_context
test_framework_owner_instruction_is_trusted
test_framework_conversation_instruction_is_untrusted
test_framework_telegram_reply_is_short
test_framework_outreach_does_not_force_call
test_framework_does_not_repeat_question
test_framework_draft_mode_still_requires_approval
test_framework_auto_mode_still_requires_trust
test_framework_failure_never_sends
test_framework_exact_text_owner_path_bypasses_rewrite
```

Последний тест особенно важен.

Если владелец дает точный текст, TG Ops должен по-прежнему отправлять именно его, без humanizer rewrite.

---

# 9. HH Ops

## 9.1 Зачем включать HH Ops отдельно

`hh-ops` уже является реальным autonomous HeadHunter worker.

`career-ops` более широкий job search system.

Эти проекты пересекаются, но сейчас это два разных runtime.

Пока они оба используются, интеграцию нужно планировать отдельно.

## 9.2 Текущие communication surfaces

```text
src/hh_applicant_tool/operations/_apply_vacancies_ai.py
src/hh_applicant_tool/automation/reply_worker.py
src/hh_applicant_tool/automation/reply_fallback.py
scripts/reply_iterative_ai.py
prompts/cover_letter_frontend.txt
prompts/cover_letter_ai_engineer.txt
prompts/reply_employer.txt
```

Два главных сценария

```text
vacancy
-> cover letter
```

и

```text
employer message
-> rule classifier
-> REPLY_TEXT or IGNORE or MANUAL
-> LLM
-> humanizer
-> revalidate latest employer turn
-> HH API send
```

Второй flow очень хорошо подходит framework.

## 9.3 Что остается локально

- HH API
- applicant negotiations
- resume aliases
- multi profile
- apply lanes
- vacancy filters
- skip tests
- classifier IGNORE REPLY_TEXT MANUAL
- manual queue
- exact employer turn revalidation
- POST dedup
- fallback policy
- cron
- profile locks
- dry run live modes

Framework не должен решать `IGNORE` или `MANUAL`, потому что это side effect classification.

## 9.4 Reply mapping

Только после classifier verdict `REPLY_TEXT` строим

```python
request = job_search_request(
    channel="hh",
    message_type="chat_reply",
    profile=selected_resume_profile,
    conversation=message_history,
    context={
        "vacancy": vacancy_context,
        "candidate_facts": resume_facts,
        "employer": employer_context,
    },
    business_rules=hh_rules,
    voice=candidate_voice,
)
```

Потом framework генерирует только текст.

Перед POST обязательно остается existing re-read.

## 9.5 Cover letter mapping

Текущие `cover_letter_frontend.txt` и `cover_letter_ai_engineer.txt` содержат почти одинаковые style правила.

Разница должна быть в profile facts.

Целевой вариант

```python
channel="hh"
domain="job_search"
message_type="application"
profile="frontend"
```

или

```python
profile="ai-engineer"
```

Framework знает общую application behavior.

HH Ops передает факты конкретного resume.

## 9.6 Что можно удалить после migration

В перспективе

```text
prompts/reply_employer.txt
style section cover_letter_frontend.txt
style section cover_letter_ai_engineer.txt
local duplicated anti AI validator
```

Но resume facts и lane routing остаются.

## 9.7 Static fallback

Сейчас reply path может использовать static fallback при provider outage.

Это можно сохранить.

Но static fallback должен проходить framework validation.

Generic fallback плохо подходит к техническому вопросу или scheduling.

Поэтому в будущем лучше intent aware safe fallbacks или no send при provider failure.

## 9.8 Tests HH Ops

```text
test_framework_only_runs_after_reply_text_classifier
test_manual_class_never_calls_framework
test_ignore_class_never_calls_framework
test_framework_frontend_application
test_framework_ai_engineer_application
test_framework_recruiter_question
test_framework_scheduling_reply
test_framework_rejection_short_reply
test_framework_missing_fact_does_not_invent
test_framework_output_revalidated_against_latest_turn
test_framework_output_passes_existing_send_safety
```

---

# 10. Career Ops

## 10.1 Почему интеграция здесь сложнее

Career Ops не является одним Python worker.

Это большой Node.js, TypeScript, Go и agent skill проект.

Communication logic распределена между markdown modes, Node scripts, Web UI prompt builders и coding CLI.

Поэтому нельзя просто импортировать Python package в один файл.

Нужно сначала сделать официальный cross language bridge.

## 10.2 Что в Career Ops не относится к Humanizer Framework

Не надо трогать

- vacancy discovery
- ATS scanning
- offer evaluation
- scoring
- triage
- CV generation
- PDF rendering
- CV fact gate
- report generation
- tracker
- application state
- Playwright form extraction
- sensitive field confirmation
- form control interpretation
- resume selection
- autonomous submit verification

Даже если там используется LLM, это не human communication framework.

## 10.3 Реальные human facing communication surfaces

Изученные точки

```text
modes/contacto.md
modes/email.md
modes/followup.md
modes/cover.md
web/src/lib/apply/answer-prompt.mjs
config/profile.yml
voice-dna.md if present
```

Дополнительно communication artifacts могут появляться в application flows.

## 10.4 Contacto

`modes/contacto.md` создает

- LinkedIn outreach
- recruiter outreach
- hiring manager outreach
- peer outreach
- interviewer message
- short job board greeting

Это почти идеальный use case framework.

Target mapping для LinkedIn

```text
domain job_search
channel linkedin
message_type outreach
profile selected career profile
```

Short BOSS или job chat greeting

```text
domain job_search
channel job_board_chat
message_type outreach
```

Candidate facts приходят из `cv.md`, `config/profile.yml` и report.

Voice приходит из `voice-dna.md`.

Contact discovery остается в Career Ops.

## 10.5 Email mode

`modes/email.md` создает

- HR application email
- referral request
- cold application
- process stuck recovery
- confirmed time no show

Это тоже communication, но framework 0.1 пока не умеет хорошо возвращать subject плюс body.

Перед интеграцией нужен structured output.

Target mapping

```text
channel email
domain job_search
message_type application_email
```

Subtype можно передавать через trusted context или отдельное request field.

## 10.6 Followup mode

`modes/followup.md` очень хорошо ложится на `message_type follow_up`.

Career Ops по-прежнему сам

- считает cadence
- решает кому пора писать
- выбирает contact
- достает report
- достает proof points

Framework только формирует final draft.

Email follow up использует `channel email`.

LinkedIn follow up использует `channel linkedin`.

## 10.7 Cover letter

`modes/cover.md` намного длиннее обычного application message.

Текущий framework `application` ограничен примерно 700 символами и не предназначен для полноценного cover letter.

Есть два варианта.

Вариант A

На первом этапе не переносить full cover letter generation.

Оставить Career Ops как есть.

Использовать framework только как final humanizer pass.

Вариант B

Добавить отдельный `message_type cover_letter` с собственным long form policy и fact preservation.

Рекомендуется вариант A сначала.

Причина

Career Ops уже имеет

- research
- gap confirmation
- four prompt flow
- keyword mirroring
- fact gate
- PDF artifact format

Это отдельный сложный product flow.

Framework не должен ломать его ради унификации.

## 10.8 Application form answers

`web/src/lib/apply/answer-prompt.mjs` генерирует ответы на

- Why us
- project questions
- free text application answers

и отдельно не заполняет sensitive fields.

Это потенциальный будущий use case.

Но сначала framework должен поддерживать

```text
message_type application_answer
channel ats_form
```

и желательно structured field output.

На первом этапе этот модуль не трогаем.

Он уже имеет важные safety правила.

## 10.9 Reply Watch

`reply-watch.mjs` классифицирует входящие employer replies и обновляет tracker.

Это не generation.

Его не нужно переносить.

Если позже Career Ops начнет автоматически составлять ответ на конкретное recruiter email, тогда после classification вызывается framework.

## 10.10 Voice DNA

Career Ops уже имеет `voice-dna.md`.

Это нужно считать источником `VoiceProfile`.

Не надо дублировать его содержимое в framework repo.

Adapter Career Ops должен компактно преобразовывать его в

```json
{
  "id": "candidate-default",
  "description": "...",
  "prefer": [],
  "avoid": [],
  "examples": []
}
```

## 10.11 Profiles в Career Ops

`config/profile.yml` содержит гораздо больше данных, чем нужно communication layer.

Framework должен получать только необходимый subset.

Например frontend vacancy

```json
{
  "candidate_facts": {
    "role": "Frontend Developer",
    "stack": ["React", "TypeScript"],
    "proof_points": []
  },
  "vacancy": {
    "title": "...",
    "requirements": []
  }
}
```

## 10.12 Frontend и backend profiles

Для Career Ops разные карьерные направления должны быть caller selected profiles.

```text
frontend
backend
ai-engineer
fullstack
```

Framework не должен хранить их резюме.

Career Ops сам выбирает resume variant.

После выбора он передает соответствующие factual claims.

## 10.13 Cross language integration

Career Ops уже имеет `language.output`.

Его нужно напрямую маппить в `CommunicationRequest.language`.

Например

```text
en
ru
es
zh-CN
```

Framework не должен автоматически определять язык из JD, если Career Ops уже явно выбрал output language.

## 10.14 Технический bridge

Рекомендуемый вариант для Career Ops

Humanizer Framework запускается локально

```bash
humanizer-framework serve --host 127.0.0.1 --port 8877
```

Node adapter

```text
lib/humanizer-client.mjs
```

методы

```javascript
prepareCommunication(request)
generateCommunication(request)
validateCommunication(request, text)
```

Network только loopback.

Никаких platform credentials Career Ops не передает framework.

## 10.15 Agent skill integration

Career Ops часто выполняется самим coding agent через mode markdown.

В таких modes не нужно больше хранить огромные style instructions.

Mode должен описывать

- business workflow
- required facts
- target recipient
- side effect rules

А final wording должен запрашиваться у framework.

Conceptual flow

```text
modes/contacto.md
-> agent researches contact
-> agent builds communication request JSON
-> humanizer CLI or local API
-> final draft
```

## 10.16 Что нельзя удалять из Career Ops

Нельзя удалять

- `_writing.md` целиком сразу
- fact gates
- research confirmation gates
- ATS rules
- legal field confirmation
- report logic
- output artifact structure

Сначала переносим только message wording.

## 10.17 Tests Career Ops

Добавить Node integration tests с mock Humanizer service.

```text
contacto calls humanizer for final wording
contacto keeps contact discovery outside humanizer
followup cadence stays local
followup draft uses humanizer
email mode maps correct subtype
voice dna becomes voice profile
language output passes through
frontend and backend use different candidate facts
humanizer cannot change tracker status
humanizer cannot trigger send
application answer remains untouched in phase one
cover letter remains untouched in phase one
service unavailable fails safely
```

---

# 11. Приоритет интеграции проектов

Рекомендуемый порядок не по важности проекта, а по риску миграции.

## Этап 1

`profi-worker`

Причины

- из него возникла исходная проблема
- есть реальные regression cases
- Python
- framework уже поддерживает tutoring плюс Profi
- можно быстро проверить planner quality

## Этап 2

`repetit-worker`

Причины

- Python
- только first outreach
- маленькая communication surface
- хороший второй tutoring consumer

## Этап 3

`hh-ops`

Причины

- Python
- application плюс recruiter chat
- уже есть rule based classifier
- хороший job search consumer

## Этап 4

`tg-ops`

Перед этим добавить async плюс trusted owner instruction.

## Этап 5

`career-ops`

Перед этим добавить

- HTTP или JSON CLI bridge
- email channel
- linkedin channel
- structured output
- дополнительные message types

Не надо начинать Career Ops с полного переноса всех writing flows.

---

# 12. Общий migration contract

Для каждого проекта используем одинаковые три стадии.

## Stage A

Shadow mode.

Framework получает тот же context, но его text не отправляется.

Логируем

```text
old output
new output
planner decision
validation issues
```

## Stage B

Framework draft становится primary.

Transport остается прежним.

При framework failure можно временно использовать current local path, если fallback действительно безопасен для этого flow.

## Stage C

После стабильного production периода

- удаляем duplicated prompts
- удаляем random style injection
- удаляем duplicated humanizer validators
- pin framework version
- переносим regression fixtures в общий eval corpus

---

# 13. Общий project adapter pattern

В каждом Python consumer лучше иметь один небольшой adapter.

```text
src/<project>/communication.py
```

Он отвечает только за mapping local models в framework request.

```python
class CommunicationAdapter:
    def build_outreach(...)
    def build_chat_reply(...)
    def build_follow_up(...)
    def prepare(...)
    def finalize(...)
```

Нельзя размазывать создание `CommunicationRequest` по множеству файлов.

---

# 14. Что должно оставаться конфигом проекта

Framework не должен хранить персональные факты конкретных аккаунтов.

Локальные configs остаются.

Profi

```text
profiles/info.toml
profiles/languages.toml
account env
```

Repetit

```text
persona facts
subject settings
```

TG Ops

```text
owner profile
chat relationship overrides
channel config
```

HH Ops

```text
resume aliases
profile config
apply lanes
```

Career Ops

```text
config/profile.yml
cv.md
voice-dna.md
reports
```

Framework получает только projection этих данных.

---

# 15. Общий Voice contract

Voice не должен быть равен persona facts.

```python
VoiceProfile(
    id="maxim-chat",
    description="Коротко, спокойно, без рекламной гладкости",
    prefer=[
        "короткие прямые ответы",
        "обычный messenger rhythm",
    ],
    avoid=[
        "канцелярит",
        "формальные концовки",
        "повтор собеседника",
    ],
    examples=[
        "...",
        "...",
    ],
)
```

Факты никогда не берутся из examples.

---

# 16. Общий provider strategy

Не надо заставлять все проекты сразу использовать один provider.

Framework отвечает за communication behavior.

Provider ownership может мигрировать позже.

Рекомендуемая схема v1

Profi

```text
prepare
existing GLM/OpenAI/Anthropic transport
finalize
```

Repetit

```text
prepare
existing transport
finalize
```

HH Ops

```text
prepare
existing OpenAI compatible transport
finalize
```

TG Ops

```text
prepare
existing async LiteLLM
finalize
```

Career Ops

```text
local Humanizer HTTP service
generate
```

---

# 17. Failure behavior

Framework failure не должен менять side effect safety.

Правило

```text
generation failed
!=
permission to use arbitrary fallback and send
```

Каждый consumer должен явно решить fallback semantics.

Profi

- outreach может использовать проверенный profile fallback
- chat лучше молчать при LLM failure

Repetit

- первый outreach можно не отправлять
- не создавать unsafe generic fallback

HH Ops

- current static fallback нужно пересмотреть по intent
- лучше no send, чем неуместный generic answer

TG Ops

- DRAFT может показать failure владельцу
- AUTO не должен отправлять пустой или generic fallback text без policy

Career Ops

- draft generation может fail без side effect

---

# 18. Общий eval dataset

Нужно начать общий anonymized dataset в `humanizer-framework/evals`.

Каждый fixture должен содержать

```json
{
  "project": "profi-worker",
  "domain": "tutoring",
  "channel": "profi",
  "message_type": "chat_reply",
  "profile": "info",
  "conversation": [],
  "context": {},
  "expect": {}
}
```

Проверяем свойства, а не exact string.

---

# 19. Profi fixtures

Обязательно сохранить реальные кейсы.

## Светлана

Input

```text
Ему нужно еще и программирование
```

Expected

```text
action answer
allow_cta false
```

Следующий input

```text
Задача делать домашки
```

Expected

```text
action acknowledge
allow_cta false
ask_question false
```

Failure

```text
еще один trial pitch
scheduling question
повтор methodology
```

## Екатерина

После объяснения, что к ОГЭ еще не готовились.

Expected

```text
короткий discovery response
не generic reassurance paragraph
не forced trial CTA
```

## Виктор Word

First outreach.

Expected

```text
known client name
short relevance
one question max
paragraph spacing if long
```

---

# 20. Job search fixtures

## Recruiter technical question

```text
С React 19 работали?
```

Expected

```text
answer only from candidate facts
no repeated cover letter
no unrelated CTA
```

## Scheduling

```text
Сможете завтра в 15:00?
```

Expected

```text
schedule action
use known availability only
no invented acceptance
```

## Missing fact

```text
Какой у вас текущий уровень английского?
```

Если факт не передан

```text
do not invent
```

## Rejection

```text
Мы выбрали другого кандидата
```

Expected

```text
very short polite reaction
no sales follow up
```

---

# 21. Anti template memory

Особенно важно для

- Profi first outreach
- Repetit first outreach
- Telegram vacancy outreach
- HH application messages
- Career contacto

Проект должен передавать recent outgoing messages.

Framework уже делает basic similarity по conversation history.

Дальше лучше добавить отдельный optional `recent_outputs`, чтобы first outreach к разным людям тоже сравнивался с предыдущими outbound messages аккаунта.

Иначе у нового диалога conversation history пустая и anti template память не работает.

---

# 22. Security boundaries

Во всех проектах одинаковое правило.

Trusted

- project business rules
- selected profile facts
- explicit owner instruction
- framework policy

Untrusted

- client message
- recruiter message
- vacancy text
- job description
- marketplace order description
- Telegram channel post
- voice example text

Framework должен маркировать это явно.

---

# 23. Privacy and context minimization

Нельзя передавать framework все данные проекта.

Примеры лишних данных

- API keys
- cookies
- browser session
- full database row
- raw HTML
- hidden admin fields
- entire CV when enough selected facts
- full order JSON when достаточно public summary

Adapter должен делать projection.

---

# 24. Observability

Каждый framework result желательно логировать structured metadata.

Без client private text в обычном ops log.

Минимум

```json
{
  "framework_version": "0.2.x",
  "project": "profi-worker",
  "channel": "profi",
  "message_type": "chat_reply",
  "profile": "info",
  "action": "acknowledge",
  "target_length": "very_short",
  "allow_cta": false,
  "ask_question": false,
  "rewritten": false,
  "issue_codes": []
}
```

---

# 25. Versioning

Consumer не должен зависеть от `main` без pin.

Для production используем version или fixed commit.

Любое изменение planner behavior считается потенциально behavior changing, даже если Python API не изменился.

Release notes должны отдельно содержать

```text
planner changes
policy changes
validator changes
provider changes
```

---

# 26. CI strategy

В самом framework

- unit tests
- planner fixtures
- validator tests
- policy tests
- provider adapter tests
- API bridge tests

В каждом consumer

- adapter mapping tests
- integration tests with MockProvider
- current send safety tests
- regression fixtures specific to project

Нельзя переносить browser E2E во framework.

---

# 27. Что делать с существующими configs и prompts

Ничего массово не удалять в первой интеграции.

Правильный порядок

```text
old prompt exists
new framework shadow runs
compare
framework becomes primary
old prompt remains rollback
production stabilizes
delete duplication
```

Это особенно важно для Profi и TG Ops.

---

# 28. Конкретные новые файлы по проектам

## Humanizer Framework

Добавить

```text
docs/PROJECT_INTEGRATIONS.md
src/humanizer_framework/async_framework.py
src/humanizer_framework/bridge/
src/humanizer_framework/finalize.py
```

Вероятные additions

```text
email channel
linkedin channel
trusted_instruction
recent_outputs
structured output
Career Ops message types
```

## Profi Worker

Добавить

```text
src/profi/communication.py
tests/test_communication_framework.py
```

Позже удалить duplication из

```text
src/profi/copy_style.py
src/profi/main.py
src/profi/llm/__init__.py
```

## Repetit Worker

Добавить

```text
src/repetit/communication.py
tests/test_communication_framework.py
```

Refactor `src/repetit/integration/triage.py` на eligibility decision плюс message generation.

## TG Ops

Добавить

```text
src/tg_agent/agent/communication.py
tests/test_communication_framework.py
```

После migration сократить

```text
src/tg_agent/agent/prompts.py
src/tg_agent/agent/reply.py
src/tg_agent/agent/sanitizer.py
prompts/
```

## HH Ops

Добавить

```text
src/hh_applicant_tool/communication/
tests/test_communication_framework.py
```

Integrate into

```text
automation/reply_worker.py
operations/_apply_vacancies_ai.py
```

## Career Ops

Добавить

```text
lib/humanizer-client.mjs
tests/humanizer-client.test.mjs
```

И в framework добавить HTTP или CLI bridge.

Дальше постепенно менять

```text
modes/contacto.md
modes/followup.md
modes/email.md
```

---

# 29. Definition of Done для одного consumer

Проект считается интегрированным, когда

- production communication проходит через framework
- side effect policy осталась локальной
- selected profile facts корректно передаются
- voice отделен от facts
- known conversation history передается bounded
- planner decision логируется
- framework validation вызывается
- old local style prompt больше не primary
- regression fixtures проходят
- provider failure не приводит к unsafe send
- rollback path понятен
- docs обновлены

---

# 30. Definition of Done для всей программы

Humanizer Framework можно считать реальным shared communication platform, когда

- Profi Worker использует его для outreach и chat
- Repetit Worker использует его для first outreach и будущего chat
- HH Ops использует его для application copy и employer replies
- TG Ops использует его для reply и outreach
- Career Ops использует его минимум для contacto, followup и email draft
- один voice improvement можно выпустить framework version и получить его во всех consumers
- один planner regression test защищает несколько проектов
- ни один consumer не хранит отдельную копию общего humanizer prompt
- project specific facts и side effect policy не переехали во framework

---

# 31. Итоговая рекомендуемая схема

```text
                    Humanizer Framework
          planner + policy + voice + validators
                    /       |       \
                   /        |        \
                  /         |         \
          tutoring       job search    generic
             |               |            |
        Profi/Repetit     HH/Career     Telegram
             |               |            |
             +---------------+------------+
                             |
                       final text
                             |
             project specific send layer
```

Для каждого проекта framework один и тот же.

Меняются runtime параметры

```text
domain
channel
message_type
profile
language
conversation
context
business_rules
voice
constraints
```

Не создаются отдельные forks для

- информатики
- китайского
- испанского
- frontend
- backend
- AI Engineer

Это profiles и caller context.

---

# 32. Ближайший практический шаг

До начала массовой интеграции стоит сделать небольшой framework 0.2 hardening.

Минимальный набор

1. `finalize()` для внешнего provider output
2. `agenerate()` или async provider protocol
3. `trusted_instruction`
4. `recent_outputs`
5. JSON CLI bridge
6. HTTP bridge
7. email и linkedin channels
8. базовый structured output contract

После этого начать `profi-worker` в shadow mode.

Дальше подключать проекты в порядке

```text
profi-worker
repetit-worker
hh-ops
tg-ops
career-ops
```

Это даст максимум реальных данных при минимальном риске и не заставит переписывать работающие execution layers.
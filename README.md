# Humanizer Framework

Русскоязычный движок естественной AI-переписки. Python-библиотека 0.5.0
планирует ответы, обращается к модели, проверяет ограничения и факты.
Отдельный агентский навык SKILL.md содержит 26 приемов upstream
blader/humanizer v4.0.0 и совместим с Claude Code, Cursor, Codex и pi.

## Установка и тесты

    pip install -e '.[dev]'
    ruff check .
    ruff format --check .
    pytest
    python scripts/validate-package.py

## Использование

    from humanizer_framework import CommunicationFramework, Message, tutoring_request

    request = tutoring_request(
        channel="profi",
        message_type="chat_reply",
        profile="informatics",
        conversation=[Message("user", "Нужна помощь с домашними заданиями")],
        context={"subjects": ["информатика"]},
    )
    framework = CommunicationFramework()
    prepared = framework.prepare(request)  # без вызова модели
    text = framework.generate(request)    # полноценная генерация
    print(text)

Также доступна функция write() для одного вызова.
Существующие типы сообщений - outreach, application, channel_post,
chat_reply, follow_up, scheduling, objection. Поддерживаются Profi, Repetit,
hh, Telegram и собственные каналы. Язык по умолчанию русский. Английский,
испанский и китайский оставлены для совместимости клиентских приложений,
но все встроенные системные инструкции русскоязычные.

## Модели и резервирование

Стандартная цепочка сначала пробует Z.AI GLM-5.3-Flash, затем OpenCode CLI,
затем OpenAI API с моделью gpt-4.1-mini. Модели OpenCode и OpenAI API
можно изменить переменными HUMANIZER_OPENCODE_MODEL и
HUMANIZER_OPENAI_API_MODEL. Ключ ZAI_API_KEY имеет приоритет над
ANTHROPIC_AUTH_TOKEN и ANTHROPIC_API_KEY. Нужны действительные ключи
и доступность провайдеров. Можно также передать LiteLLM, Claude CLI,
OpenCode-пул или собственную реализацию.

## Проверка сообщений

Критические ошибки запрещают выдачу результата. При правке сначала
сравниваются критические нарушения, затем стилистические замечания.
Если необязательная правка не получилась, сохраняется первоначальный
допустимый вариант.

Дополнительная проверка ищет неподтвержденные числа, некоторые заявления
об управлении и квалификации, гарантии, обещания свободного времени.
Источники - context, business_rules и числа из вопросов собеседника.
Для расписания передавайте context со slots, availability или schedule.

Проверка не равна внешней проверке достоверности. Она не сверяется
с реальным календарем и не доказывает истинность резюме. Для надежной
автономной переписки передавайте проверенные факты со стороны продукта.

Русские сообщения по умолчанию нормализуют «ё» в «е», длинные тире
в короткий дефис, а стилистические двоеточия в запятые. Время 18:30,
URL и текстовые смайлики вроде :) не меняются. В переписке на hh
смайлики запрещены.

## Логирование и приватность

Технические события JSONL не содержат тексты сообщений и сырые ошибки.
Идентификаторы клиента отключены по умолчанию. Для отключения всех логов
установите HUMANIZER_TELEMETRY=0. Для выбора файла используйте
HUMANIZER_TELEMETRY_PATH. Явное HUMANIZER_TELEMETRY_IDENTIFIERS=1
включает lead, chat и другие идентификаторы. Новый формат имеет
schema_version=2, старые журналы могут содержать больше данных.

## Навык и редакторские приемы

Корневой SKILL.md - единственный файл навыка. Манифесты для разных
агентов находятся в .claude-plugin, .cursor-plugin, agents/openai.yaml
и package.json. Документация переноса в docs/UPSTREAM_SYNC.md.

| № | Проверка |
| --- | --- |
| 1 | Искусственное противопоставление |
| 2 | Однострочный вывод и обрывки |
| 3 | Псевдоглубокие фразы |
| 4 | Постановочное вступление |
| 5 | Спор с несуществующим возражением |
| 6 | Механические тройки |
| 7 | Повтор начала предложений |
| 8 | Тире вместо связи |
| 9 | Нагромождение оговорок |
| 10 | Механические сложные определения |
| 11 | Безличная речь |
| 12 | Типовые AI-слова |
| 13 | Преувеличенная значимость |
| 14 | Расплывчатые связи |
| 15 | Пустые хвосты |
| 16 | Рекламные эпитеты |
| 17 | Заимствованный авторитет |
| 18 | Избегание простых глаголов |
| 19 | Жирный шрифт для декора |
| 20 | Декоративные заголовки |
| 21 | Несоответствующие кавычки |
| 22 | Остатки чат-бота |
| 23 | Отговорки и догадки |
| 24 | Дублирование заголовка |
| 25 | Рассказ о подготовке текста |
| 26 | Повтор известного собеседнику |

Все 26 приемов разобраны с примерами и исключениями в SKILL.md.
Это инструменты редактирования, а не способ гарантированно распознать AI.

## Документация

- docs/ARCHITECTURE.md - архитектура
- docs/INTEGRATION.md - интеграция
- docs/UPSTREAM_SYNC.md - состояние upstream
- CHANGELOG.md - история изменений

CI проверяет Python 3.11, 3.12, 3.13 без реальных облачных вызовов.


## Web admin

Install the optional web dependencies and start the local admin:

    pip install -e '.[admin]'
    humanizer-admin

Open http://127.0.0.1:8765. The admin provides the seven existing message modes, prompt and context inputs, voice settings, a prompt preview via prepare(), and generation via generate(). It also shows provider configuration and content-free activity from the existing JSONL telemetry. The core package remains dependency-free; see docs/ADMIN.md for setup, remote-access security and privacy details.

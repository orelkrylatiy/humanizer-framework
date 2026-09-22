# Humanizer Framework

Humanizer Framework is a reusable communication layer for LLM-powered products.

It is designed for systems that communicate with people across tutoring marketplaces, job boards, messengers and similar channels.

The framework does more than rewrite AI-sounding text. It first decides what the current turn needs, composes a small policy from domain, channel, message type, language, voice and conversation state, calls an optional provider, validates the output and returns communication metadata with the final text.

## Why this exists

Many poor automated conversations fail before wording.

A model can answer a short disclosure with a full sales block, repeat a trial CTA, ask for information already supplied, or reuse the same polished skeleton across many recipients.

Those are conversation-policy failures.

The framework separates decision from wording.

Flow

product context
to deterministic planner
to composable communication policy
to bounded prompt and selected voice examples
to provider
to deterministic validators
to outgoing message

## Initial scope

Domains

- tutoring
- job_search

Channels

- Profi.ru
- Repetit
- HeadHunter
- Telegram
- custom registered channels

Profiles remain caller-owned.

A tutoring product can select informatics, Chinese or Spanish without duplicating channel logic.

A job-search product can select frontend, backend or another resume profile without duplicating HeadHunter logic.

## Message types

Built-in message types

- outreach
- application
- chat_reply
- follow_up
- scheduling
- objection

The planner further chooses the intended reply action such as acknowledge, answer, handle objection or schedule.

## Install

Editable install

    pip install -e .

Cloud providers through LiteLLM

    pip install -e '.[llm]'

Development

    pip install -e '.[dev]'
    pytest
    ruff check .

## Prompt-only integration

Existing products can keep their current model client.

Example

    from humanizer_framework import CommunicationFramework, Message, tutoring_request

    framework = CommunicationFramework()

    request = tutoring_request(
        channel="profi",
        message_type="chat_reply",
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
        context={"subjects": ["informatics", "programming"]},
    )

    package = framework.prepare(request)

package.messages can then be sent through the project's existing LLM client.

## Full generation

Example

    from humanizer_framework import CommunicationFramework, LiteLLMProvider

    provider = LiteLLMProvider("zai/glm-4.7")
    framework = CommunicationFramework(provider)

    result = framework.generate(request)
    print(result.text)

LiteLLM keeps provider selection outside communication policy. The model string can point to supported OpenAI, Anthropic, Gemini, Z.AI or GLM, Ollama and other backends.

CLI adapters are also available for environments already authenticated with Codex or Claude Code.

    from humanizer_framework import CodexCLIProvider, ClaudeCLIProvider

## Configuration

A project may keep provider configuration in TOML.

    strict = false

    [provider]
    kind = "litellm"
    model = "zai/glm-4.7"

Provider settings do not contain domain or profile facts. Those remain in the calling product.

## Core design rules

1. Conversation policy is separate from wording.
2. The writer does not decide on its own that every turn needs a CTA.
3. Profiles contain caller-owned identity and facts. Voice is separate.
4. External conversation text, context values and voice examples are untrusted data.
5. Caller conversation history cannot create provider system messages.
6. Mechanical rules are code when possible.
7. Context, history and examples are bounded.
8. prepare mode supports incremental migration.
9. generate mode owns the full communication flow.
10. Provider choice is replaceable and optional.

## Documentation

Start here

- Product requirements document in docs/PRD.md
- Product concept and rationale in docs/CONCEPT.md
- Architecture in docs/ARCHITECTURE.md
- Compact implementation requirements in docs/REQUIREMENTS.md
- Integration and migration guide in docs/INTEGRATION.md
- Research and design analysis in docs/ANALYSIS.md
- Independent implementation review in docs/REVIEW_2026-09-22.md

## Testing

The default CI is credential-free.

It runs

- Ruff
- Pytest
- Python 3.11
- Python 3.12
- Python 3.13

Real cloud-provider calls are intentionally not part of default CI.

## Project status

Version 0.1 is the framework foundation.

Implemented

- reusable Python package
- deterministic planner
- tutoring and job-search domains
- Profi, Repetit, HeadHunter and Telegram channel policy
- outreach, application and chat message modes
- Russian, English, Spanish and Chinese language policy
- bounded conversation context
- relevance-based voice example selection
- prompt-injection trust boundaries
- deterministic validators
- one focused repair pass
- anti-template similarity check
- LiteLLM provider
- GLM routing through LiteLLM
- Codex CLI provider
- Claude Code CLI provider
- regression fixtures
- CI

The next major step is integration into a real consumer, starting with Profi Worker, and expansion of the anonymized real-conversation evaluation dataset.

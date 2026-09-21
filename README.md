# Humanizer Framework

Humanizer Framework is a reusable communication layer for LLM-powered products. It is designed for systems that communicate with people across tutoring marketplaces, job boards, messengers and similar channels.

It does more than rewrite AI-sounding text. The framework first decides what the current turn needs, then composes a small prompt from domain, channel, message type, voice and conversation state, calls an optional LLM provider, validates the result, and returns the outgoing message.

## Why this exists

A text humanizer can fix wording after generation, but many bad conversations start earlier. A model may answer a short disclosure with a full sales block, repeat a trial CTA, ask for information already provided, or reuse the same message skeleton across many recipients. Those are conversation-policy failures, not only style failures.

The framework separates these concerns.

```text
product context
    -> deterministic planner
    -> composable communication policy
    -> compact prompt + selected voice examples
    -> provider
    -> deterministic validators
    -> outgoing message
```

## Initial domains and channels

The first release ships reusable domain policies for tutoring and job search. Channel presets include Profi.ru, Repetitor.ru, HeadHunter and Telegram. Projects can register more channels without forking the framework.

Profiles remain caller-owned. A tutoring product can have separate profiles for informatics, Chinese and Spanish. A job-search product can have separate frontend and backend candidate profiles. The framework receives the selected profile facts and voice at runtime.

## Message types

Built-in message types are

- `outreach`
- `application`
- `chat_reply`
- `follow_up`
- `scheduling`
- `objection`

The planner further classifies the current turn and chooses a reply action such as acknowledge, answer, handle objection or schedule.

## Install

```bash
pip install -e .
```

For cloud model providers through LiteLLM

```bash
pip install -e '.[llm]'
```

For development

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## Prompt-only integration

Existing projects do not need to replace their LLM stack immediately.

```python
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
# package.messages can be sent through the project's existing LLM client
```

## Full generation

```python
from humanizer_framework import CommunicationFramework, LiteLLMProvider

provider = LiteLLMProvider("zai/glm-4.7")
framework = CommunicationFramework(provider)
result = framework.generate(request)
print(result.text)
```

LiteLLM keeps provider selection outside the communication architecture. The model string can point to OpenAI, Anthropic, Gemini, Z.AI/GLM, Ollama and many other supported backends.

CLI adapters are also available for environments already authenticated with Codex or Claude Code.

```python
from humanizer_framework import CodexCLIProvider, ClaudeCLIProvider
```

## Configuration

A project may keep provider configuration in TOML.

```toml
strict = false

[provider]
kind = "litellm"
model = "zai/glm-4.7"
```

Or use a local CLI.

```toml
[provider]
kind = "codex-cli"
```

Provider settings do not contain domain or profile facts. Those stay in the calling product.

## Design rules

The framework follows a few hard boundaries.

1. Conversation policy is separate from wording. The writer does not decide on its own that every turn needs a CTA.
2. Profiles contain facts and voice, not channel behavior.
3. Mechanical rules are code when possible. Length, question count, repeated CTA patterns, recent-template similarity and language normalization do not need extra prompt tokens.
4. Context stays bounded. The prompt includes a limited recent history, compact known context and at most a few voice examples.
5. The framework supports both `prepare()` and `generate()` so existing products can migrate incrementally.
6. Provider choice is replaceable and optional.

## Documentation

- [Research and design analysis](docs/ANALYSIS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Integration and migration](docs/INTEGRATION.md)

## Project status

Version `0.1.0` is the first framework cut. It implements the shared core, deterministic planner, policy composition, prompt budgeting, Russian messenger normalization, anti-template checks, provider abstraction, LiteLLM support, Codex and Claude CLI adapters, tests and CI.

The next quality step is to add a larger anonymized conversational evaluation dataset from real tutoring and job-search flows, then run model-backed comparison suites against it.

# Humanizer Framework

Humanizer Framework is a reusable communication layer for LLM-powered products.

It is designed for systems that communicate with people across tutoring marketplaces, job boards, messengers and similar channels.

The framework does more than rewrite AI-sounding text. It first decides what the current turn needs, composes a small policy from domain, channel, message type, language, voice and conversation state, calls an optional provider, validates the output and returns validated outgoing text. Hard-invalid text is never returned.

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

Zero-config generation needs no provider argument. The framework uses its
default chain: OpenCode CLI, then direct HTTP to Z.AI, then the OpenAI API.
Each backend resolves its own credentials from the environment:

    from humanizer_framework import CommunicationFramework

    framework = CommunicationFramework()
    text = framework.generate(request)

The direct Z.AI backend uses `glm-5.3-flash` with thinking enabled, as required
by that model. If all backends fail, generation raises `ProviderExecutionError`.

To use a different backend, pass a provider explicitly.

Example

    from humanizer_framework import CommunicationFramework, LiteLLMProvider

    provider = LiteLLMProvider("zai/glm-4.7")
    framework = CommunicationFramework(provider)

    text = framework.generate(request)
    print(text)

LiteLLM keeps provider selection outside communication policy. The model string can point to supported OpenAI, Anthropic, Gemini, Z.AI or GLM, Ollama and other backends.

Agent-backed generation uses OpenCode for every model provider.

    from humanizer_framework import (
        HarnessProvider,
        OpenCodeCLIProvider,
        openai_api_provider,
        zai_api_provider,
    )

    gpt = openai_api_provider(
        credential_source_file=(
            "~/AppData/Roaming/hh-applicant-tool/0555/config.json"
        ),
        credential_source_json_path="openai_reply.api_key",
    )
    glm = zai_api_provider(
        credential_source_file="~/.claude/settings.json",
        credential_source_json_path="env.ANTHROPIC_AUTH_TOKEN",
    )
    provider = HarnessProvider.opencode_provider_pool([gpt, glm])

CLI providers run one isolated, non-interactive turn. They do not continue the user's last session or expose the caller's project directory. The OpenCode adapter parses JSONL events and surfaces provider errors as typed framework errors.

The default agent harness spawns only OpenCode:

    provider = HarnessProvider.opencode_first(
        "openai/gpt-6-luna",
    )
    framework = CommunicationFramework(provider)

To rotate between several OpenCode models or providers while retaining
failover, build an OpenCode-only pool:

    provider = HarnessProvider.opencode_pool(
        [
            {"model": "openai/gpt-6-luna"},
            {
                "model": "zai-coding/glm-5.3-flash",
                "credential_source_file": "~/.claude/settings.json",
                "credential_source_json_path": "env.ANTHROPIC_AUTH_TOKEN",
                "credential_target_env": "ZAI_API_KEY",
                "opencode_config": zai_config,
            },
        ]
    )

The pool rotates its starting backend per request and tries the remaining
OpenCode backends if that backend fails.

The OpenCode model is mandatory and uses `provider/model`. This prevents an
implicit default from silently selecting another provider. `agent` and
`variant` can be passed through `opencode_options`.

OpenCode v2 can save several accounts for one provider, but only one is active
at a time. For concurrent key rotation, configure a pool with secret values in
environment variables:

    provider = HarnessProvider.opencode_first(
        "openai/gpt-6-luna",
        credentials=[
            {
                "credential_source_env": "HUMANIZER_OPENAI_KEY_1",
                "credential_target_env": "OPENAI_API_KEY",
            },
            {
                "credential_source_env": "HUMANIZER_OPENAI_KEY_2",
                "credential_target_env": "OPENAI_API_KEY",
            },
        ],
    )

Each request starts at the next key. Every key-backed OpenCode process gets an
isolated credential database, so it cannot be shadowed by or mutate the user's
active OpenCode account. Secret values are never copied into framework config.

A GLM Coding Plan key already stored in Claude Code settings can be consumed
without duplicating the secret:

    glm = OpenCodeCLIProvider(
        model="zai-coding/glm-5.3-flash",
        credential_source_file="~/.claude/settings.json",
        credential_source_json_path="env.ANTHROPIC_AUTH_TOKEN",
        credential_target_env="ZAI_API_KEY",
        opencode_config={
            "provider": {
                "zai-coding": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Z.AI Coding",
                    "options": {
                        "baseURL": "https://api.z.ai/api/coding/paas/v4",
                        "apiKey": "{env:ZAI_API_KEY}",
                    },
                    "models": {"glm-5.3-flash": {"name": "GLM-5.3 Flash"}},
                }
            }
        },
    )

The framework reads the JSON value only for the child process. It does not put
the key in source code, TOML, logs or the provider object.

An OpenAI API key uses a separate OpenCode custom provider. For example, an
existing hh-applicant-tool profile can remain the secret source:

    gpt = OpenCodeCLIProvider(
        model="openai-api/gpt-4.1-mini",
        credential_source_file=(
            "~/AppData/Roaming/hh-applicant-tool/0555/config.json"
        ),
        credential_source_json_path="openai_reply.api_key",
        credential_target_env="OPENAI_API_KEY",
        opencode_config={
            "provider": {
                "openai-api": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "OpenAI API",
                    "options": {
                        "baseURL": "https://api.openai.com/v1",
                        "apiKey": "{env:OPENAI_API_KEY}",
                    },
                    "models": {"gpt-4.1-mini": {"name": "GPT-4.1 mini"}},
                }
            }
        },
    )

## Configuration

A project may keep provider configuration in TOML.

    [provider]
    kind = "litellm"
    model = "zai/glm-4.7"

Other provider examples

    [provider]
    kind = "opencode-cli"
    model = "openai/gpt-6-luna"

    [provider]
    kind = "harness"
    model = "openai/gpt-6-luna"

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

Version 0.2 adds a fail-closed string generation contract and isolated CLI providers.

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
- isolated OpenCode harness for OpenAI and Z.AI API providers
- provider retry and fail-closed hard validation
- regression fixtures
- CI

The next major step is integration into a real consumer, starting with Profi Worker, and expansion of the anonymized real-conversation evaluation dataset.

# Telemetry

Generation calls write one technical JSONL event by default. The event contains
UTC time, project, channel/domain/message type/profile, optional lead/recipient
identity from request context, provider/model, latency, attempts, repair status,
validation issues, errors, and provider-reported token usage. Prompts and output
texts are never written.

Set `HUMANIZER_TELEMETRY_PATH` to choose a file, or
`HUMANIZER_TELEMETRY=0` to disable it. Other consumers need no code changes;
editable installs pick up the framework update automatically. Consumers that
want a project-specific file can set the path before importing/generating.


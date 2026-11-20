# Web admin

Humanizer Framework includes an optional local web admin for interactive generation. It is a thin UI over the existing Python API; it does not implement a second prompt engine or bypass validation.

## Install

From a checkout:

    pip install -e '.[admin]'

Or install the package with the admin extra:

    pip install 'humanizer-framework[admin]'

The admin extra installs FastAPI and Uvicorn. The core library remains dependency-free.

## Configure providers

The admin uses the same default provider chain as CommunicationFramework():

1. Z.AI / GLM using ZAI_API_KEY (or the supported Anthropic-compatible key variables);
2. OpenCode CLI using its local authentication and HUMANIZER_OPENCODE_MODEL;
3. direct OpenAI API using OPENAI_API_KEY and HUMANIZER_OPENAI_API_MODEL.

Set credentials in the environment or in the .env file used by Humanizer Framework. The UI only reports whether a credential is present; it never returns its value.

## Run

    humanizer-admin

Open http://127.0.0.1:8765.

You can also run:

    python -m humanizer_framework.admin --host 127.0.0.1 --port 8765

The server binds to loopback by default. Stop it with Ctrl+C.

## Remote access

Do not expose the admin directly to the public internet. If LAN access is required, set a long random token and explicitly allow the hostname used by the browser:

    export HUMANIZER_ADMIN_TOKEN='replace-with-a-long-random-secret'
    export HUMANIZER_ADMIN_ALLOWED_HOSTS='localhost,127.0.0.1,::1,192.168.1.20'
    humanizer-admin --host 0.0.0.0 --port 8765

The browser asks for the token when the API returns 401. It is kept in session storage for the current tab. The token is never written to the repository or telemetry. Use a trusted private network or a VPN; do not forward this port to the public internet.

## What the UI controls

- Mode: all seven MessageType values already supported by the framework.
- Domain, channel, language and profile: the same request dimensions used by Python callers.
- Prompt: mapped to the framework's existing business_rules goal instruction.
- Source text: passed as an incoming conversation message, with the same role normalization and 1,800-character per-message bound as the core prompt builder.
- Facts/context: structured JSON, bounded to 3,500 characters.
- Voice: description, preferences, avoid-list and up to three examples.
- Prompt preview: calls CommunicationFramework.prepare() with a mock provider. It does not contact a model.
- Generate: calls CommunicationFramework.generate(), including provider fallback, normalization, validators and the optional repair attempt.

The deterministic planner and hard validators remain authoritative. For example, a prompt cannot force a question or CTA when the selected mode's plan forbids it. Choose a mode that matches the intended communication action.

## Activity and privacy

The Activity view reads the existing JSONL telemetry file. It shows only allowlisted technical fields: timestamp, status, elapsed time, mode, channel, provider/model, retry counts and validation issue codes. It does not show prompt text, source text, generated text, identifiers or raw provider exceptions.

The UI does not persist prompts or generated output. The model provider receives the prompt and supplied context as part of normal generation. To disable telemetry:

    export HUMANIZER_TELEMETRY=0

The telemetry path can be changed with HUMANIZER_TELEMETRY_PATH. The activity view will show an empty state if telemetry is disabled or no events have been recorded.

## Troubleshooting

- ProviderExecutionError: check the provider status page, credentials, model availability and the server output.
- OpenCode is shown as available when its executable is on PATH; the admin does not run an authentication test.
- A 422 response means the generated text failed a hard framework validator. The rejected text and issue codes are shown for inspection; it is not marked as valid.
- A 502 response means the configured provider chain could not produce a response.
- If the UI cannot load static files, reinstall the package so admin_static package data is included.

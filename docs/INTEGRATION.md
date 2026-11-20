# Integration and migration

## Do not copy the framework into product repositories

Install it as a versioned Python dependency or expose it behind a small internal HTTP service when the caller is not Python.

For Python products, pin a release or commit rather than tracking `main` implicitly.

## Existing project migration

Existing prompt and configuration systems do not need to be removed in one change.

### Step 1

Map the product's current profile and business configuration into `CommunicationRequest`.

Examples

Tutoring product

```python
request = tutoring_request(
    channel="profi",
    message_type="chat_reply",
    profile=current_profile.id,
    conversation=history,
    context={
        "client_name": order.client_name,
        "student_name": order.student_name,
        "profile_facts": current_profile.public_facts,
        "order": order.public_context,
    },
    business_rules=current_profile.communication_rules,
    voice=current_profile.voice,
)
```

Job-search product

```python
request = job_search_request(
    channel="hh",
    message_type="application",
    profile="backend",
    conversation=[],
    context={
        "vacancy": vacancy.summary,
        "candidate_facts": selected_resume.public_facts,
    },
)
```

### Step 2

Use `prepare()` with the existing LLM client.

This validates framework behavior without changing credentials, routing or model infrastructure.

### Step 3

Move generation into the framework with the preferred provider adapter.

For a local agent harness, prefer an explicit OpenCode model and ordered
fallbacks:

```python
provider = HarnessProvider.opencode_first(
    "openai/gpt-5.6-luna-fast",  # example: choose a model available in your OpenCode
)
framework = CommunicationFramework(provider)
```

The default harness uses OpenCode only. For parallel use of multiple API keys,
pass multiple environment-variable mappings through `credentials`. For several
models or providers, use `HarnessProvider.opencode_pool()`. Both pools rotate
the starting OpenCode process per request and isolate injected credential
databases per invocation.

### Step 4

After regression fixtures pass, delete duplicated local communication prompts, random style injection and overlapping validators from the product.

Browser automation, database state and delivery stay unchanged.

## Multiple profiles

Do not create separate framework forks for informatics, Chinese, Spanish, frontend or backend.

The product selects a profile and supplies its facts at runtime. Channel and message-type behavior stays shared.

## Non-Python products

Keep this repository as the source of truth and expose a small service wrapper around `prepare()` and `generate()` rather than reimplementing policies in Java, JavaScript or Go.

The repository also includes an optional local operator admin. Its preview and generation endpoints are intended for a human using the browser, not as a stable multi-tenant product API. A future product-facing HTTP contract should accept `CommunicationRequest` and return validated text or a typed generation error without exposing provider-specific details.

## Current Profi Worker bridge (implementation detail)

The long-term recommendation above is a pinned Python dependency. The
**current** `profi-worker/src/profi/humanizer_bridge.py` takes a different
transitional approach: it prepends `PROFI_HUMANIZER_DIR/src` to `sys.path`
and imports `humanizer_framework` from that separate checkout.
This keeps repository boundaries intact, but it is **not an automatic
dependency installed by `uv sync` in Profi Worker**.

On a machine running both projects, point the Profi account environment at
the **Humanizer checkout root**, not at the Profi repository:

```bash
export PROFI_HUMANIZER_DIR=/absolute/path/to/humanizer-framework
test -f "$PROFI_HUMANIZER_DIR/src/humanizer_framework/__init__.py"
# From the Profi Worker repository:
uv run python -c 'from profi.humanizer_bridge import _framework; print(_framework()[0].__name__)'
```

Run this import smoke test before enabling live outreach. A wrong path raises
`HumanizerError` on the Profi side; its fast-path marks the order `failed`
and does not send a placeholder message.

The example OpenCode model above matches the current fallback in
`providers/default_chain.py` but is **not a universally available model
identifier**. Override it to a model supported by the active OpenCode
account; the default chain can also use Z.AI or direct OpenAI API.

# Architecture

## Boundary

The calling product owns discovery, scraping, browser automation, persistence, ranking, account selection, profile facts and delivery.

Humanizer Framework owns the communication decision and outgoing wording.

```text
product
  context + selected profile + conversation + business constraints
      |
      v
humanizer framework
  planner
  policy registry
  prompt builder
  provider
  validators
      |
      v
outgoing message + plan + validation metadata
```

## Axes

### Domain

Describes the broad business conversation such as `tutoring` or `job_search`.

### Channel

Describes surface conventions such as `profi`, `repetitor`, `hh` or `telegram`.

### Message type

Describes the product-known interaction shape such as `outreach`, `application` or `chat_reply`.

### Conversation plan

Describes what the current turn should do. This is derived before generation.

### Profile

Identifies the product-owned identity or role configuration. The framework treats it as metadata and receives its actual facts through context.

### Voice

Controls wording habits only. It must not weaken business rules or invent facts.

## Runtime flow

### Prepare mode

`CommunicationFramework.prepare(request)`

1. Run deterministic planner
2. Resolve constraints
3. Compose domain, channel, message-type and action policies
4. Add bounded context and selected voice examples
5. Return `PromptPackage`

No model is required.

### Generate mode

`CommunicationFramework.generate(request)`

1. Run prepare flow
2. Call provider
3. Apply deterministic language normalization
4. Validate result
5. If issues exist, make at most one focused rewrite attempt
6. Keep the candidate only when its issue score improves
7. Return text, plan, validation issues, provider and prompt version

Strict mode may reject outputs that retain hard validation failures.

## Planner design

Version 0.1 is intentionally deterministic.

Known message types such as outreach, application and follow-up have explicit plans. Existing chat uses small heuristics to distinguish scheduling, objection, question, agreement and ordinary disclosure.

The planner API is isolated so an optional model-backed planner can later be added only for ambiguous cases.

## Policy registry

`PolicyRegistry` is composable and caller-extensible.

A product can add a new channel

```python
registry.register_channel(
    "custom_marketplace",
    "Short marketplace chat. Avoid formal letter structure.",
)
```

This avoids copying the framework into each product.

## Provider boundary

The provider protocol contains one operation

```python
generate(messages, temperature, max_tokens) -> str
```

This keeps the communication core independent of SDK churn.

LiteLLM is optional and provides broad cloud-provider coverage. CLI providers are convenience adapters for authenticated Codex and Claude Code environments.

## Context budget

The prompt builder deliberately does not send the entire repository configuration or long humanization guide to the LLM.

Only current policy fragments, the planner decision, bounded structured context, recent conversation and a few voice examples are included.

## Validation severity

Hard issues are suitable for strict rejection. Examples include character-budget overflow, forbidden punctuation when configured and an unplanned CTA.

Soft issues are quality signals such as template similarity or staged wording. They trigger one rewrite attempt but do not necessarily block output unless the product chooses stricter behavior.

## Evaluation roadmap

Unit tests cover deterministic behavior.

The next layer should add anonymized real-conversation fixtures with property-based expectations rather than exact-string goldens.

Examples

- tutoring disclosure must not introduce a trial CTA
- recruiter question must be answered before adding a next step
- first outreach should use a known client name once when supplied
- ongoing chat should not repeat the first-message value proposition
- no question should be asked for information already present in state

DeepEval can score multi-turn relevance and knowledge retention. Promptfoo can compare prompt and model variants in CI. Langfuse can later collect production traces into datasets and experiments.

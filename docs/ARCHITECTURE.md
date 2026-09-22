# Architecture

The detailed product contract is in docs/PRD.md.

## Boundary

The calling product owns discovery, scraping, browser automation, persistence, ranking, account selection, profile facts and delivery.

Humanizer Framework owns the communication decision and outgoing wording.

Runtime flow

product context
to planner
to policy registry
to prompt builder
to provider
to validators
to outgoing message plus plan and validation metadata

## Axes

### Domain

Describes the broad business conversation such as tutoring or job_search.

### Channel

Describes surface conventions such as profi, repetit, hh or telegram.

The legacy key repetitor remains a compatibility alias.

### Message type

Describes the product-known interaction shape such as outreach, application or chat_reply.

### Conversation plan

Describes what the current turn should do. This is derived before generation.

### Profile

Identifies the product-owned identity or role configuration. The framework treats it as metadata and receives its actual facts through context.

### Voice

Controls wording habits only. It must not weaken business rules or invent facts.

## Trust boundary

Only framework-authored policy messages may receive provider system priority.

Caller conversation roles are normalized to user or assistant.

Known context, marketplace text, vacancy text and voice examples are untrusted data even when they are embedded in a framework-authored prompt section.

Business rules are trusted caller configuration.

The framework must not receive unrelated platform credentials or secrets.

## Prepare mode

CommunicationFramework.prepare(request)

1. Run deterministic planner
2. Resolve constraints
3. Compose domain, channel, message-type, language and action policies
4. Add bounded context and selected voice examples
5. Normalize provider roles
6. Return PromptPackage

No model is required.

## Generate mode

CommunicationFramework.generate(request)

1. Run prepare flow
2. Call provider
3. Apply deterministic language normalization
4. Validate result
5. If issues exist, make at most one focused rewrite attempt
6. Keep the candidate only when its issue score improves
7. In strict mode reject remaining hard failures
8. Return text, plan, validation issues, provider and prompt version

## Planner design

Version 0.1 is intentionally deterministic.

Known message types such as outreach, application and follow-up have explicit plans.

Existing chat uses small language-aware heuristics to distinguish scheduling, objection, question, agreement and ordinary disclosure.

The planner API is isolated so an optional model-backed ambiguity planner can later be added without changing writer or validator contracts.

## Policy registry

PolicyRegistry is composable and caller-extensible.

A product can register a new domain, channel, message-type policy or language policy without copying the framework.

## Provider boundary

The provider protocol contains one operation that receives provider-ready messages and generation parameters and returns text.

This keeps the communication core independent of SDK churn.

LiteLLM is optional and provides broad cloud-provider coverage. CLI providers are convenience adapters for authenticated Codex and Claude Code environments.

Provider-specific generic options cannot replace framework-owned model call fields.

## Context budget

The prompt builder deliberately does not send the entire repository configuration or long humanization guide to the LLM.

Only current policy fragments, planner decision, bounded structured context, bounded recent conversation and a few selected voice examples are included.

Individual oversized history messages are clipped before total history accumulation.

## Voice selection

Voice examples are style data, not facts.

Version 0.1 uses deterministic lexical relevance to the latest user message and fills unused slots in stable order.

Future retrieval can use embeddings without changing the VoiceProfile contract.

## Validation severity

Hard issues are suitable for strict rejection.

Examples

- empty output
- character-budget overflow
- forbidden punctuation when configured
- unplanned question
- unplanned CTA
- missing required first-outreach name

Soft issues are quality signals such as template similarity or staged wording.

They trigger one rewrite attempt but do not necessarily block output unless the product chooses stricter behavior.

## Evaluation roadmap

Unit tests cover deterministic behavior.

Anonymized real-conversation fixtures should use property-based expectations rather than exact-string goldens.

Examples

- tutoring disclosure must not introduce a trial CTA
- recruiter question must be answered before adding a next step
- first outreach should use a known client name once when supplied
- ongoing chat should not repeat the first-message value proposition
- no question should be asked for information already present in state

DeepEval can score multi-turn relevance and knowledge retention.

Promptfoo can compare prompt and model variants in CI.

Langfuse can later collect production traces into datasets and experiments.

## Planned service boundary

Python consumers use the library directly.

Non-Python consumers should eventually use a small internal HTTP wrapper around the same request and result contracts.

The HTTP service must contain no separate communication policy implementation.

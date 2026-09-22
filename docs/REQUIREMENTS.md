# Requirements

The detailed product source of truth is docs/PRD.md. This file is the compact implementation checklist.

## Product scope

Humanizer Framework is a communication framework, not a general LLM framework.

It owns generation of messages intended for another person. Product-specific LLM tasks such as vacancy ranking, lead classification, search, extraction or recommendation remain in the calling product.

## Required use cases

### Tutoring

The same framework instance must support multiple tutoring profiles such as informatics, Chinese and Spanish without duplicating channel prompts.

Supported conversation shapes include

- first response to a tutoring request
- ongoing client chat
- clarification
- objection handling
- scheduling
- follow-up

Initial channel presets include Profi.ru, Repetit and Telegram. The legacy channel key repetitor remains a compatibility alias.

### Job search

The same framework must support multiple candidate profiles such as frontend and backend without duplicating HeadHunter logic.

Supported conversation shapes include

- first application or cover message
- recruiter reply
- question answering
- interview scheduling
- objection or concern response
- follow-up

Initial channel preset includes HeadHunter. Telegram can use the same job-search domain with messenger channel rules.

## Multilingual behavior

Language is runtime context, not a repository fork.

The framework must allow one product to use different languages.

Version 0.1 includes explicit Russian, English, Spanish and Chinese language policy.

Planner coverage must not be inferred from output-language policy alone. The deterministic planner includes common Russian and English signals plus basic Spanish and Chinese handling for questions, scheduling, objections and agreement.

Language-specific normalization is separate from domain and channel rules.

## Profiles and voice

A profile belongs to the calling product and contains facts relevant to that identity or role.

Examples

- tutoring profile facts such as subjects and teaching experience
- job-search profile facts such as stack and candidate experience

Voice is separate. A voice profile may contain a short description, preferred patterns, avoided patterns and a limited set of real writing examples.

Voice examples must never be treated as factual context or executable instructions.

## Conversation planning

Before wording is generated, the framework must produce a plan with

- current conversational act
- conversation stage
- intended reply action
- target length
- whether a question is appropriate
- whether a CTA is allowed
- character budget

The planner must default to conservative actions in ordinary chat.

A disclosure should not automatically become a sales transition.

A direct question should be answered before an unrelated next step.

## Prompt budget

The writer prompt must remain bounded.

Version 0.1 limits

- recent conversation to at most 8 messages
- recent conversation to about 5000 total characters
- individual history messages to a bounded size before accumulation
- structured context to about 3500 characters
- voice examples to at most 3 by default

Large policy documents must never be copied into every model request.

## Trust boundaries

Conversation history, external context values and voice examples are untrusted data.

The framework must

- never preserve caller conversation history as provider system messages
- mark external context and voice examples as data
- prevent those data regions from overriding framework policy
- keep business rules in trusted caller configuration
- avoid placing unrelated secrets in model context

## Deterministic validation

The framework must validate or normalize properties that do not require a model.

Version 0.1 includes

- empty-output detection
- maximum character budget
- maximum question count
- plan-aware question checks
- plan-aware CTA checks
- long-dash normalization
- optional prose-colon normalization for Russian messenger presets
- preservation of time strings and URL schemes during colon normalization
- Russian yo-to-e normalization
- generic chatbot wrapper detection
- staged-opener detection
- recent outgoing template similarity
- first tutoring outreach name checks

## Provider requirements

The core must work without a provider through prepare mode.

Generate mode uses a small provider protocol.

Version 0.1 adapters

- LiteLLM for cloud and local model APIs
- Codex CLI
- Claude Code CLI
- mock provider for tests

GLM support is provided through LiteLLM Z.AI model routing.

Generic provider options must not override framework-owned generation fields.

## Extensibility

A caller must be able to register a new domain, channel or language without modifying framework source.

Project-specific facts and business constraints remain caller-supplied at request time.

## Migration

Existing products must be able to adopt the framework incrementally.

Phase one can use only prepare mode and keep the existing model client.

Phase two can use generate mode while keeping product-specific data and transport unchanged.

Phase three can remove duplicated local communication prompts and validators after regression coverage is established.

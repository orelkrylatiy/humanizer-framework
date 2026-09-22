# Product Requirements Document

Document status: active
Product: Humanizer Framework
Version target: 0.1 foundation with 0.2 integration roadmap
Primary use cases: tutoring communication, job-search communication, messenger outreach
Initial channels: Profi.ru, Repetit, HeadHunter, Telegram
Initial implementation language: Python
Last updated: 2026-09-22

## 1. Executive summary

Humanizer Framework is a reusable communication layer for products that use large language models to communicate with people.

The product exists because communication quality cannot be solved by text rewriting alone.

A traditional humanizer starts with completed text and tries to remove common AI-writing patterns. That helps with phrasing, but it does not solve the more important failure modes found in automated marketplace and job-search conversations.

Examples of those failures include

- replying to a one-line client disclosure with a long sales paragraph
- proposing a trial lesson after every client message
- repeating the same value proposition in an ongoing chat
- asking a question simply because every template ends in a question
- asking for information already present in the conversation
- treating first outreach and an established chat as the same writing task
- repeating one polished message skeleton across hundreds of recipients
- copying facts from style examples
- allowing platform text to influence system-level behavior
- sending the entire conversation, voice corpus and project configuration to the model on every turn

Humanizer Framework addresses the whole communication decision.

The core flow is

product context
to conversation planner
to policy composition
to bounded prompt construction
to LLM provider
to deterministic validation
to outgoing message

The framework is shared across products.

It should support tutoring profiles such as informatics, Chinese and Spanish, and job-search profiles such as frontend and backend, without duplicating communication code for each profile.

The calling project owns its facts and business data. The framework owns how a human-facing message is planned, written and checked.

## 2. Product definition

Humanizer Framework is a communication framework.

It is not

- a browser automation framework
- a scraping framework
- a job ranking engine
- a tutoring recommendation engine
- a generic agent runtime
- a CRM
- a database
- a messaging transport
- a replacement for every LLM call in a product
- a guarantee that model output is indistinguishable from a human

Its responsibility begins when a product has enough context to produce or answer a human-facing message.

Its responsibility ends when it returns the generated message and communication metadata to the caller.

The caller then decides whether and how to send the message.

## 3. Why this must be a separate framework

The same communication problems appear across unrelated products.

A tutoring automation product and a job-search automation product both need to

- answer the current point first
- avoid repeating known information
- distinguish first contact from ongoing chat
- keep brief conversations brief
- use only supplied facts
- avoid generic chatbot language
- handle questions differently from disclosures
- avoid repeated CTAs
- adapt to channel conventions
- use a stable voice
- control prompt size
- validate mechanical rules
- test regressions

If every product contains its own version of these rules, they diverge.

A fix made in one repository does not improve the others.

Prompts become copied configuration rather than shared product logic.

The standalone framework creates one versioned source of truth.

A product upgrades the dependency when it is ready to adopt new behavior.

## 4. Target consumers

The first consumers are internal automation products.

### 4.1 Tutoring marketplace automation

Typical channels

- Profi.ru
- Repetit
- Telegram

Typical profiles

- informatics tutor
- programming tutor
- Chinese tutor
- Spanish tutor
- other tutoring subjects

Typical message situations

- first response to a request
- answer after the client replies
- qualification
- homework-help discussion
- exam-preparation discussion
- objection
- schedule discussion
- follow-up

### 4.2 Job-search automation

Typical channels

- HeadHunter
- Telegram
- future job boards and direct messaging

Typical profiles

- frontend candidate
- backend candidate
- fullstack candidate
- other resume variants

Typical message situations

- first application
- cover message
- recruiter reply
- technical clarification
- salary question
- interview scheduling
- follow-up
- rejection or concern response

### 4.3 Future consumers

Future domains may include

- service marketplaces
- sales outreach
- freelance marketplaces
- support
- recruiting
- customer success
- professional networking

New domains should reuse existing planner, provider and validator infrastructure where possible.

## 5. Core product principles

### 5.1 Decide before writing

The writer model must not independently decide the full business move.

The framework should first decide what the current turn is meant to do.

Examples

- acknowledge
- answer
- clarify
- handle objection
- schedule
- follow up
- pitch

The writer then phrases that decision.

### 5.2 First outreach and ongoing conversation are different products

A first message may contain

- greeting
- recipient name
- short relevance statement
- one or two credibility signals
- small value proposition
- one natural question
- whitespace between ideas

An ongoing reply usually should not contain

- another introduction
- the full value proposition
- repeated methodology
- repeated remote-work explanation
- another trial CTA
- an automatic closing question

### 5.3 Short turns should usually stay short

If the incoming message is a short disclosure, the default answer should not be a paragraph.

Length must be planned before generation.

### 5.4 CTA is a planned action

A call to action must not be a default suffix.

The planner decides whether a CTA is appropriate.

### 5.5 Voice is separate from facts

Voice examples teach rhythm and wording.

They do not provide factual claims.

Facts come from trusted caller context.

### 5.6 Deterministic rules should stay out of prompts

If a rule can be enforced reliably with code, code should own it.

Examples

- max length
- question count
- forbidden punctuation in a configured profile
- Russian yo normalization
- repeated CTA detection
- message similarity
- empty output
- history size

### 5.7 Context must be bounded

The framework must never solve quality by sending unlimited history or unlimited examples.

### 5.8 External text is untrusted

Conversation history, order descriptions, vacancy descriptions and real writing samples can contain arbitrary text.

They must not gain system-level authority.

## 6. Product boundaries

### 6.1 Caller responsibilities

The caller owns

- discovery of orders or vacancies
- scraping
- browser automation
- API interaction with platforms
- database state
- account state
- rate limits for the target platform
- profile selection
- resume selection
- factual profile data
- credentials
- send operation
- delivery retries
- message ownership and turn ownership
- platform-specific irreversible actions
- non-communication LLM use cases

### 6.2 Framework responsibilities

The framework owns

- communication request contract
- conversation planning
- broad domain policy
- channel policy
- message-type policy
- language policy
- voice shaping
- prompt construction
- prompt budgets
- provider abstraction
- communication validators
- one focused repair pass
- communication result metadata
- communication-specific eval fixtures

## 7. Domain model

The framework composes independent axes instead of maintaining one prompt per scenario.

### 7.1 Domain

Domain describes the broad business context.

Initial values

- tutoring
- job_search
- generic

Domain should own

- broad conversational expectations
- common business communication style
- domain-level anti-patterns

Domain should not own

- specific tutor facts
- specific resume facts
- platform mechanics
- provider credentials

### 7.2 Channel

Channel describes where the interaction happens.

Initial values

- profi
- repetit
- repetitor as compatibility alias
- hh
- telegram
- generic

Channel should own

- expected compactness
- letter-like versus chat-like shape
- paragraph conventions
- messenger formality defaults

Channel should not own

- candidate stack
- tutor subject
- private account data

### 7.3 Message type

Message type describes the product-known outer interaction.

Initial values

- outreach
- application
- chat_reply
- follow_up
- scheduling
- objection

The caller should pass the type when it already knows it.

For example the caller always knows that a newly generated HeadHunter cover message is an application.

### 7.4 Conversation act

Conversation act is the planner interpretation of the latest turn.

Initial values

- disclosure
- question
- objection
- agreement
- scheduling
- unknown

### 7.5 Reply action

Reply action describes what the outgoing turn should do.

Initial values

- pitch
- acknowledge
- answer
- clarify
- handle_objection
- schedule
- follow_up

### 7.6 Conversation stage

Initial values

- new
- discovery
- qualified
- ready
- scheduling
- closed

Version 0.1 uses a light stage model.

Future versions may accept explicit caller-owned conversation state rather than inferring all stages.

### 7.7 Profile

Profile identifies the caller-selected identity or configuration.

Examples

Tutoring

- informatics
- chinese
- spanish

Job search

- frontend
- backend
- fullstack

The framework treats the profile id as metadata.

The actual factual content should arrive in structured context.

### 7.8 Voice

Voice is reusable wording behavior.

A voice can contain

- description
- preferred words or habits
- avoided words or habits
- writing examples

Voice must not contain authoritative business facts.

## 8. Primary scenarios

### 8.1 Tutoring first outreach

Inputs

- tutoring domain
- marketplace channel
- outreach message type
- selected tutor profile
- order context
- known client name when available

Expected behavior

- greet naturally
- use known client name once
- mention concrete relevance to the request
- optionally mention one or two credibility points
- avoid a generic list of benefits
- allow a question
- allow a CTA but do not require it
- permit slightly more text than ordinary chat
- use paragraph spacing when the message becomes long enough

### 8.2 Tutoring ongoing disclosure

Example input

Client says that the main task is doing homework.

Expected planner behavior

- act disclosure
- stage discovery
- action acknowledge
- no required question
- no CTA
- very short target

Expected writer behavior

- react to homework need
- do not repeat tutor introduction
- do not pitch a trial lesson
- do not ask for scheduling

### 8.3 Tutoring question

Example input

Client asks whether programming is also covered.

Expected behavior

- answer directly
- no automatic trial CTA
- no unrelated question
- use profile facts only

### 8.4 Tutoring scheduling

Expected behavior

- focus on logistics
- ask one useful timing question if necessary
- do not reopen the sales pitch

### 8.5 HeadHunter application

Inputs

- job_search domain
- hh channel
- application type
- selected resume profile
- vacancy summary
- candidate facts

Expected behavior

- connect candidate facts to vacancy needs
- avoid invented achievements
- do not force a question
- allow more text than messenger chat
- do not repeat irrelevant stack details

### 8.6 Recruiter question

Expected behavior

- answer the exact question first
- use only supplied candidate facts
- do not repeat cover letter
- do not add an unrelated next step

### 8.7 Follow-up

Expected behavior

- concise
- low-pressure
- do not shame recipient
- do not repeat full original pitch
- make it easy to answer or ignore

## 9. Multilingual requirements

Language is a runtime parameter.

A new language must not require a repository fork.

### 9.1 Language policy

The prompt must explicitly state the output language.

Initial language policies

- Russian
- English
- Spanish
- Chinese

### 9.2 Language-specific planning

Language policy alone is not enough.

Question, scheduling, objection and agreement signals can differ by language.

Version 0.1 includes

- Russian and English common planner signals
- Spanish basic scheduling, objection and agreement signals
- Chinese fullwidth question punctuation
- common Chinese question endings
- Chinese basic scheduling, objection and agreement signals

### 9.3 Language-specific deterministic normalization

Normalization is profile-specific.

Current Russian messenger behavior can

- replace yo with e
- replace long dash with a short hyphen
- remove stylistic prose colons while preserving times and URL schemes

These rules must not automatically apply to every language or every document type.

### 9.4 Future language packs

Future language support should package

- planner signals
- language policy
- deterministic normalization
- anti-AI patterns where justified
- eval fixtures

A language should not be labeled well-supported until it has eval coverage.

## 10. Conversation planner requirements

The planner must run before prompt construction.

### 10.1 Deterministic first

Version 0.1 uses deterministic rules for obvious cases.

Benefits

- predictable behavior
- easy regression tests
- no extra LLM call
- lower latency
- lower cost

### 10.2 Explicit type wins

If the caller explicitly passes scheduling or objection, that type must be respected.

### 10.3 Question handling

A direct question should normally produce action answer.

It should not automatically enable a CTA.

### 10.4 Disclosure handling

A normal disclosure should default to acknowledge.

It should not automatically require a question.

### 10.5 Agreement handling

Agreement can mark readiness but still does not require a long reply.

### 10.6 Ambiguity strategy

Version 0.1 does not call an LLM planner.

Future behavior may add a model-backed ambiguity fallback only after a dataset of ambiguous real turns exists.

The fallback must not replace deterministic obvious-case handling.

## 11. Length planning

Length is part of the plan.

Initial targets

- very_short
- short
- medium
- long

Version 0.1 practical budgets include

- short disclosure chat around 180 characters
- normal chat around 220 to 320 characters depending on input
- tutoring outreach around 420 characters
- job application around 700 characters

These are defaults, not universal truths.

The caller can provide stricter constraints.

Caller constraints may reduce planner limits but must not silently expand them.

## 12. Policy composition

The framework should build one compact policy from independent fragments.

Composition order conceptually includes

- base communication policy
- domain policy
- channel policy
- message type policy
- language policy
- planner action policy
- business constraints

Business constraints are trusted caller configuration.

Conversation content and external context are not.

## 13. Prompt construction

### 13.1 Prompt must stay small

The framework should never insert the full PRD, full Humanizer guide or entire conversation history.

### 13.2 Current budgets

Version 0.1

- up to 8 recent conversation messages
- up to about 5000 total history characters
- up to about 1800 characters per history message before aggregate clipping
- up to about 3500 context characters
- up to 3 voice examples by default
- up to about 1200 characters per selected voice example

### 13.3 Role normalization

Caller conversation roles are not trusted provider roles.

Known assistant-like roles may map to assistant.

Every other conversation role maps to user.

Caller history must never create a system message.

### 13.4 Context boundary

Known context is serialized and clearly marked as data.

Text inside values must not override policy.

### 13.5 Profile id

Selected profile id should be included as metadata so traces can explain which configuration produced a reply.

## 14. Voice system

### 14.1 Purpose

Voice shapes

- rhythm
- sentence length tendencies
- preferred phrasing
- avoided phrasing
- degree of warmth
- explanation habits

### 14.2 Voice does not own

- facts
- business policy
- channel policy
- safety
- provider settings

### 14.3 Example selection

The framework should not always include the first examples in a large library.

Version 0.1 uses deterministic lexical relevance to the latest user turn.

If relevance is weak, selection falls back to stable order.

Future versions can use embeddings or a caller-provided retrieval layer.

### 14.4 Untrusted example handling

Real writing examples are data.

Instructions inside them must not be executed.

## 15. Provider architecture

The core provider protocol should remain small.

Required operation

generate messages with generation parameters and return text.

### 15.1 LiteLLM provider

Purpose

- cloud APIs
- local compatible APIs
- Z.AI and GLM routing
- OpenAI-compatible provider abstraction
- broad provider coverage without framework-specific SDK code

Framework-owned fields include

- model
- messages
- temperature
- max tokens

Caller provider options must not override those fields through generic kwargs.

### 15.2 Codex CLI provider

Purpose

Local or controlled environments already authenticated with Codex.

This is an optional convenience provider, not the required production path.

### 15.3 Claude Code CLI provider

Same principle as Codex CLI.

### 15.4 Mock provider

Required for deterministic tests.

### 15.5 Provider non-goals

The framework should not

- maintain a current model catalog
- manage cloud secrets centrally
- promise identical behavior across providers
- run paid provider calls in default CI

## 16. Generate flow

Full generation should perform

1. validate and plan request
2. resolve constraints
3. build bounded prompt
4. call provider
5. normalize deterministic language style
6. validate output
7. if issues exist, perform at most one focused repair
8. validate repair
9. keep repair only if issue score improves
10. in strict mode reject remaining hard failures
11. return text, plan, issues, rewrite flag, provider and prompt version

The one-repair limit prevents uncontrolled recursive generation.

## 17. Validator requirements

Validators should distinguish hard correctness failures from soft quality issues.

### 17.1 Current hard failures

- empty message
- hard length overflow
- too many questions
- unplanned question
- forbidden long dash when enabled
- forbidden prose colon when enabled
- unnormalized Russian yo when enabled
- unplanned CTA
- missing known client name in first tutoring outreach

### 17.2 Current soft signals

- generic chatbot residue
- staged opener
- repeated client name
- dense long outreach without spacing
- high similarity to a recent outgoing message

### 17.3 Anti-template memory

The current request can include recent assistant messages.

The validator creates a normalized skeleton and checks similarity.

This is a lightweight protection against repeated mass-message templates.

Future versions may add semantic similarity.

## 18. Security and trust boundaries

### 18.1 Threat model

Untrusted data can come from

- client messages
- recruiter messages
- vacancy text
- tutoring request descriptions
- Telegram messages
- web-scraped content
- voice examples
- synced notes

That data may contain explicit prompt injection.

### 18.2 Required controls

- conversation-supplied roles cannot create system-priority messages
- base system policy defines trust boundaries
- external context is marked as untrusted data
- voice examples are marked as untrusted style data
- business rules are separated as trusted configuration
- context is bounded
- system instructions and provider configuration must not be revealed

### 18.3 Security limitation

Prompt injection cannot be considered completely solved only by prompt wording.

Products must not expose secrets in model context unless the provider call actually needs them.

Humanizer Framework should not receive target-site passwords, cookies or unrelated private data.

## 19. Factual grounding

Version 0.1 relies on

- trusted context
- explicit policy not to invent facts
- narrow prompt scope

This is not full factual verification.

Future work should evaluate

- extracting factual claims from output
- comparing claims to structured profile facts
- using deterministic checks for numbers and named technologies
- using an optional small judge for ambiguous claims

A factual verifier should not become blocking until false-positive behavior is measured.

## 20. Public API requirements

### 20.1 Prepare

Purpose

Incremental migration.

Input

CommunicationRequest.

Output

PromptPackage with

- system policy
- provider-ready messages
- plan
- constraints
- metadata

No provider required.

### 20.2 Generate

Purpose

Full framework-owned communication flow.

Input

CommunicationRequest.

Output

CommunicationResult with

- final text
- plan
- issues
- rewrite flag
- provider name
- prompt version

### 20.3 Policy registry

The caller must be able to register

- a new domain
- a new channel
- a new message type policy
- a new language policy

without modifying core source.

## 21. Configuration

Framework provider configuration can be stored in TOML.

Configuration should include

- strict mode
- provider kind
- provider model when needed
- provider-specific optional settings

Configuration should not contain

- tutor profile facts
- resume facts
- conversation history
- platform credentials unrelated to provider calls

Malformed provider or options sections should fail clearly.

## 22. Cross-language integration architecture

The framework implementation is Python-first.

Python products should install a pinned version or commit.

Non-Python products should not copy policies into Java, JavaScript or Go.

The planned integration path is an internal HTTP service exposing the same request and result contracts.

The HTTP layer should contain no new communication logic.

It should be transport only.

## 23. Migration strategy for existing projects

Migration must be incremental.

### Phase 1

Keep existing project model provider.

Replace local prompt assembly with framework prepare mode.

Compare output and logs.

### Phase 2

Move generation to framework generate mode.

Keep product browser logic, database logic and delivery unchanged.

### Phase 3

Delete duplicated project-local communication prompts and validators once regression fixtures prove equivalent or better behavior.

### Phase 4

Add production observability and shared eval datasets.

This approach avoids rewriting whole products.

## 24. Profi Worker migration expectations

Profi Worker should remain responsible for

- scanning orders
- account selection
- profile selection
- browser actions
- turn ownership
- database state
- message sending

Humanizer Framework should replace

- CHAT_SYSTEM-like communication prompts
- duplicated human-style instructions
- random smile injection
- repeated next-step prompting
- communication-specific text validation

Initial migration should preserve existing hard business constraints such as what facts may be mentioned.

## 25. Career and HeadHunter migration expectations

The job-search product should remain responsible for

- vacancy discovery
- filtering
- resume selection
- fit scoring
- application state
- browser or API submission

The framework should own

- cover-message communication policy
- recruiter chat replies
- follow-up wording
- scheduling wording
- communication validation

Frontend and backend are profiles, not separate framework implementations.

## 26. Telegram migration expectations

Telegram is a channel, not a domain.

The same Telegram channel policy can be combined with

- job_search
- tutoring
- future recruiting
- other domains

This avoids creating a separate Telegram communication engine.

## 27. Evaluation strategy

### 27.1 Deterministic unit tests

Every deterministic rule should have a direct test.

### 27.2 Regression fixtures

Real failures should become anonymized fixtures.

Fixtures should specify properties rather than one exact ideal answer.

Example expectations

- action acknowledge
- allow_cta false
- ask_question false
- max chars under threshold
- client name required

### 27.3 Model-backed evaluation

Future suites should evaluate generated messages across model and prompt changes.

DeepEval can help measure

- turn relevancy
- knowledge retention
- role adherence
- conversation completeness

Promptfoo can help run

- provider comparisons
- prompt comparisons
- CI matrices
- cached evaluation

### 27.4 Production evaluation

Langfuse or an equivalent tracing layer can later support

- prompt version tracing
- provider comparison
- dataset creation
- production examples
- experiment tracking

## 28. Quality metrics

The project should eventually track

- hard validation failure rate
- repair rate
- repair success rate
- average output length by message type
- question rate by message type
- CTA rate by planner action
- template similarity rate
- repeated CTA rate
- factual error rate
- human review preference rate
- task success rate where the consumer can measure it
- token and latency cost

Metrics must be segmented by

- domain
- channel
- language
- profile
- message type
- provider
- prompt version

## 29. Functional requirements

FR-001

The framework shall accept a CommunicationRequest containing channel, domain, message type, language, profile, conversation, context, business rules, optional voice and optional constraints.

FR-002

The framework shall provide prepare mode that does not require a provider.

FR-003

The framework shall provide generate mode using a provider abstraction.

FR-004

The planner shall run before writer prompt generation.

FR-005

A normal disclosure in ongoing chat shall default to an acknowledge action without automatic CTA.

FR-006

A direct question shall default to answer before any next-step behavior.

FR-007

First outreach shall have a larger default length budget than ongoing short chat.

FR-008

Known client name shall be required in first tutoring outreach when supplied.

FR-009

Voice examples shall not be treated as factual context.

FR-010

Conversation history shall not be able to create system-priority provider messages.

FR-011

Prompt history shall be bounded by both message count and total size.

FR-012

Individual very large conversation turns shall be clipped.

FR-013

Context shall be bounded.

FR-014

The framework shall support caller registration of new domains, channels and languages.

FR-015

The framework shall support Russian, English, Spanish and Chinese language policy in the initial release.

FR-016

The planner shall recognize ASCII and Chinese fullwidth question punctuation.

FR-017

The initial planner shall include basic Spanish and Chinese common-state signals.

FR-018

The framework shall normalize configured Russian messenger punctuation rules deterministically.

FR-019

Time strings such as 18:30 shall survive colon normalization.

FR-020

URL schemes shall survive colon normalization.

FR-021

The validator shall detect empty output as a hard failure.

FR-022

The validator shall detect unplanned questions when the plan forbids a question.

FR-023

The validator shall detect unplanned CTA patterns when the plan forbids CTA.

FR-024

The validator shall detect repeated-message similarity against recent assistant output.

FR-025

The framework shall attempt at most one repair per generate call.

FR-026

A repair shall replace the first candidate only when validation issue score improves.

FR-027

Strict mode shall reject remaining hard validation failures.

FR-028

LiteLLM provider options shall not override framework-owned generation fields.

FR-029

Provider configuration shall fail clearly on malformed option types.

FR-030

The framework shall return plan and validation metadata with generated text.

## 30. Non-functional requirements

NFR-001 Predictability

Obvious planner cases should be deterministic.

NFR-002 Testability

Core behavior should run in CI without paid provider credentials.

NFR-003 Extensibility

Adding a new channel should not require copying the framework.

NFR-004 Dependency control

The base package should remain lightweight. Cloud SDK behavior should stay optional.

NFR-005 Prompt efficiency

Prompts should be bounded and should not include full project documentation.

NFR-006 Security

Untrusted external text must not receive system-level provider priority.

NFR-007 Backward migration

Existing projects must be able to adopt prepare mode without replacing their current provider.

NFR-008 Provider neutrality

Communication policy must not depend on one model vendor.

NFR-009 Language extensibility

Adding a language should be possible without changing domain architecture.

NFR-010 Observability

Results must carry enough metadata for callers to trace plan, validation, provider and prompt version.

## 31. Acceptance criteria for the current foundation

The 0.1 foundation is acceptable when

- package imports successfully on supported Python versions
- prepare works without provider
- generate works with the provider protocol
- deterministic planner fixtures pass
- Profi disclosure case does not allow CTA
- recruiter question case does not allow CTA
- known tutoring client name validation works
- Russian normalization preserves time strings
- history cannot inject system role
- large history is bounded
- Chinese question punctuation is recognized
- Spanish scheduling basic signal is recognized
- empty output is a hard failure
- LiteLLM reserved kwargs are rejected
- CI passes on Python 3.11, 3.12 and 3.13
- PRD, architecture, concept and integration docs agree on product boundaries

## 32. Release roadmap

### 0.1 Foundation

Included

- Python package
- planner
- policy registry
- prompt builder
- voice model
- bounded context
- validators
- repair pass
- LiteLLM
- Codex CLI
- Claude CLI
- deterministic tests
- basic eval fixtures
- tutoring and job-search domains
- Profi, Repetit, HeadHunter and Telegram presets
- Russian, English, Spanish and Chinese language policy

### 0.2 First real consumer

Primary goal

Integrate Profi Worker.

Work

- create adapter from current profile configuration
- create anonymized real conversation dataset
- compare current output with framework output
- improve planner ambiguity handling based on real failures
- add stronger repeated-skeleton checks
- add factual consistency experiments

### 0.3 Multi-consumer proof

Integrate

- HeadHunter or Career Ops
- Telegram workflow

Goal

Prove that shared rules improve multiple products without platform-specific regressions.

### 0.4 Service and observability

Potential work

- internal HTTP API
- Langfuse adapter
- prompt version registry
- provider smoke tests
- release benchmark report

### Later

Potential work only after evidence

- LLM ambiguity planner
- embedding-based example retrieval
- DSPy optimization
- semantic anti-template detection
- richer language packs
- automatic voice learning from approved samples

## 33. Risks

### Risk 1 Over-generalization

A universal framework can become vague if it ignores channel and domain differences.

Mitigation

Keep domain, channel, message type and voice as separate axes.

### Risk 2 Prompt bloat

Adding every quality rule to the system prompt will increase cost and reduce clarity.

Mitigation

Use code for deterministic rules and bounded policy fragments.

### Risk 3 False humanization

Random slang, emoji or mistakes can look more artificial than clean text.

Mitigation

Do not inject random human touches. Use voice and conversation context.

### Risk 4 Planner errors

A wrong action can produce a natural but strategically wrong answer.

Mitigation

Deterministic obvious cases, fixtures, action metadata and later ambiguity fallback.

### Risk 5 Fact invention

A good style model can still invent candidate or tutor claims.

Mitigation

Trusted context only, explicit grounding rules and future factual verification.

### Risk 6 Prompt injection

External text can contain model instructions.

Mitigation

Role normalization, explicit untrusted-data boundaries, bounded context and no secrets in prompt.

### Risk 7 Framework drift from consumers

Projects may keep local prompt overrides that conflict with core policy.

Mitigation

Document migration ownership and remove duplicated local communication rules after integration proves stable.

## 34. Decisions already made

Decision

The project remains a standalone framework.

Reason

Communication behavior is shared across multiple products.

Decision

The framework is Python-first.

Reason

Initial consumers are Python and implementation speed matters.

Decision

Non-Python consumers should eventually use an HTTP wrapper.

Reason

Policies should not be duplicated across languages.

Decision

Planner is deterministic first.

Reason

Lower cost, easier testing and clear ownership.

Decision

LiteLLM is optional.

Reason

Provider breadth without making the base package dependent on one cloud SDK.

Decision

Voice is separate from facts.

Reason

Style examples must not become factual authority.

Decision

First outreach and ongoing chat are separate message modes.

Reason

Their natural length, structure and goals differ materially.

Decision

A CTA is planned, not automatically appended.

Reason

Repeated conversion pressure is one of the main observed AI-like behaviors.

## 35. Open questions

The following should be answered with real consumer data rather than speculation.

- How often does the deterministic planner misclassify ambiguous ongoing turns?
- What similarity threshold best catches repeated message skeletons without penalizing normal short acknowledgements?
- Should factual consistency become a hard gate for selected domains?
- Which parts of profile context should be normalized into a typed schema?
- When should a model-backed planner be invoked?
- How many voice examples provide the best quality per token?
- Which provider and model combinations perform best for short Russian marketplace chat?
- Should first outreach name requirements vary by channel?
- Which language packs deserve blocking validators versus advisory signals?
- When is an HTTP service worth the operational overhead?

## 36. Product success definition

The framework is successful when products stop maintaining large duplicated communication prompts and still improve communication quality.

A successful integration should demonstrate

- fewer repeated sales transitions
- shorter and more proportional chat replies
- fewer questions for already known information
- fewer repeated templates
- stable profile-specific voice
- no loss of product facts
- controlled prompt cost
- deterministic regression coverage
- easier rollout of shared communication improvements

The ultimate goal is not to trick a detector.

The goal is for automated communication to behave like a competent person participating in the actual conversation instead of a language model executing the same marketing template every turn.

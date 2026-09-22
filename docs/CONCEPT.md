# Humanizer Framework concept

## What this project is

Humanizer Framework is a reusable communication engine for products that use LLMs to talk to people.

It is not a general agent framework and it is not only a post-processing humanizer.

The framework owns the part of a product that answers one question.

Given this channel, profile, conversation, business context and current situation, what should we say to the person now and how should we phrase it?

Typical consumers are tutoring marketplace automation, job-search automation, recruiter messaging, Telegram outreach and similar systems.

A product can still use other LLM calls for search, ranking, extraction, filtering or classification. Those calls remain outside this repository. Humanizer Framework is specifically the communication layer.

## Why it exists

The original Humanizer project solves a narrower problem. It rewrites completed text so it contains fewer common AI-writing patterns.

That is useful, but real automated conversations fail earlier than wording.

A model can choose the wrong conversational action even when every sentence sounds natural.

Examples

- a client sends one short fact and the bot replies with a full sales pitch
- a recruiter asks one direct question and the bot repeats the cover letter
- a tutor bot proposes a trial lesson after every client message
- a bot asks for information that was already supplied
- first outreach messages repeat the same skeleton across many recipients
- the model adds a question because the prompt always expects a next step
- a short messenger conversation receives essay-like replies

These are policy and state problems, not only style problems.

Humanizer Framework therefore separates decision from wording.

Flow

product data
to planner
to policy resolver
to bounded prompt builder
to provider
to validators
to outgoing message

## Why it is a standalone repository

Communication quality problems repeat across products.

Profi.ru, Repetit, HeadHunter and Telegram have different surface conventions, but they share many rules.

- do not repeat already known information
- answer the current question first
- do not force a CTA
- keep short turns short
- avoid generic chatbot language
- match voice without copying facts from examples
- detect repetitive outgoing templates
- keep prompts bounded
- validate mechanical style rules deterministically

Copying those rules into each product would create multiple diverging versions.

The framework is therefore versioned and consumed as a dependency.

A Python product can call it directly.

A non-Python product should eventually call the same framework through a small internal HTTP service instead of porting policies to another language.

## How products use it

A caller supplies runtime context with channel, domain, message type, selected profile, language, conversation history, public factual context, business rules and optional voice.

The framework can then be used in two modes.

### Prepare mode

prepare(request) runs planning and prompt construction without calling a model.

It exists so older projects can keep their current LLM client while adopting framework behavior.

### Generate mode

generate(request) runs the full flow through the configured provider and validators.

## What stays in the caller

The calling product owns

- scraping and browser automation
- job or order discovery
- vacancy ranking
- lead filtering
- databases
- account selection
- private credentials
- selected resume or tutor profile
- factual profile data
- platform delivery and retries
- product-specific business state

The framework owns

- conversational planning
- communication policy
- prompt construction
- bounded dialogue context
- voice shaping
- outgoing text generation
- communication-specific validation
- communication regression fixtures

## Domains, channels and profiles are separate

A domain describes the broad business conversation.

Examples are tutoring and job_search.

A channel describes the surface.

Examples are profi, repetit, hh and telegram.

A profile is caller-owned identity data.

Tutoring profiles can include informatics, Chinese and Spanish.

Job-search profiles can include frontend, backend and fullstack.

The framework does not need a separate fork or prompt set for each profile.

This allows combinations such as

tutoring + profi + informatics
tutoring + repetit + chinese
tutoring + telegram + spanish
job_search + hh + frontend
job_search + hh + backend
job_search + telegram + backend

## Message types and planner actions are separate

The product usually knows the outer message type.

Examples are outreach, application, chat_reply, follow_up, scheduling and objection.

Inside ongoing chat, the planner chooses a narrower action such as acknowledge, answer, handle objection, schedule or follow up.

This prevents the writer model from deciding that every turn needs to advance a sales funnel.

## Language model

Language is runtime context.

The framework is not Russian-only.

Language-specific behavior belongs in language policy and deterministic normalization, while domain and channel behavior stays reusable.

Current explicit language policies include Russian, English, Spanish and Chinese. More languages can be registered without forking the framework.

Planner heuristics are intentionally small. Version 0.1 covers common Russian and English signals plus basic Spanish and Chinese question, scheduling, objection and agreement signals. Products can also pass an explicit message type when they already know the situation.

## Provider model

Provider choice is replaceable.

Current adapters include

- LiteLLM for cloud and local model APIs
- Codex CLI
- Claude Code CLI
- mock provider for tests

GLM models are reached through LiteLLM Z.AI routing.

The framework does not hardcode a current model catalog.

## Security model

Conversation history, vacancy text, order descriptions and voice examples are untrusted data.

They must not be allowed to override framework policy.

The prompt builder therefore

- never preserves a conversation-supplied system role
- labels known context and voice examples as untrusted data
- instructs the model not to follow embedded instructions
- keeps business rules in a trusted policy section
- limits history and context size

This is a defense-in-depth boundary, not a claim that prompt injection is perfectly solved.

## Quality model

The framework uses two kinds of quality control.

Deterministic checks handle measurable properties such as

- length
- question count
- forbidden punctuation for selected profiles
- repeated CTA patterns
- known-name requirements
- empty output
- similarity to recent outgoing messages

Evaluation fixtures handle conversational properties such as

- a disclosure should not become a forced trial CTA
- a recruiter question should be answered directly
- first tutoring outreach should use a known client name
- a job application should not automatically ask a question

Future model-backed evaluation will add DeepEval and Promptfoo suites. Production tracing can later use Langfuse.

## The intended end state

Every product should be able to replace local communication prompt logic with one stable framework call.

Fixing a shared communication bug once should improve every product after it upgrades the framework version.

That is the primary reason this repository exists.

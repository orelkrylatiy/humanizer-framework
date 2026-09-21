# Research and design analysis

Research date 2026-09-22.

## Problem definition

The target problem is broader than text humanization. We need one communication layer that can be reused by products working on tutoring marketplaces, job boards, messengers and future channels. It must handle first outreach, applications, follow-ups and ongoing multi-turn conversations while preserving each product's profile facts and business constraints.

The failure mode seen in real marketplace conversations is often behavioral. A client sends one short fact and the model responds with reassurance, a methodology explanation, another sales pitch, a trial CTA and a scheduling question. Rewriting that paragraph can make it sound nicer, but the system still chose the wrong conversational action.

The framework therefore needs two layers before generation and two layers after it.

```text
understand turn -> choose action -> write -> validate
```

## Projects reviewed

### blader/humanizer

Repository
https://github.com/blader/humanizer

Strengths

- Compact taxonomy of structural AI-writing patterns
- Strong emphasis on preserving supported claims
- Voice matching from writing samples
- Useful anti-patterns such as staged openers, forced triads, inflated significance, sales language and chatbot residue

Limitations for this project

- It is primarily a rewrite skill for completed prose
- It does not own multi-turn conversation state
- It does not decide whether a CTA, clarification or acknowledgement is appropriate
- It does not provide a reusable runtime API for multiple products and providers

Decision

Keep the anti-AI concepts, but do not keep the original skill packaging as the product architecture.

### devswha/patina

Repository
https://github.com/devswha/patina

Strengths

- Separates Document Type, Persona and Register instead of collapsing all style into one prompt
- Treats persona as voice-only rather than business policy
- Includes deterministic analysis and verification around LLM transformations
- Learns reusable voice traits from samples
- Uses explicit prompt budgets and bounded conversation history on hosted flows
- Has regression and quality harnesses instead of relying only on subjective review

Most useful idea for this framework

Independent axes with clear ownership. We adapt this into domain, channel, message type, voice and conversation policy.

### AIScientists-Dev/academic-humanizer

Repository
https://github.com/AIScientists-Dev/academic-humanizer

Strengths

- Domain-specific humanization instead of a single universal rewrite style
- Calibrates against real accepted writing samples
- Protects claims, numbers and citations

Lesson

Humanization rules need domain context and must not flatten important domain conventions.

### Rasa CALM

Reference
https://rasa.com/calm

Strengths

- Separates language understanding from deterministic business logic
- Uses structured flows to decide what happens next
- Keeps the LLM from owning the entire business decision loop

Most useful idea for this framework

The writer should not independently decide the business action. A planner decides the intended reply action first.

### DeepEval

Repository
https://github.com/confident-ai/deepeval

References
https://deepeval.com/docs/metrics-turn-relevancy
https://deepeval.com/docs/metrics-knowledge-retention

Strengths

- Multi-turn metrics for Turn Relevancy, Knowledge Retention, Role Adherence and Conversation Completeness
- Custom conversational evaluation criteria
- Conversation simulation and regression testing

Decision

Do not make DeepEval a mandatory runtime dependency. Design fixtures and result metadata so DeepEval can be added as an optional quality suite.

### Promptfoo

Repository
https://github.com/promptfoo/promptfoo

Strengths

- Model and prompt comparison
- Declarative eval suites
- CI integration
- Multi-provider testing and caching

Decision

Use it later as an external model-backed matrix runner. Keep deterministic unit tests in Python so the core remains lightweight.

### Langfuse

Repository
https://github.com/langfuse/langfuse

Strengths

- Prompt versioning
- Tracing and production observability
- Datasets and experiments
- Code and model-based evaluators

Decision

Keep observability hooks outside the core API for now. Add optional integration after production consumers start using the framework.

### LiteLLM

Documentation
https://docs.litellm.ai/

Strengths

- Unified OpenAI-style interface for many model providers
- Python SDK and gateway mode
- Retry, routing and fallback capabilities
- Z.AI/GLM support in addition to OpenAI, Anthropic, Gemini, Ollama and other providers

Decision

Use LiteLLM as an optional provider adapter instead of reimplementing cloud APIs. Keep the provider protocol small so callers can also use their existing client or a CLI adapter.

### DSPy

Repository
https://github.com/stanfordnlp/dspy

Strengths

- Optimizes prompts and few-shot examples against explicit metrics
- Can start with relatively small evaluation datasets

Decision

Useful after a stable benchmark exists. It is not a foundation for version 0.1 because optimizing against weak or incomplete metrics would simply automate the wrong behavior.

## Selected architecture

The strongest combined approach is

1. Rasa-style separation of conversation decision and language generation
2. Patina-style independent policy axes and deterministic checks
3. Humanizer-style structural anti-AI guidance
4. LiteLLM as an optional multi-provider layer
5. DeepEval and Promptfoo as later model-backed regression tools
6. Langfuse as later production observability
7. DSPy only after quality metrics and datasets are mature

## Why not use LangChain as the core

LangChain provides broad model and agent integration, but this framework does not need a general agent runtime. Its core task is small and stable. A narrow provider protocol plus LiteLLM keeps dependencies and context smaller and makes the communication contract easier to test.

## Why not make every decision with an LLM

Many communication choices are cheap and predictable in code. If the system already knows it is producing a first outreach, it does not need an extra model call to classify that. If a short incoming message is a disclosure, the safe default is acknowledgement rather than a new sales block. Deterministic planning also makes regression tests meaningful.

LLM planning can be added later for ambiguous cases, but it should be a fallback rather than the only path.

## Initial quality principles

- First outreach and ongoing chat are different modes
- Short incoming turns normally receive short outgoing turns
- A disclosure does not automatically trigger a question
- A question is answered before any next step
- CTA is a planned action, not a default suffix
- Voice examples influence wording but never contribute facts
- Channel policies and domain policies are composable
- Repeated message skeletons are a quality problem even if each individual message is grammatically good
- Mechanical punctuation and length rules belong in validators rather than large prompts
- Generated facts must come from caller context

## Provider strategy

Cloud APIs use the optional LiteLLM adapter. Z.AI/GLM can be selected with model strings such as `zai/glm-*` supported by the installed LiteLLM version.

Local authenticated coding-agent environments can use the provided Codex and Claude Code CLI adapters. These are optional convenience adapters, not required for production communication. Codex non-interactive automation uses `codex exec`. Claude Code supports non-interactive print mode with `claude -p`.

The framework deliberately does not hardcode a list of current model names. Provider catalogs change more often than the communication API.

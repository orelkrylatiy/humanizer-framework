from __future__ import annotations

from dataclasses import dataclass, field, replace

from .models import CommunicationRequest, MessageType, Plan, StyleConstraints

_BASE = """Write the next message as a normal person in an ongoing conversation.
Respond to the current conversational need, not to a generic sales objective.
Do not repeat facts the other person already knows.
Do not add a next step unless the plan allows it.
Prefer plain language. Avoid staged openers, forced triads, inflated claims, generic reassurance and chatbot wrappers.
Keep every factual claim grounded in the supplied context.
"""

_DEFAULT_DOMAINS = {
    "tutoring": """This is tutoring communication. A first outreach may briefly show fit and teaching relevance. After the person replies, switch to ordinary messenger mode. Do not repeatedly sell a trial lesson or restate the tutor profile.""",
    "job_search": """This is job-search communication. Tailor applications to the role using only supplied candidate facts. In recruiter chat, answer the current question directly and avoid repeating the cover letter.""",
    "generic": "Keep the message appropriate to the current channel and conversation.",
}

_DEFAULT_CHANNELS = {
    "profi": "Marketplace chat. Keep the tone personal and compact. First outreach can use short paragraphs. Later replies should usually be one short paragraph.",
    "repetitor": "Tutoring marketplace chat. Keep the tone personal and compact. First outreach can use short paragraphs. Later replies should usually be one short paragraph.",
    "hh": "Job-board communication. Applications may be more complete than chat replies. Recruiter replies should stay concise and factual.",
    "telegram": "Messenger conversation. Match the other person's brevity and directness. Avoid formal letter scaffolding unless the user is formal.",
    "generic": "Use the conventions of a short digital conversation.",
}

_DEFAULT_MESSAGE_TYPES = {
    MessageType.OUTREACH: "First contact. Greet naturally. Use the person's name once when known. Give one or two concrete reasons for relevance. Use whitespace between distinct ideas. One natural question is allowed but not mandatory.",
    MessageType.APPLICATION: "First job application. Connect the candidate to the role using concrete supplied experience. Keep it readable and specific. Do not invent achievements or metrics.",
    MessageType.CHAT_REPLY: "The conversation has already started. Do not introduce yourself again. React to the latest point. A question is optional, never automatic.",
    MessageType.FOLLOW_UP: "Follow up lightly. Do not guilt the recipient or repeat the entire previous pitch.",
    MessageType.SCHEDULING: "Discuss timing and logistics only. Do not add a new sales pitch.",
    MessageType.OBJECTION: "Address the exact concern first. Do not bury the answer under reassurance or a CTA.",
}

_ACTION = {
    "pitch": "Make the first message relevant and easy to answer.",
    "acknowledge": "Acknowledge the new information. Keep it short. Do not force a question.",
    "answer": "Answer the question directly. Do not append an unrelated CTA.",
    "clarify": "Ask one useful clarification only if the missing detail blocks a good response.",
    "handle_objection": "Respond to the concern directly and proportionally.",
    "schedule": "Move the logistics forward with one concrete scheduling question when needed.",
    "follow_up": "Send a low-pressure reminder that does not repeat the full original message.",
}


@dataclass(slots=True)
class PolicyRegistry:
    """Small, composable policy registry.

    Product projects can register a new channel or domain without forking the
    framework. Project-specific business facts still belong in the caller.
    """

    base: str = _BASE
    domains: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_DOMAINS))
    channels: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_CHANNELS))
    message_types: dict[MessageType, str] = field(
        default_factory=lambda: dict(_DEFAULT_MESSAGE_TYPES)
    )

    def register_domain(self, name: str, policy: str) -> None:
        self.domains[name] = policy

    def register_channel(self, name: str, policy: str) -> None:
        self.channels[name] = policy

    def register_message_type(self, message_type: MessageType | str, policy: str) -> None:
        self.message_types[MessageType(message_type)] = policy


def default_constraints(request: CommunicationRequest, plan: Plan) -> StyleConstraints:
    constraints = request.constraints or StyleConstraints()
    constraints = replace(constraints, max_chars=plan.max_chars)
    if request.language.lower().startswith("ru") and request.channel in {
        "profi",
        "repetitor",
        "telegram",
    }:
        constraints = replace(
            constraints,
            forbid_em_dash=True,
            forbid_colon=True,
            replace_yo=True,
        )
    return constraints


def render_policy(
    request: CommunicationRequest,
    plan: Plan,
    registry: PolicyRegistry | None = None,
) -> str:
    registry = registry or PolicyRegistry()
    message_type = MessageType(request.message_type)
    parts = [
        registry.base.strip(),
        registry.domains.get(request.domain, registry.domains["generic"]),
        registry.channels.get(request.channel, registry.channels["generic"]),
        registry.message_types[message_type],
        _ACTION[plan.action.value],
        f"Target length is {plan.target_length.value}. Hard character budget is {plan.max_chars}.",
        f"Question allowed by plan is {'yes' if plan.ask_question else 'no'}.",
        f"CTA allowed by plan is {'yes' if plan.allow_cta else 'no'}.",
    ]
    if request.business_rules:
        parts.append("Business constraints\n" + "\n".join(f"- {rule}" for rule in request.business_rules))
    return "\n\n".join(parts)

from __future__ import annotations

import json

from .models import CommunicationRequest, Plan, PromptPackage, StyleConstraints
from .policies import PolicyRegistry, render_policy

_MAX_HISTORY_MESSAGES = 8
_MAX_HISTORY_CHARS = 5000
_MAX_CONTEXT_CHARS = 3500


def _provider_role(role: str) -> str:
    normalized = role.lower()
    if normalized in {"assistant", "seller", "agent", "bot"}:
        return "assistant"
    if normalized == "system":
        return "system"
    return "user"


def _trim_history(request: CommunicationRequest) -> list[dict[str, str]]:
    items = request.conversation[-_MAX_HISTORY_MESSAGES:]
    out = [{"role": _provider_role(m.role), "content": m.content} for m in items]
    total = 0
    kept: list[dict[str, str]] = []
    for item in reversed(out):
        size = len(item["content"])
        if kept and total + size > _MAX_HISTORY_CHARS:
            break
        kept.append(item)
        total += size
    return list(reversed(kept))


def _voice_block(request: CommunicationRequest, constraints: StyleConstraints) -> str:
    voice = request.voice
    if not voice:
        return ""
    parts = [f"Voice profile {voice.id}"]
    if voice.description:
        parts.append(voice.description)
    if voice.prefer:
        parts.append("Prefer patterns\n" + "\n".join(f"- {x}" for x in voice.prefer[:8]))
    if voice.avoid:
        parts.append("Avoid patterns\n" + "\n".join(f"- {x}" for x in voice.avoid[:8]))
    examples = voice.examples[: constraints.max_voice_examples]
    if examples:
        parts.append("Style examples only. Do not copy facts from them.\n" + "\n---\n".join(examples))
    return "\n\n".join(parts)


def build_prompt(
    request: CommunicationRequest,
    plan: Plan,
    constraints: StyleConstraints,
    registry: PolicyRegistry | None = None,
) -> PromptPackage:
    system = render_policy(request, plan, registry)
    voice = _voice_block(request, constraints)
    if voice:
        system += "\n\n" + voice

    context_json = json.dumps(request.context, ensure_ascii=False, default=str)
    if len(context_json) > _MAX_CONTEXT_CHARS:
        context_json = context_json[:_MAX_CONTEXT_CHARS] + "..."

    planner_json = json.dumps(
        {
            "act": plan.act.value,
            "stage": plan.stage.value,
            "action": plan.action.value,
            "target_length": plan.target_length.value,
            "ask_question": plan.ask_question,
            "allow_cta": plan.allow_cta,
            "max_chars": plan.max_chars,
        },
        ensure_ascii=False,
    )

    messages = [
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "system",
            "content": f"Planner decision\n{planner_json}\n\nKnown context\n{context_json}",
        },
        *_trim_history(request),
        {
            "role": "user",
            "content": "Write only the next outgoing message. No analysis, labels or alternatives.",
        },
    ]
    return PromptPackage(
        system=system,
        messages=messages,
        plan=plan,
        constraints=constraints,
        metadata={
            "channel": request.channel,
            "domain": request.domain,
            "profile": request.profile,
            "language": request.language,
            "message_type": str(request.message_type),
        },
    )

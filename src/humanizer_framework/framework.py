from __future__ import annotations

from .models import CommunicationRequest, CommunicationResult, PromptPackage, ValidationIssue
from .planner import plan
from .policies import PolicyRegistry, default_constraints
from .prompting import build_prompt
from .providers.base import Provider
from .validators import normalize_output, validate_output


class CommunicationFramework:
    def __init__(
        self,
        provider: Provider | None = None,
        *,
        strict: bool = False,
        policies: PolicyRegistry | None = None,
    ):
        self.provider = provider
        self.strict = strict
        self.policies = policies or PolicyRegistry()

    def prepare(self, request: CommunicationRequest) -> PromptPackage:
        current_plan = plan(request)
        constraints = default_constraints(request, current_plan)
        return build_prompt(request, current_plan, constraints, self.policies)

    def generate(self, request: CommunicationRequest) -> CommunicationResult:
        if self.provider is None:
            raise RuntimeError("generate() requires a provider. Use prepare() for prompt-only mode.")

        package = self.prepare(request)
        raw = self.provider.generate(package.messages, max_tokens=400)
        text = normalize_output(raw, package.constraints, request.language)
        issues = validate_output(text, request, package.plan, package.constraints)
        rewritten = False

        if issues:
            repair_messages = [
                *package.messages,
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": _repair_instruction(issues, package.plan.max_chars),
                },
            ]
            candidate = self.provider.generate(repair_messages, temperature=0.2, max_tokens=400)
            candidate = normalize_output(candidate, package.constraints, request.language)
            candidate_issues = validate_output(
                candidate, request, package.plan, package.constraints
            )
            if _issue_score(candidate_issues) < _issue_score(issues):
                text, issues, rewritten = candidate, candidate_issues, True

        if self.strict and any(issue.hard for issue in issues):
            details = ", ".join(issue.code for issue in issues if issue.hard)
            raise ValueError(f"Generated message failed hard validation: {details}")

        return CommunicationResult(
            text=text,
            plan=package.plan,
            issues=issues,
            rewritten=rewritten,
            provider=getattr(self.provider, "name", type(self.provider).__name__),
        )


def _issue_score(issues: list[ValidationIssue]) -> int:
    return sum(3 if issue.hard else 1 for issue in issues)


def _repair_instruction(issues: list[ValidationIssue], max_chars: int) -> str:
    codes = ", ".join(issue.code for issue in issues)
    return (
        "Rewrite only the outgoing message. Preserve its meaning and supplied facts. "
        f"Fix these validation problems {codes}. Keep it under {max_chars} characters. "
        "Do not explain the rewrite."
    )

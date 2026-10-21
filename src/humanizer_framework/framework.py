from __future__ import annotations

import time

from .errors import GenerationValidationError, ProviderExecutionError
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
        strict: bool = True,
        provider_attempts: int = 2,
        retry_delay_seconds: float = 0.5,
        policies: PolicyRegistry | None = None,
    ):
        self.provider = provider
        # Kept as an accepted argument for configuration compatibility. Hard
        # validation is always fail-closed; callers never receive unsafe text.
        self.strict = strict
        if provider_attempts < 1:
            raise ValueError("provider_attempts must be at least 1")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        self.provider_attempts = provider_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.policies = policies or PolicyRegistry()

    def prepare(self, request: CommunicationRequest) -> PromptPackage:
        current_plan = plan(request)
        constraints = default_constraints(request, current_plan)
        return build_prompt(request, current_plan, constraints, self.policies)

    def generate(self, request: CommunicationRequest) -> CommunicationResult:
        if self.provider is None:
            raise RuntimeError(
                "generate() requires a provider. Use prepare() for prompt-only mode."
            )

        package = self.prepare(request)
        raw = self._call_provider(package.messages, max_tokens=400)
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
            candidate = self._call_provider(
                repair_messages, temperature=0.2, max_tokens=400
            )
            candidate = normalize_output(candidate, package.constraints, request.language)
            candidate_issues = validate_output(
                candidate, request, package.plan, package.constraints
            )
            if _issue_score(candidate_issues) < _issue_score(issues):
                text, issues, rewritten = candidate, candidate_issues, True

        hard_issues = [issue for issue in issues if issue.hard]
        if hard_issues:
            raise GenerationValidationError(hard_issues, last_text=text)

        return CommunicationResult(
            text=text,
            plan=package.plan,
            issues=issues,
            rewritten=rewritten,
            provider=getattr(self.provider, "name", type(self.provider).__name__),
        )

    def _call_provider(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        if self.provider is None:  # pragma: no cover - guarded by generate()
            raise RuntimeError("provider is not configured")

        last_error: Exception | None = None
        for attempt in range(self.provider_attempts):
            try:
                return self.provider.generate(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.provider_attempts and self.retry_delay_seconds:
                    time.sleep(self.retry_delay_seconds)

        provider_name = getattr(self.provider, "name", type(self.provider).__name__)
        raise ProviderExecutionError(
            f"Provider {provider_name!r} failed after {self.provider_attempts} attempt(s): "
            f"{last_error}"
        ) from last_error


def _issue_score(issues: list[ValidationIssue]) -> int:
    return sum(3 if issue.hard else 1 for issue in issues)


def _repair_instruction(issues: list[ValidationIssue], max_chars: int) -> str:
    codes = ", ".join(issue.code for issue in issues)
    return (
        "Rewrite only the outgoing message. Preserve its meaning and supplied facts. "
        f"Fix these validation problems {codes}. Keep it under {max_chars} characters. "
        "Do not explain the rewrite."
    )

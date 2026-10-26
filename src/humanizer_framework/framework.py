from __future__ import annotations

import time

from .errors import GenerationValidationError, ProviderExecutionError
from .models import CommunicationRequest, CommunicationResult, PromptPackage, ValidationIssue
from .planner import plan
from .policies import PolicyRegistry, default_constraints
from .prompting import build_prompt
from .providers import default_provider
from .providers.base import Provider
from .validators import normalize_output, validate_output
from .telemetry import now_utc, write_generation_event


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
        # Zero-config default uses the framework's own provider fallback chain.
        self.provider = provider if provider is not None else default_provider()
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
        self._last_provider_attempts = 0

    def prepare(self, request: CommunicationRequest) -> PromptPackage:
        current_plan = plan(request)
        constraints = default_constraints(request, current_plan)
        return build_prompt(request, current_plan, constraints, self.policies)

    def generate(self, request: CommunicationRequest) -> CommunicationResult:
        started_at = now_utc()
        started_clock = time.perf_counter()
        calls = 0
        attempts = 0
        repair_attempted = False
        rewritten = False
        self._last_provider_attempts = 0
        if self.provider is None:
            raise RuntimeError(
                "generate() requires a provider. Use prepare() for prompt-only mode."
            )
        try:
            package = self.prepare(request)
            raw = self._call_provider(package.messages, max_tokens=400)
            calls += 1
            attempts += self._last_provider_attempts
            text = normalize_output(raw, package.constraints, request.language)
            issues = validate_output(text, request, package.plan, package.constraints)

            if issues:
                repair_attempted = True
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
                calls += 1
                attempts += self._last_provider_attempts
                candidate = normalize_output(candidate, package.constraints, request.language)
                candidate_issues = validate_output(
                    candidate, request, package.plan, package.constraints
                )
                if _issue_score(candidate_issues) < _issue_score(issues):
                    text, issues, rewritten = candidate, candidate_issues, True

            hard_issues = [issue for issue in issues if issue.hard]
            if hard_issues:
                raise GenerationValidationError(hard_issues, last_text=text)

            result = CommunicationResult(
                text=text,
                plan=package.plan,
                issues=issues,
                rewritten=rewritten,
                provider=getattr(self.provider, "name", type(self.provider).__name__),
            )
            write_generation_event(
                request,
                started_at=started_at,
                status="success",
                provider=self.provider,
                elapsed_ms=round((time.perf_counter() - started_clock) * 1000),
                calls=calls,
                attempts=attempts,
                repair_attempted=repair_attempted,
                rewritten=rewritten,
                issues=issues,
            )
            return result
        except Exception as exc:
            write_generation_event(
                request,
                started_at=started_at,
                status="error",
                provider=self.provider,
                elapsed_ms=round((time.perf_counter() - started_clock) * 1000),
                calls=calls,
                attempts=attempts + self._last_provider_attempts,
                repair_attempted=repair_attempted,
                error=exc,
            )
            raise

    def _call_provider(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 300,
    ) -> str:
        if self.provider is None:  # pragma: no cover - guarded by generate()
            raise RuntimeError("provider is not configured")

        self._last_provider_attempts = 0
        last_error: Exception | None = None
        for attempt in range(self.provider_attempts):
            self._last_provider_attempts += 1
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

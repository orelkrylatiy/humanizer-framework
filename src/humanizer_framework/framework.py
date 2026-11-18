from __future__ import annotations

import threading
import time

from .errors import GenerationValidationError, ProviderExecutionError
from .models import CommunicationRequest, CommunicationResult, PromptPackage, ValidationIssue
from .planner import plan
from .policies import PolicyRegistry, default_constraints
from .prompting import build_prompt
from .providers import default_provider
from .providers.base import Provider
from .telemetry import now_utc, provider_snapshot, write_generation_event
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
        self.provider = provider if provider is not None else default_provider()
        # Строгая проверка обязательна даже для strict=False.
        self.strict = strict
        if provider_attempts < 1:
            raise ValueError("provider_attempts must be at least 1")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        self.provider_attempts = provider_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.policies = policies or PolicyRegistry()
        # Попытки одного запроса не должны смешиваться с параллельными вызовами.
        self._call_state = threading.local()

    @property
    def _last_provider_attempts(self) -> int:
        return getattr(self._call_state, "attempts", 0)

    @_last_provider_attempts.setter
    def _last_provider_attempts(self, value: int) -> None:
        self._call_state.attempts = value

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
            calls += 1
            try:
                raw = self._call_provider(package.messages, max_tokens=400)
            finally:
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
                calls += 1
                candidate_raw: str | None = None
                try:
                    candidate_raw = self._call_provider(
                        repair_messages, temperature=0.2, max_tokens=400
                    )
                except ProviderExecutionError:
                    # Если первый вариант допустим, сбой необязательной правки
                    # не должен терять уже полученный ответ.
                    if any(issue.hard for issue in issues):
                        raise GenerationValidationError(
                            [issue for issue in issues if issue.hard], last_text=text
                        ) from None
                finally:
                    attempts += self._last_provider_attempts

                if candidate_raw is not None:
                    candidate = normalize_output(
                        candidate_raw, package.constraints, request.language
                    )
                    candidate_issues = validate_output(
                        candidate, request, package.plan, package.constraints
                    )
                    # Сначала сравниваем критические нарушения, затем мягкие.
                    # Никакая сумма мягких замечаний не перевесит один hard.
                    if _issue_score(candidate_issues) < _issue_score(issues):
                        text, issues, rewritten = candidate, candidate_issues, True

            hard_issues = [issue for issue in issues if issue.hard]
            if hard_issues:
                raise GenerationValidationError(hard_issues, last_text=text)

            snapshot = provider_snapshot(self.provider)
            result = CommunicationResult(
                text=text,
                plan=package.plan,
                issues=issues,
                rewritten=rewritten,
                provider=snapshot["provider"],
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
                attempts=attempts,
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
        if self.provider is None:  # pragma: no cover
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
        error_type = type(last_error).__name__ if last_error else "UnknownError"
        # Не включаем str(last_error): там встречаются заголовки HTTP и ключи.
        raise ProviderExecutionError(
            f"Провайдер {provider_name!r} не ответил после "
            f"{self.provider_attempts} попыток ({error_type})."
        ) from last_error


def _issue_score(issues: list[ValidationIssue]) -> tuple[int, int]:
    return (
        sum(1 for issue in issues if issue.hard),
        sum(1 for issue in issues if not issue.hard),
    )


def _repair_instruction(issues: list[ValidationIssue], max_chars: int) -> str:
    codes = ", ".join(issue.code for issue in issues)
    return (
        "Перепиши только исходящее сообщение. Сохрани смысл и подтвержденные факты. "
        f"Устрани замечания {codes}. Уложись в {max_chars} символов. "
        "Не добавляй никаких пояснений к исправленному тексту."
    )

from __future__ import annotations

from collections.abc import Sequence

from .models import ValidationIssue


class GenerationError(RuntimeError):
    """Base error for provider and output-generation failures."""


class ProviderExecutionError(GenerationError):
    """A configured provider could not produce a usable response."""


class GenerationValidationError(GenerationError):
    """Generation and repair completed without a safe outgoing message."""

    def __init__(self, issues: Sequence[ValidationIssue], *, last_text: str = "") -> None:
        self.issues = tuple(issues)
        self.last_text = last_text
        details = ", ".join(issue.code for issue in self.issues) or "unknown"
        super().__init__(f"Generated message failed hard validation: {details}")

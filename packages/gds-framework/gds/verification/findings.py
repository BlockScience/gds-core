"""Verification finding and report models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Severity level of a verification finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    """A single verification check result — pass or fail with context."""

    check_id: str
    severity: Severity
    message: str
    source_elements: list[str] = Field(default_factory=list)
    passed: bool
    exportable_predicate: str = ""


class VerificationReport(BaseModel):
    """Aggregated verification results for a system."""

    system_name: str
    findings: list[Finding] = Field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(
            1 for f in self.findings if not f.passed and f.severity == Severity.ERROR
        )

    @property
    def warnings(self) -> int:
        return sum(
            1 for f in self.findings if not f.passed and f.severity == Severity.WARNING
        )

    @property
    def info_count(self) -> int:
        return sum(
            1 for f in self.findings if not f.passed and f.severity == Severity.INFO
        )

    @property
    def checks_passed(self) -> int:
        return sum(1 for f in self.findings if f.passed)

    @property
    def checks_total(self) -> int:
        return len(self.findings)

"""Software architecture DSL exceptions."""

from gds.blocks.errors import GDSError


class SWError(GDSError):
    """Base exception for software architecture DSL errors."""


class SWValidationError(SWError):
    """Raised when a software architecture model fails structural validation."""


class SWCompilationError(SWError):
    """Raised when compilation of a software architecture model fails."""

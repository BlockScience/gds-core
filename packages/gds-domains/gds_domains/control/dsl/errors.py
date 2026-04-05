"""Control system DSL exceptions."""

from gds.blocks.errors import GDSError


class CSError(GDSError):
    """Base exception for control system DSL errors."""


class CSValidationError(CSError):
    """Raised when a ControlModel fails structural validation."""


class CSCompilationError(CSError):
    """Raised when compilation of a ControlModel fails."""

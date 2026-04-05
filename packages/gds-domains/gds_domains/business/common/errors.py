"""Business dynamics DSL exceptions."""

from gds.blocks.errors import GDSError


class BizError(GDSError):
    """Base exception for business dynamics DSL errors."""


class BizValidationError(BizError):
    """Raised when a business dynamics model fails structural validation."""


class BizCompilationError(BizError):
    """Raised when compilation of a business dynamics model fails."""

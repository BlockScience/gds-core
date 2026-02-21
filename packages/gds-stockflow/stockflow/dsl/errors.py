"""Stock-flow DSL exceptions."""

from gds.blocks.errors import GDSError


class SFError(GDSError):
    """Base exception for stock-flow DSL errors."""


class SFValidationError(SFError):
    """Raised when a StockFlowModel fails structural validation."""


class SFCompilationError(SFError):
    """Raised when compilation of a StockFlowModel fails."""

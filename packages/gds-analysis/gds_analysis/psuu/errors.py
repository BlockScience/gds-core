"""Exception hierarchy for gds-psuu."""


class PsuuError(Exception):
    """Base exception for all gds-psuu errors."""


class PsuuValidationError(PsuuError, ValueError):
    """Raised when parameter space or configuration is invalid."""


class PsuuSearchError(PsuuError, RuntimeError):
    """Raised when the search/optimization process fails."""

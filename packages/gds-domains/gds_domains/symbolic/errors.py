"""Errors for gds-symbolic."""

from gds_domains.control.dsl.errors import CSError


class SymbolicError(CSError):
    """Raised when symbolic model construction or compilation fails."""

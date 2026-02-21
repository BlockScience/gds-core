"""GDS-specific error types.

Raised at construction time during Pydantic validation when a block
or composition violates structural constraints.
"""


class GDSError(Exception):
    """Base class for all GDS errors."""


class GDSTypeError(GDSError):
    """Port type mismatch or invalid port structure during construction."""


class GDSCompositionError(GDSError):
    """Invalid composition structure."""

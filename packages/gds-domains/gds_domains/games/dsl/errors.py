"""DSL-specific error types.

These wrap the GDS base errors with game-theory-specific names.
"""

from gds.blocks.errors import GDSCompositionError, GDSError, GDSTypeError


class DSLError(GDSError):
    """Base class for all DSL errors."""


class DSLTypeError(GDSTypeError):
    """Port type mismatch or invalid port structure during construction."""


class DSLCompositionError(GDSCompositionError):
    """Invalid composition structure."""

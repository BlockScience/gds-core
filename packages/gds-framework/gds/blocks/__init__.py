"""Block primitives, composition operators, and GDS roles."""

from gds.blocks.base import AtomicBlock, Block
from gds.blocks.composition import (
    FeedbackLoop,
    ParallelComposition,
    StackComposition,
    TemporalLoop,
    Wiring,
)
from gds.blocks.errors import GDSCompositionError, GDSError, GDSTypeError
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy

__all__ = [
    "AtomicBlock",
    "Block",
    "BoundaryAction",
    "ControlAction",
    "FeedbackLoop",
    "GDSCompositionError",
    "GDSError",
    "GDSTypeError",
    "Mechanism",
    "ParallelComposition",
    "Policy",
    "StackComposition",
    "TemporalLoop",
    "Wiring",
]

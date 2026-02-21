"""Abstract base class for Blocks in the GDS framework.

A Block is the fundamental composable unit. It has a name and an Interface
(directional port pairs). Composition operators build composite blocks
from simpler ones, forming a tree that the compiler flattens into a list
of atomic blocks + wiring.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from gds.tagged import Tagged
from gds.types.interface import Interface

if TYPE_CHECKING:
    from gds.blocks.composition import (
        FeedbackLoop,
        ParallelComposition,
        StackComposition,
        TemporalLoop,
        Wiring,
    )


class Block(Tagged, ABC):
    """Abstract base for all Blocks — both atomic and composite.

    Every block has a ``name`` and an ``interface`` describing its boundary
    ports. Composition operators (``>>``, ``|``, ``.feedback()``, ``.loop()``)
    build composite blocks from simpler ones.
    """

    name: str
    interface: Interface = Interface()

    @abstractmethod
    def flatten(self) -> list[AtomicBlock]:
        """Return all atomic blocks in evaluation order."""

    def __rshift__(self, other: Block) -> StackComposition:
        """``a >> b`` — stack (sequential) composition."""
        from gds.blocks.composition import StackComposition

        return StackComposition(
            name=f"{self.name} >> {other.name}",
            first=self,
            second=other,
        )

    def __or__(self, other: Block) -> ParallelComposition:
        """``a | b`` — parallel composition."""
        from gds.blocks.composition import ParallelComposition

        return ParallelComposition(
            name=f"{self.name} | {other.name}",
            left=self,
            right=other,
        )

    def feedback(self, wiring: list[Wiring]) -> FeedbackLoop:
        """Wrap with backward feedback within a single timestep."""
        from gds.blocks.composition import FeedbackLoop

        return FeedbackLoop(
            name=f"{self.name} [feedback]",
            inner=self,
            feedback_wiring=wiring,
        )

    def loop(self, wiring: list[Wiring], exit_condition: str = "") -> TemporalLoop:
        """Wrap with forward temporal iteration across timesteps."""
        from gds.blocks.composition import TemporalLoop

        return TemporalLoop(
            name=f"{self.name} [loop]",
            inner=self,
            temporal_wiring=wiring,
            exit_condition=exit_condition,
        )


class AtomicBlock(Block):
    """Base class for non-decomposable (leaf) blocks.

    Domain packages subclass this to define their own atomic block types.
    """

    def flatten(self) -> list[AtomicBlock]:
        return [self]

"""Abstract base class for open games in the DSL.

OpenGame subclasses the generic GDS Block, adding the (X, Y, R, S)
convention from compositional game theory. Users compose games with
Python operators::

    pipeline = context_builder >> history >> policy >> reactive_decision
    agent = pipeline.feedback([...])
    negotiation = (agent1 | agent2).corecursive([...])
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from gds.blocks.base import Block
from pydantic import model_validator

from ogs.dsl.types import Signature

if TYPE_CHECKING:
    from ogs.dsl.composition import (
        CorecursiveLoop,
        FeedbackLoop,
        Flow,
        ParallelComposition,
        SequentialComposition,
    )
    from ogs.dsl.games import AtomicGame


class OpenGame(Block):
    """Abstract base for all open games — both atomic components and composites.

    Every open game has a ``name`` and a ``signature`` describing its boundary
    ports using the (X, Y, R, S) convention. The ``signature`` keyword is
    accepted at construction and stored in the GDS ``interface`` field.
    """

    @model_validator(mode="before")
    @classmethod
    def _accept_signature_kwarg(cls, data: dict) -> dict:
        """Accept 'signature' as an alias for 'interface'."""
        if isinstance(data, dict) and "signature" in data:
            data["interface"] = data.pop("signature")
        return data

    @property
    def signature(self) -> Signature:
        """Game-theory alias for self.interface with x/y/r/s accessors."""
        iface = self.interface
        if isinstance(iface, Signature):
            return iface
        return Signature(
            forward_in=iface.forward_in,
            forward_out=iface.forward_out,
            backward_in=iface.backward_in,
            backward_out=iface.backward_out,
        )

    @abstractmethod
    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        """Return all atomic games in evaluation order."""

    def __rshift__(self, other: OpenGame) -> SequentialComposition:  # type: ignore[override]
        """``g1 >> g2`` — sequential composition."""
        from ogs.dsl.composition import SequentialComposition

        return SequentialComposition(
            name=f"{self.name} >> {other.name}",
            first=self,
            second=other,
        )

    def __or__(self, other: OpenGame) -> ParallelComposition:  # type: ignore[override]
        """``g1 | g2`` — parallel composition."""
        from ogs.dsl.composition import ParallelComposition

        return ParallelComposition(
            name=f"{self.name} | {other.name}",
            left=self,
            right=other,
        )

    def feedback(self, wiring: list[Flow]) -> FeedbackLoop:  # type: ignore[override]
        """Wrap with contravariant S→R feedback within a single timestep."""
        from ogs.dsl.composition import FeedbackLoop

        return FeedbackLoop(
            name=f"{self.name} [feedback]",
            inner=self,
            feedback_wiring=wiring,
        )

    def corecursive(
        self, wiring: list[Flow], exit_condition: str = ""
    ) -> CorecursiveLoop:
        """Wrap with covariant Y→X temporal iteration across timesteps."""
        from ogs.dsl.composition import CorecursiveLoop

        return CorecursiveLoop(
            name=f"{self.name} [corecursive]",
            inner=self,
            corecursive_wiring=wiring,
            exit_condition=exit_condition,
        )

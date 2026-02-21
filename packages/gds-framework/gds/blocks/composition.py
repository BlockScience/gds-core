"""Composition operators: stack, parallel, feedback, and temporal loop.

These operators combine blocks into larger composite systems:

- **Stack** (``>>``) — chains blocks so one's output feeds another's input.
- **Parallel** (``|``) — runs blocks side-by-side with no shared wires.
- **Feedback** — connects backward_out to backward_in within a single timestep.
- **Temporal Loop** — connects forward_out to forward_in across timesteps.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

from gds.blocks.base import AtomicBlock, Block
from gds.blocks.errors import GDSTypeError
from gds.ir.models import FlowDirection
from gds.types.interface import Interface, Port


class Wiring(BaseModel, frozen=True):
    """An explicit connection between two blocks.

    Covariant wirings (the default) carry data forward; contravariant
    wirings carry feedback backward.
    """

    source_block: str
    source_port: str
    target_block: str
    target_port: str
    direction: FlowDirection = FlowDirection.COVARIANT


class StackComposition(Block):
    """``a >> b`` — stack (sequential) composition.

    Output of the first block feeds input of the second. If no explicit
    ``wiring`` is provided, the validator checks that forward_out tokens
    overlap with forward_in tokens.
    """

    first: Block
    second: Block
    wiring: list[Wiring] = Field(default_factory=list)

    @model_validator(mode="after")
    def _compute_interface_and_validate(self) -> Self:
        if not self.wiring:
            first_out_tokens = _collect_tokens(self.first.interface.forward_out)
            second_in_tokens = _collect_tokens(self.second.interface.forward_in)

            if (
                first_out_tokens
                and second_in_tokens
                and not (first_out_tokens & second_in_tokens)
            ):
                raise GDSTypeError(
                    f"Stack composition {self.name!r}: "
                    f"first.forward_out tokens {first_out_tokens} have no overlap with "
                    f"second.forward_in tokens {second_in_tokens}"
                )

        self.interface = Interface(
            forward_in=self.first.interface.forward_in
            + self.second.interface.forward_in,
            forward_out=self.first.interface.forward_out
            + self.second.interface.forward_out,
            backward_in=self.first.interface.backward_in
            + self.second.interface.backward_in,
            backward_out=self.first.interface.backward_out
            + self.second.interface.backward_out,
        )
        return self

    def flatten(self) -> list[AtomicBlock]:
        return self.first.flatten() + self.second.flatten()


class ParallelComposition(Block):
    """``a | b`` — parallel composition: blocks run independently."""

    left: Block
    right: Block

    @model_validator(mode="after")
    def _compute_interface(self) -> Self:
        self.interface = Interface(
            forward_in=self.left.interface.forward_in + self.right.interface.forward_in,
            forward_out=self.left.interface.forward_out
            + self.right.interface.forward_out,
            backward_in=self.left.interface.backward_in
            + self.right.interface.backward_in,
            backward_out=self.left.interface.backward_out
            + self.right.interface.backward_out,
        )
        return self

    def flatten(self) -> list[AtomicBlock]:
        return self.left.flatten() + self.right.flatten()


class FeedbackLoop(Block):
    """Backward feedback within a single timestep (backward_out -> backward_in)."""

    inner: Block
    feedback_wiring: list[Wiring]

    @model_validator(mode="after")
    def _validate_and_compute_interface(self) -> Self:
        self.interface = self.inner.interface
        return self

    def flatten(self) -> list[AtomicBlock]:
        return self.inner.flatten()


class TemporalLoop(Block):
    """Forward temporal iteration across timesteps (forward_out -> forward_in).

    All temporal wiring must be covariant direction.
    """

    inner: Block
    temporal_wiring: list[Wiring]
    exit_condition: str = ""

    @model_validator(mode="after")
    def _validate_and_compute_interface(self) -> Self:
        for w in self.temporal_wiring:
            if w.direction != FlowDirection.COVARIANT:
                raise GDSTypeError(
                    f"TemporalLoop {self.name!r}: temporal wiring "
                    f"{w.source_block}.{w.source_port} → "
                    f"{w.target_block}.{w.target_port} "
                    f"must be COVARIANT (got {w.direction.value})"
                )

        self.interface = self.inner.interface
        return self

    def flatten(self) -> list[AtomicBlock]:
        return self.inner.flatten()


def _collect_tokens(ports: tuple[Port, ...]) -> frozenset[str]:
    """Collect all type tokens from a tuple of ports."""
    tokens: set[str] = set()
    for p in ports:
        tokens.update(p.type_tokens)
    return frozenset(tokens)

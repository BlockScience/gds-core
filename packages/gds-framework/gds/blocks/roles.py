"""GDS block roles from the MSML decomposition.

These roles decompose the transition function h into typed components:

- **BoundaryAction** — exogenous input (GDS admissible inputs U)
- **ControlAction** — endogenous control (reads state, emits signals)
- **Policy** — decision logic (maps signals to mechanism inputs)
- **Mechanism** — state update (the only component that writes state)

Each role subclasses AtomicBlock, inheriting composition operators and
flatten(). Role-specific validators enforce structural constraints.

Protocols
---------
``HasParams``, ``HasConstraints``, and ``HasOptions`` describe the structural
attributes shared by multiple role types without requiring a common base class.
Use ``isinstance(block, HasParams)`` for safe narrowing instead of
``cast(Any, block)`` or ``hasattr`` guards.
"""

from __future__ import annotations

from typing import Protocol, Self, runtime_checkable

from pydantic import Field, model_validator

from gds.blocks.base import AtomicBlock
from gds.blocks.errors import GDSCompositionError


@runtime_checkable
class HasParams(Protocol):
    """Structural protocol for blocks that declare parameter dependencies."""

    params_used: list[str]


@runtime_checkable
class HasConstraints(Protocol):
    """Structural protocol for blocks that carry constraint annotations."""

    constraints: list[str]


@runtime_checkable
class HasOptions(Protocol):
    """Structural protocol for blocks that enumerate named strategy options."""

    options: list[str]


class BoundaryAction(AtomicBlock):
    """Exogenous input — enters the system from outside.

    In GDS terms: part of the admissible input set U.
    Boundary actions model external agents, oracles, user inputs,
    environmental signals — anything the system doesn't control.

    Enforces ``forward_in = ()`` since boundary actions receive no
    internal forward signals.
    """

    kind: str = "boundary"
    options: list[str] = Field(default_factory=list)
    params_used: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_no_forward_in(self) -> Self:
        if self.interface.forward_in:
            raise GDSCompositionError(
                f"BoundaryAction {self.name!r}: forward_in must be empty "
                f"(boundary actions receive no internal forward signals)"
            )
        return self


class ControlAction(AtomicBlock):
    """Endogenous control — reads state, emits control signals.

    These are internal feedback loops: the system observing itself
    and generating signals that influence downstream policy/mechanism blocks.
    """

    kind: str = "control"
    options: list[str] = Field(default_factory=list)
    params_used: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class Policy(AtomicBlock):
    """Decision logic — maps signals to mechanism inputs.

    Policies select from feasible actions. Named options support
    scenario analysis and A/B testing.

    In GDS terms: policies implement the decision mapping
    within the admissibility constraint.
    """

    kind: str = "policy"
    options: list[str] = Field(default_factory=list)
    params_used: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class Mechanism(AtomicBlock):
    """State update — the only block type that writes to state.

    Mechanisms are the atomic state transitions that compose into h.
    They have no backward ports (state writes don't propagate signals).

    ``updates`` lists (entity_name, variable_name) pairs specifying
    which state variables this mechanism modifies.
    """

    kind: str = "mechanism"
    updates: list[tuple[str, str]] = Field(default_factory=list)
    params_used: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_no_backward(self) -> Self:
        if self.interface.backward_in or self.interface.backward_out:
            raise GDSCompositionError(
                f"Mechanism {self.name!r}: backward ports must be empty "
                f"(mechanisms write state, they don't pass backward signals)"
            )
        return self

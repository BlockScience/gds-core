"""Structural annotations linking blocks to state variable dependencies.

Paper Definitions 2.5, 2.7, and Assumption 3.2 from Zargham & Shorish
(2022), *Generalized Dynamical Systems Part I: Foundations*.

AdmissibleInputConstraint declares that a BoundaryAction's output
is constrained by state (U_x). TransitionSignature declares the
read dependency graph of a Mechanism's transition (f|_x).
StateMetric declares a distance function on a subset of state variables.

All follow the f_struct / f_behav split: the dependency graph
(which variables participate, what kind of metric) is structural (R1).
The actual constraint/transition/distance function is behavioral (R3).
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdmissibleInputConstraint(BaseModel):
    """Declares that a BoundaryAction's output is constrained by state.

    Paper Definition 2.5: U : X -> P(U), returning the set of
    admissible inputs given current state x.

    Structural part (R1): name, boundary_block, depends_on
    Behavioral part (R3): constraint callable (lossy in serialization)

    Keyed by ``name`` (not ``boundary_block``) to allow multiple
    constraints per BoundaryAction — e.g., balance limit + regulatory cap.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    boundary_block: str
    depends_on: list[tuple[str, str]] = Field(default_factory=list)
    constraint: Callable[[dict, Any], bool] | None = None
    description: str = ""


class TransitionSignature(BaseModel):
    """Declares the structural read signature of a mechanism's transition.

    Paper Definition 2.7: f|_x : U_x -> X, where
    Image(f|_x) = Image(f(x, .)).

    Writes are NOT included — ``Mechanism.updates`` already tracks those.
    One signature per mechanism (intentional simplification; a mechanism
    that updates multiple variables may have different read deps per
    variable, but this level of granularity is deferred).

    Structural part (R1): mechanism, reads, depends_on_blocks
    Behavioral part: the actual transition function (R3, not stored)
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    mechanism: str
    reads: list[tuple[str, str]] = Field(default_factory=list)
    depends_on_blocks: list[str] = Field(default_factory=list)
    preserves_invariant: str = ""


class StateMetric(BaseModel):
    """Declares a distance function on a subset of state variables.

    Paper Assumption 3.2: d_X : X x X -> R, a metric on the state space.

    Structural part (R1): name, variables (which entity-variable pairs
    participate), metric_type (annotation: "euclidean", "hamming", etc.)
    Behavioral part (R3): distance callable (lossy in serialization)

    One metric per name. A spec may have multiple metrics over different
    variable subsets (e.g., spatial distance vs. economic distance).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    variables: list[tuple[str, str]] = Field(default_factory=list)
    metric_type: str = ""
    distance: Callable[[Any, Any], float] | None = None
    description: str = ""

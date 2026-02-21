"""Core IR (Intermediate Representation) data models for GDS.

The IR is a flat, serializable representation that sits between the typed
DSL and the verification/report layers. Domain packages extend these
generic models with their own block types and metadata.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from gds.parameters import ParameterSchema


class FlowDirection(StrEnum):
    """Direction of an information flow in a block composition.

    - COVARIANT — forward data flow (forward_in → forward_out direction).
    - CONTRAVARIANT — backward feedback flow (backward_out → backward_in direction).
    """

    COVARIANT = "covariant"
    CONTRAVARIANT = "contravariant"


class CompositionType(StrEnum):
    """How blocks are composed within a system.

    - SEQUENTIAL — output of one feeds input of next (stack).
    - PARALLEL — blocks run side-by-side with no shared wires.
    - FEEDBACK — backward_out→backward_in connections within a timestep.
    - TEMPORAL — forward_out→forward_in connections across timesteps.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    FEEDBACK = "feedback"
    TEMPORAL = "temporal"


class BlockIR(BaseModel):
    """A single block in the flat IR representation.

    The ``block_type`` is a plain string — domain packages define their own
    type taxonomies (e.g., "decision", "policy", "mechanism").
    """

    name: str
    block_type: str = ""
    signature: tuple[str, str, str, str] = ("", "", "", "")
    logic: str = ""
    color_code: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class WiringIR(BaseModel):
    """A directed connection (edge) between blocks in the IR.

    ``is_feedback`` and ``is_temporal`` flags distinguish special wiring
    categories for verification. The ``category`` field is an open string
    that domain packages can use for domain-specific edge classification;
    the generic protocol only interprets ``"dataflow"``.
    """

    source: str
    target: str
    label: str
    wiring_type: str = ""
    direction: FlowDirection
    is_feedback: bool = False
    is_temporal: bool = False
    category: str = "dataflow"


class HierarchyNodeIR(BaseModel):
    """A node in the composition tree for visualization.

    Leaf nodes (composition_type=None) map 1:1 to a BlockIR.
    Interior nodes represent composition operators and contain children.
    """

    id: str
    name: str
    composition_type: CompositionType | None = None
    children: list[HierarchyNodeIR] = Field(default_factory=list)
    block_name: str | None = None
    exit_condition: str = ""


class SystemIR(BaseModel):
    """A complete composed system — the top-level IR unit.

    Domain packages wrap this with additional metadata (e.g., terminal
    conditions, action spaces for open games).
    """

    name: str
    blocks: list[BlockIR] = Field(default_factory=list)
    wirings: list[WiringIR] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    composition_type: CompositionType = CompositionType.SEQUENTIAL
    hierarchy: HierarchyNodeIR | None = None
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    parameter_schema: ParameterSchema = Field(default_factory=ParameterSchema)

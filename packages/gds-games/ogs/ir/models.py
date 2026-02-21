"""Core IR data models for open games specification.

Imports generic types from GDS and re-exports domain enums from the DSL
layer for backwards compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gds.ir.models import SystemIR

# Re-export generic GDS types for backwards compatibility
from gds.ir.models import FlowDirection
from gds.ir.models import HierarchyNodeIR as _GDSHierarchyNodeIR
from pydantic import BaseModel, Field

# Domain enums — canonical definitions live in ogs.dsl.types.
# Re-exported here so existing consumers (tests, notebooks, viz, reports,
# verification) continue to work without import changes.
from ogs.dsl.types import CompositionType, FlowType, GameType, InputType


class OpenGameIR(BaseModel):
    """A single open game component in the flat IR representation."""

    name: str
    game_type: GameType
    signature: tuple[str, str, str, str]  # (X, Y, R, S)
    logic: str = ""
    gds_function: str | None = None
    constraints: list[str] = Field(default_factory=list)
    parent_pattern: str | None = None
    color_code: int
    contained_nodes: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


class FlowIR(BaseModel):
    """A directed information flow (edge) between components in the IR."""

    source: str
    target: str
    label: str
    flow_type: FlowType
    direction: FlowDirection
    is_feedback: bool = False
    is_corecursive: bool = False


class InputIR(BaseModel):
    """An external input that crosses the pattern boundary."""

    name: str
    input_type: InputType
    schema_hint: str = ""
    shape: str = ""


# Metadata models — canonical definitions live in ogs.dsl.pattern.
# Imported directly for use in PatternIR fields, and re-exported as
# *IR aliases for backwards compatibility.
from ogs.dsl.pattern import (  # noqa: E402
    ActionSpace,
    StateInitialization,
    TerminalCondition,
)

ActionSpaceIR = ActionSpace
StateInitializationIR = StateInitialization
TerminalConditionIR = TerminalCondition


class HierarchyNodeIR(_GDSHierarchyNodeIR):
    """OGS hierarchy node — extends GDS with CORECURSIVE composition type.

    Inherits ``id``, ``name``, ``block_name``, ``exit_condition``, and
    ``children`` from GDS. Overrides ``composition_type`` to use the OGS
    enum which includes CORECURSIVE (mapped to GDS TEMPORAL).

    The ``game_name`` property is a backwards-compatible alias for
    ``block_name`` (inherited from GDS).
    """

    composition_type: CompositionType | None = None  # type: ignore[assignment]  # OGS enum (has CORECURSIVE)
    children: list[HierarchyNodeIR] = Field(default_factory=list)  # type: ignore[assignment]

    @property
    def game_name(self) -> str | None:
        """Backwards-compatible alias for ``block_name``."""
        return self.block_name


class PatternIR(BaseModel):
    """A complete composite pattern — the top-level unit of specification."""

    name: str
    games: list[OpenGameIR] = Field(default_factory=list)
    flows: list[FlowIR] = Field(default_factory=list)
    inputs: list[InputIR] = Field(default_factory=list)
    composition_type: CompositionType
    terminal_conditions: list[TerminalCondition] | None = None
    action_spaces: list[ActionSpace] | None = None
    initialization: list[StateInitialization] | None = None
    hierarchy: HierarchyNodeIR | None = None
    source_canvas: str
    source_spec_notes: str | None = None

    def to_system_ir(self) -> SystemIR:
        """Project this OGS PatternIR to a GDS SystemIR.

        Enables interop with any GDS tool that accepts SystemIR, including
        GDS generic verification checks (G-001 through G-006).

        Mapping:
        - OpenGameIR → BlockIR (game_type → block_type, constraints/tags → metadata)
        - FlowIR → WiringIR (flow_type → wiring_type, is_corecursive → is_temporal)
        - OGS CORECURSIVE → GDS TEMPORAL
        """
        from gds.ir.models import BlockIR, SystemIR, WiringIR
        from gds.ir.models import CompositionType as GDSCompositionType

        blocks = [
            BlockIR(
                name=g.name,
                block_type=g.game_type.value,
                signature=g.signature,
                logic=g.logic,
                color_code=g.color_code,
                metadata={"constraints": g.constraints, "tags": g.tags},
            )
            for g in self.games
        ]

        wirings = [
            WiringIR(
                source=f.source,
                target=f.target,
                label=f.label,
                wiring_type=f.flow_type.value,
                direction=f.direction,
                is_feedback=f.is_feedback,
                is_temporal=f.is_corecursive,
            )
            for f in self.flows
        ]

        # Map OGS composition types to GDS (CORECURSIVE → TEMPORAL)
        comp_map = {
            "sequential": "SEQUENTIAL",
            "parallel": "PARALLEL",
            "feedback": "FEEDBACK",
            "corecursive": "TEMPORAL",
        }
        gds_comp = GDSCompositionType[comp_map[self.composition_type.value]]

        inputs = [
            {
                "name": i.name,
                "input_type": i.input_type.value,
                "schema_hint": i.schema_hint,
            }
            for i in self.inputs
        ]

        return SystemIR(
            name=self.name,
            blocks=blocks,
            wirings=wirings,
            inputs=inputs,
            composition_type=gds_comp,
            source=self.source_canvas,
        )

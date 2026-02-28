"""SupplyChainModel — declarative container for supply chain networks.

Users declare nodes, shipments, demand sources, and order policies.
The model validates structural integrity at construction time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_business.common.errors import BizValidationError
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class SupplyChainModel(BaseModel):
    """A complete supply chain network declaration.

    Validates at construction:
    1. At least one node
    2. No duplicate node names
    3. Shipment source/target reference declared nodes
    4. Demand target references a declared node
    5. OrderPolicy node references a declared node
    6. OrderPolicy inputs reference declared nodes
    """

    name: str
    nodes: list[SupplyNode]
    shipments: list[Shipment] = Field(default_factory=list)
    demand_sources: list[DemandSource] = Field(default_factory=list)
    order_policies: list[OrderPolicy] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one node
        if not self.nodes:
            errors.append("Supply chain must have at least one node")

        # 2. No duplicate node names
        names: list[str] = [n.name for n in self.nodes]
        seen: set[str] = set()
        for n in names:
            if n in seen:
                errors.append(f"Duplicate node name: {n!r}")
            seen.add(n)

        node_names = set(names)

        # 3. Shipment source/target reference declared nodes
        for s in self.shipments:
            if s.source_node not in node_names:
                errors.append(
                    f"Shipment {s.name!r} source_node {s.source_node!r} "
                    f"is not a declared node"
                )
            if s.target_node not in node_names:
                errors.append(
                    f"Shipment {s.name!r} target_node {s.target_node!r} "
                    f"is not a declared node"
                )

        # 4. Demand target references a declared node
        for d in self.demand_sources:
            if d.target_node not in node_names:
                errors.append(
                    f"DemandSource {d.name!r} target_node {d.target_node!r} "
                    f"is not a declared node"
                )

        # 5. OrderPolicy node references a declared node
        for op in self.order_policies:
            if op.node not in node_names:
                errors.append(
                    f"OrderPolicy {op.name!r} node {op.node!r} is not a declared node"
                )

        # 6. OrderPolicy inputs reference declared nodes
        for op in self.order_policies:
            for inp in op.inputs:
                if inp not in node_names:
                    errors.append(
                        f"OrderPolicy {op.name!r} input {inp!r} is not a declared node"
                    )

        if errors:
            raise BizValidationError(
                f"SupplyChainModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def node_names(self) -> set[str]:
        return {n.name for n in self.nodes}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_business.supplychain.compile import compile_scn

        return compile_scn(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_business.supplychain.compile import compile_scn_to_system

        return compile_scn_to_system(self)

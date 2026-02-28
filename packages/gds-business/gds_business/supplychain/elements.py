"""Supply chain network element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class SupplyNode(BaseModel, frozen=True):
    """A warehouse, factory, or distribution center node.

    Maps to: GDS Mechanism (state update f) + Entity (inventory state X).
    """

    name: str
    initial_inventory: float = 0.0
    capacity: float = Field(default=float("inf"), description="Max inventory capacity")
    description: str = ""


class Shipment(BaseModel, frozen=True):
    """A directed flow link between supply nodes.

    Maps to: GDS Wiring.
    """

    name: str
    source_node: str
    target_node: str
    lead_time: float = 1.0


class DemandSource(BaseModel, frozen=True):
    """An exogenous demand signal entering the network.

    Maps to: GDS BoundaryAction (exogenous input U).
    """

    name: str
    target_node: str
    description: str = ""


class OrderPolicy(BaseModel, frozen=True):
    """A reorder decision logic node.

    Maps to: GDS Policy (decision logic g).
    Observes inventory and demand signals, emits order decisions.
    """

    name: str
    node: str
    inputs: list[str] = Field(
        default_factory=list,
        description="Names of nodes whose inventory this policy observes",
    )

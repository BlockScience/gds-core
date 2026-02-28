"""Compiler: ERDModel -> GDSSpec -> SystemIR.

ERDs are primarily state-focused — the composition tree is flat.
Each relationship becomes a Mechanism that cross-updates entities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.roles import Mechanism
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

from gds_software.common.compile_utils import parallel_tier
from gds_software.erd.elements import ERDEntity, ERDRelationship

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.erd.model import ERDModel


# ── Semantic types ───────────────────────────────────────────

ERDAttributeType = TypeDef(
    name="ERD Attribute",
    python_type=dict,
    description="ERD entity attribute data",
)

ERDAttributeSpace = Space(
    name="ERD AttributeSpace",
    fields={"value": ERDAttributeType},
    description="Space for ERD attribute data",
)


# ── Port naming helpers ──────────────────────────────────────


def _entity_port_name(name: str) -> str:
    return f"{name} Entity"


def _rel_block_name(name: str) -> str:
    return f"{name} Relationship"


# ── Block builders ───────────────────────────────────────────


def _build_relationship_mechanism(rel: ERDRelationship, model: ERDModel) -> Mechanism:
    """ERDRelationship -> Mechanism: cross-entity state update."""
    return Mechanism(
        name=_rel_block_name(rel.name),
        interface=Interface(
            forward_in=(port(_entity_port_name(rel.source)),),
            forward_out=(port(_entity_port_name(rel.target)),),
        ),
        updates=[(rel.target, rel.name)],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_erd_entity(entity: ERDEntity) -> Entity:
    """Create a GDS Entity with StateVariables for each attribute."""
    variables = {}
    for attr in entity.attributes:
        variables[attr.name] = StateVariable(
            name=attr.name,
            typedef=ERDAttributeType,
            description=f"Attribute {attr.name} of {entity.name}",
        )

    # Ensure at least one variable
    if not variables:
        variables["id"] = StateVariable(
            name="id",
            typedef=ERDAttributeType,
            description=f"Default ID for {entity.name}",
        )

    return Entity(
        name=entity.name,
        variables=variables,
        description=f"ERD entity {entity.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: ERDModel) -> Block:
    """Build flat composition — relationships in parallel.

    ERDs are state-focused, so the composition is flat:
        (relationship_mechanisms |)
    """
    blocks: list[Block] = []
    for rel in model.relationships:
        blocks.append(_build_relationship_mechanism(rel, model))

    if not blocks:
        # No relationships — create a single placeholder mechanism
        # for the first entity
        entity = model.entities[0]
        return Mechanism(
            name=f"{entity.name} Identity",
            interface=Interface(
                forward_out=(port(_entity_port_name(entity.name)),),
            ),
            updates=[(entity.name, "id")],
        )

    return parallel_tier(blocks)


# ── Public API ───────────────────────────────────────────────


def compile_erd(model: ERDModel) -> GDSSpec:
    """Compile an ERDModel into a GDSSpec."""
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(ERDAttributeType)

    # 2. Register spaces
    spec.collect(ERDAttributeSpace)

    # 3. Register entities
    for entity in model.entities:
        spec.register_entity(_build_erd_entity(entity))

    # 4. Register blocks
    for rel in model.relationships:
        spec.register_block(_build_relationship_mechanism(rel, model))

    # If no relationships, create identity mechanism
    if not model.relationships:
        entity = model.entities[0]
        spec.register_block(
            Mechanism(
                name=f"{entity.name} Identity",
                interface=Interface(
                    forward_out=(port(_entity_port_name(entity.name)),),
                ),
                updates=[(entity.name, "id")],
            )
        )

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for rel in model.relationships:
        wires.append(
            Wire(
                source=_rel_block_name(rel.name),
                target=_rel_block_name(rel.name),
                space="ERD AttributeSpace",
            )
        )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for ERD {model.name!r}",
        )
    )

    return spec


def compile_erd_to_system(model: ERDModel) -> SystemIR:
    """Compile an ERDModel directly to SystemIR."""
    root = _build_composition_tree(model)
    return compile_system(model.name, root)

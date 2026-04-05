"""GDS Data Model — modeled as an Entity-Relationship Diagram.

Models the Pydantic model graph of gds-framework: GDSSpec has Blocks,
Blocks have Interfaces, Interfaces have Ports, etc. This ERD formalizes
the structural relationships that are currently implicit in the code.

The ERD compiles to a GDSSpec where entities become stateful mechanisms
and relationships become wirings — revealing the data model as a
dynamical system where state = the registry contents.
"""

from gds import project_canonical, verify
from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds_domains.software.erd.compile import compile_erd, compile_erd_to_system
from gds_domains.software.erd.elements import (
    Attribute,
    Cardinality,
    ERDEntity,
    ERDRelationship,
)
from gds_domains.software.erd.model import ERDModel
from gds_viz import system_to_mermaid


def build_erd_model() -> ERDModel:
    """Build the GDS data model as an ERD."""
    return ERDModel(
        name="GDS Data Model",
        description="The Pydantic model graph of gds-framework",
        entities=[
            ERDEntity(
                name="GDSSpec",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="description", type="str", is_nullable=True),
                ],
                description="Central specification registry",
            ),
            ERDEntity(
                name="Block",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="kind", type="str"),
                ],
                description="Compositional unit (AtomicBlock or composed)",
            ),
            ERDEntity(
                name="Interface",
                attributes=[
                    Attribute(name="forward_in", type="tuple[Port]"),
                    Attribute(name="forward_out", type="tuple[Port]"),
                    Attribute(name="backward_in", type="tuple[Port]"),
                    Attribute(name="backward_out", type="tuple[Port]"),
                ],
                description="Bidirectional typed boundary of a Block",
            ),
            ERDEntity(
                name="Port",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="type_tokens", type="frozenset[str]"),
                ],
                description="Named typed connection point",
            ),
            ERDEntity(
                name="TypeDef",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="python_type", type="type"),
                    Attribute(name="constraint", type="Callable", is_nullable=True),
                ],
                description="Runtime-constrained type definition",
            ),
            ERDEntity(
                name="Entity",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                ],
                description="State space dimension (groups StateVariables)",
            ),
            ERDEntity(
                name="StateVariable",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="symbol", type="str", is_nullable=True),
                ],
                description="Single dimension of X",
            ),
            ERDEntity(
                name="SpecWiring",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                ],
                description="Explicit data flow connections between blocks",
            ),
            ERDEntity(
                name="Wire",
                attributes=[
                    Attribute(name="source", type="str"),
                    Attribute(name="target", type="str"),
                    Attribute(name="space", type="str", is_nullable=True),
                ],
                description="Single connection from source block to target",
            ),
        ],
        relationships=[
            ERDRelationship(
                name="has_block",
                source="GDSSpec",
                target="Block",
                cardinality=Cardinality.ONE_TO_MANY,
                description="A spec registers many blocks",
            ),
            ERDRelationship(
                name="has_interface",
                source="Block",
                target="Interface",
                cardinality=Cardinality.ONE_TO_ONE,
                description="Each block has exactly one interface",
            ),
            ERDRelationship(
                name="has_port",
                source="Interface",
                target="Port",
                cardinality=Cardinality.ONE_TO_MANY,
                description="An interface has many ports across 4 slots",
            ),
            ERDRelationship(
                name="has_type",
                source="GDSSpec",
                target="TypeDef",
                cardinality=Cardinality.ONE_TO_MANY,
                description="A spec registers many type definitions",
            ),
            ERDRelationship(
                name="has_entity",
                source="GDSSpec",
                target="Entity",
                cardinality=Cardinality.ONE_TO_MANY,
                description="A spec registers many entities",
            ),
            ERDRelationship(
                name="has_variable",
                source="Entity",
                target="StateVariable",
                cardinality=Cardinality.ONE_TO_MANY,
                description="An entity groups many state variables",
            ),
            ERDRelationship(
                name="typed_by",
                source="StateVariable",
                target="TypeDef",
                cardinality=Cardinality.MANY_TO_ONE,
                description="Each variable is typed by a TypeDef",
            ),
            ERDRelationship(
                name="has_wiring",
                source="GDSSpec",
                target="SpecWiring",
                cardinality=Cardinality.ONE_TO_MANY,
                description="A spec has many wiring groups",
            ),
            ERDRelationship(
                name="has_wire",
                source="SpecWiring",
                target="Wire",
                cardinality=Cardinality.ONE_TO_MANY,
                description="A wiring group has many wires",
            ),
        ],
    )


def build_erd_spec() -> GDSSpec:
    return compile_erd(build_erd_model())


def build_erd_system() -> SystemIR:
    return compile_erd_to_system(build_erd_model())


if __name__ == "__main__":
    model = build_erd_model()
    spec = build_erd_spec()
    ir = build_erd_system()
    report = verify(ir)
    canonical = project_canonical(spec)

    print("=== GDS Data Model (ERD) ===")
    print(f"Entities: {len(model.entities)}")
    print(f"Relationships: {len(model.relationships)}")
    print(f"Blocks: {len(spec.blocks)}")
    print(f"Verification: {report.errors} errors")
    print("")
    print(f"=== Canonical: {canonical.formula} ===")
    print(f"U: {canonical.boundary_blocks}")
    print(f"g: {canonical.policy_blocks}")
    print(f"f: {canonical.mechanism_blocks}")
    print(f"X: {canonical.state_variables}")
    print("")
    print(system_to_mermaid(ir))

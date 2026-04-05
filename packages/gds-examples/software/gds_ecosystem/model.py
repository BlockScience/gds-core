"""GDS Ecosystem — the monorepo modeled using its own software architecture DSL.

Dog-fooding: the GDS framework models its own package dependency graph
as a component diagram, compiles it to GDSSpec, verifies it, and
derives the canonical decomposition.

Result: h = g (stateless — pure API composition). The ecosystem has no
mutable state; all packages are pure API providers/consumers connected
by typed interfaces.

Concepts Covered:
    - Component diagram with provides/requires interfaces
    - Connector-based dependency wiring
    - Compilation to GDSSpec and SystemIR
    - Canonical decomposition of the ecosystem
    - Self-referential modeling (framework models itself)

GDS Decomposition:
    X  = {} (empty — no stateful components)
    U  = {GDSSpec, SimAPI, ODEAPI} (provider APIs)
    g  = {gds-games, gds-stockflow, gds-control, gds-owl,
          gds-analysis, gds-symbolic} (consumer packages)
    f  = {} (no state updates)
    h  = g (stateless composition)
"""

from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds_domains.software.component.compile import (
    compile_component,
    compile_component_to_system,
)
from gds_domains.software.component.elements import Component, Connector, InterfaceDef
from gds_domains.software.component.model import ComponentModel

# ── Components (packages) ──────────────────────────────────────

gds_framework = Component(
    name="gds-framework",
    provides=["GDSSpec"],
    description="Core engine: blocks, composition, verification (pydantic only)",
)

gds_games = Component(
    name="gds-games",
    requires=["GDSSpec"],
    description="Game theory DSL + Nash equilibrium",
)

gds_stockflow = Component(
    name="gds-stockflow",
    requires=["GDSSpec"],
    description="Stock-flow DSL",
)

gds_control = Component(
    name="gds-control",
    requires=["GDSSpec"],
    provides=["ControlAPI"],
    description="Control systems DSL",
)

gds_owl = Component(
    name="gds-owl",
    requires=["GDSSpec"],
    description="OWL/SHACL/SPARQL export/import",
)

gds_sim = Component(
    name="gds-sim",
    provides=["SimAPI"],
    description="Discrete-time simulation engine (standalone)",
)

gds_analysis = Component(
    name="gds-analysis",
    requires=["GDSSpec", "SimAPI", "ODEAPI"],
    description="Reachability, metrics, constraint enforcement",
)

gds_continuous = Component(
    name="gds-continuous",
    provides=["ODEAPI"],
    description="Continuous-time ODE engine (standalone, scipy)",
)

gds_symbolic = Component(
    name="gds-symbolic",
    requires=["ControlAPI"],
    description="SymPy bridge + Hamiltonian mechanics",
)

# ── Interfaces ─────────────────────────────────────────────────

interfaces = [
    InterfaceDef(
        name="GDSSpec",
        provided_by="gds-framework",
        description="Structural specification registry",
    ),
    InterfaceDef(
        name="SimAPI",
        provided_by="gds-sim",
        description="Discrete trajectory execution",
    ),
    InterfaceDef(
        name="ODEAPI",
        provided_by="gds-continuous",
        description="ODE integration",
    ),
    InterfaceDef(
        name="ControlAPI",
        provided_by="gds-control",
        description="Control model compilation",
    ),
]

# ── Connectors (dependency wiring) ─────────────────────────────

connectors = [
    Connector(
        name="games-uses-framework",
        source="gds-framework",
        source_interface="GDSSpec",
        target="gds-games",
        target_interface="GDSSpec",
    ),
    Connector(
        name="stockflow-uses-framework",
        source="gds-framework",
        source_interface="GDSSpec",
        target="gds-stockflow",
        target_interface="GDSSpec",
    ),
    Connector(
        name="control-uses-framework",
        source="gds-framework",
        source_interface="GDSSpec",
        target="gds-control",
        target_interface="GDSSpec",
    ),
    Connector(
        name="owl-uses-framework",
        source="gds-framework",
        source_interface="GDSSpec",
        target="gds-owl",
        target_interface="GDSSpec",
    ),
    Connector(
        name="symbolic-uses-control",
        source="gds-control",
        source_interface="ControlAPI",
        target="gds-symbolic",
        target_interface="ControlAPI",
    ),
    Connector(
        name="analysis-uses-framework",
        source="gds-framework",
        source_interface="GDSSpec",
        target="gds-analysis",
        target_interface="GDSSpec",
    ),
    Connector(
        name="analysis-uses-sim",
        source="gds-sim",
        source_interface="SimAPI",
        target="gds-analysis",
        target_interface="SimAPI",
    ),
    Connector(
        name="analysis-uses-continuous",
        source="gds-continuous",
        source_interface="ODEAPI",
        target="gds-analysis",
        target_interface="ODEAPI",
    ),
]


def build_model() -> ComponentModel:
    """Build the GDS ecosystem component model."""
    return ComponentModel(
        name="GDS Ecosystem",
        description="The GDS monorepo modeled using its own component DSL",
        components=[
            gds_framework,
            gds_games,
            gds_stockflow,
            gds_control,
            gds_owl,
            gds_sim,
            gds_analysis,
            gds_continuous,
            gds_symbolic,
        ],
        interfaces=interfaces,
        connectors=connectors,
    )


def build_spec() -> GDSSpec:
    """Compile the ecosystem model to a GDSSpec."""
    return compile_component(build_model())


def build_system() -> SystemIR:
    """Compile the ecosystem model to a SystemIR."""
    return compile_component_to_system(build_model())

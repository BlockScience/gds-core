"""GDS User Pipeline — modeled as a Data Flow Diagram.

Models the actual data transformation pipeline a user follows:
User → define spec → compile → verify → export to OWL → simulate → analyze

This DFD reveals the data flows between GDS subsystems and identifies
where data transforms (processes) vs where it persists (data stores).

GDS Decomposition:
    X  = {GDSSpec, SystemIR, VerificationReport, RDFGraph, Trajectory}
    U  = {User, DSL Definitions}
    g  = {Compile, Verify, Export, Adapt}
    f  = {Simulate, Analyze} (state-updating processes)
"""

from gds import project_canonical, verify
from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds_domains.software.dfd.compile import compile_dfd, compile_dfd_to_system
from gds_domains.software.dfd.elements import (
    DataFlow,
    DataStore,
    ExternalEntity,
    Process,
)
from gds_domains.software.dfd.model import DFDModel
from gds_viz import system_to_mermaid


def build_dfd_model() -> DFDModel:
    """Build the GDS user pipeline as a DFD."""
    return DFDModel(
        name="GDS User Pipeline",
        description="Data flow through the GDS ecosystem from spec to analysis",
        external_entities=[
            ExternalEntity(name="User", description="Modeler defining a system"),
            ExternalEntity(
                name="DSL",
                description="Domain-specific language (stockflow, control, etc.)",
            ),
        ],
        processes=[
            Process(
                name="Register Spec",
                description="Build GDSSpec from types, entities, blocks, wirings",
            ),
            Process(
                name="Compile",
                description="Flatten composition tree to SystemIR",
            ),
            Process(
                name="Verify",
                description="Run G-001..G-006 + SC-001..SC-009 checks",
            ),
            Process(
                name="Export to OWL",
                description="Serialize GDSSpec to RDF/Turtle via gds-owl",
            ),
            Process(
                name="Adapt to Sim",
                description="Bridge spec to gds-sim Model via gds-analysis",
            ),
            Process(
                name="Simulate",
                description="Execute trajectories via gds-sim or gds-continuous",
            ),
            Process(
                name="Analyze",
                description="Compute reachability, metrics, distances",
            ),
        ],
        data_stores=[
            DataStore(name="GDSSpec Store", description="Structural specification"),
            DataStore(name="SystemIR Store", description="Flat IR"),
            DataStore(name="RDF Graph", description="OWL/Turtle serialization"),
            DataStore(name="Trajectory Store", description="Simulation results"),
        ],
        data_flows=[
            # User inputs
            DataFlow(
                name="types + entities",
                source="User",
                target="Register Spec",
                data="TypeDefs, Entities, Blocks",
            ),
            DataFlow(
                name="DSL model",
                source="DSL",
                target="Register Spec",
                data="Domain model (StockFlowModel, ControlModel, etc.)",
            ),
            # Spec registration
            DataFlow(
                name="spec",
                source="Register Spec",
                target="GDSSpec Store",
                data="GDSSpec",
            ),
            # Compilation
            DataFlow(
                name="spec to compile",
                source="GDSSpec Store",
                target="Compile",
                data="GDSSpec + Block tree",
            ),
            DataFlow(
                name="system ir",
                source="Compile",
                target="SystemIR Store",
                data="SystemIR",
            ),
            # Verification
            DataFlow(
                name="ir to verify",
                source="SystemIR Store",
                target="Verify",
                data="SystemIR",
            ),
            DataFlow(
                name="report",
                source="Verify",
                target="User",
                data="VerificationReport",
            ),
            # OWL export
            DataFlow(
                name="spec to owl",
                source="GDSSpec Store",
                target="Export to OWL",
                data="GDSSpec",
            ),
            DataFlow(
                name="rdf",
                source="Export to OWL",
                target="RDF Graph",
                data="Turtle/RDF",
            ),
            # Simulation
            DataFlow(
                name="spec to adapter",
                source="GDSSpec Store",
                target="Adapt to Sim",
                data="GDSSpec + policies + SUFs",
            ),
            DataFlow(
                name="model",
                source="Adapt to Sim",
                target="Simulate",
                data="gds_sim.Model",
            ),
            DataFlow(
                name="trajectory",
                source="Simulate",
                target="Trajectory Store",
                data="Results (trajectory rows)",
            ),
            # Analysis
            DataFlow(
                name="trajectory to analyze",
                source="Trajectory Store",
                target="Analyze",
                data="Trajectory + StateMetric",
            ),
            DataFlow(
                name="analysis results",
                source="Analyze",
                target="User",
                data="Distances, R(x), X_C",
            ),
        ],
    )


def build_dfd_spec() -> GDSSpec:
    return compile_dfd(build_dfd_model())


def build_dfd_system() -> SystemIR:
    return compile_dfd_to_system(build_dfd_model())


if __name__ == "__main__":
    model = build_dfd_model()
    spec = build_dfd_spec()
    ir = build_dfd_system()
    report = verify(ir)
    canonical = project_canonical(spec)

    print("=== GDS User Pipeline (DFD) ===")
    print(f"Blocks: {len(spec.blocks)}")
    print(f"Wirings: {len(spec.wirings)}")
    print(f"Verification: {report.errors} errors")
    print("")
    print(f"=== Canonical: {canonical.formula} ===")
    print(f"U: {canonical.boundary_blocks}")
    print(f"g: {canonical.policy_blocks}")
    print(f"f: {canonical.mechanism_blocks}")
    print(f"X: {canonical.state_variables}")
    print("")
    print(system_to_mermaid(ir))

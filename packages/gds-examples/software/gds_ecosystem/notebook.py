import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium", app_title="GDS Ecosystem Self-Model")


@app.cell
def imports():
    import marimo as mo

    from gds import project_canonical, verify
    from gds_software.component.compile import (
        compile_component,
        compile_component_to_system,
    )
    from gds_software.component.elements import (
        Component,
        Connector,
        InterfaceDef,
    )
    from gds_software.component.model import ComponentModel
    from gds_software.dfd.compile import compile_dfd, compile_dfd_to_system
    from gds_software.dfd.elements import (
        DataFlow,
        DataStore,
        ExternalEntity,
        Process,
    )
    from gds_software.dfd.model import DFDModel
    from gds_software.erd.compile import compile_erd, compile_erd_to_system
    from gds_software.erd.elements import (
        Attribute,
        Cardinality,
        ERDEntity,
        ERDRelationship,
    )
    from gds_software.erd.model import ERDModel
    from gds_viz import system_to_mermaid

    return (
        Attribute,
        Cardinality,
        Component,
        ComponentModel,
        Connector,
        DataFlow,
        DataStore,
        DFDModel,
        ERDEntity,
        ERDModel,
        ERDRelationship,
        ExternalEntity,
        InterfaceDef,
        Process,
        compile_component,
        compile_component_to_system,
        compile_dfd,
        compile_dfd_to_system,
        compile_erd,
        compile_erd_to_system,
        mo,
        project_canonical,
        system_to_mermaid,
        verify,
    )


@app.cell
def intro(mo):
    mo.md("""# GDS Ecosystem Self-Model

The GDS framework models **itself** using three of its own
software architecture diagram types. This is dog-fooding:
the framework's DSLs, compilers, and verification checks
are applied to the framework's own package structure.

Each diagram type reveals a different canonical form:

| Diagram | Canonical | What it reveals |
|---------|-----------|-----------------|
| Component | h = g | Package API dependencies (stateless) |
| DFD | h = f . g | User data pipeline (full dynamics) |
| ERD | h = f | Pydantic model graph (pure state) |
""")
    return


@app.cell
def component_model(Component, ComponentModel, Connector, InterfaceDef, mo):
    mo.md("## 1. Component Diagram — Package Dependencies")

    comp_model = ComponentModel(
        name="GDS Ecosystem",
        description="Package dependency graph",
        components=[
            Component(
                name="gds-framework",
                provides=["GDSSpec"],
                description="Core engine",
            ),
            Component(
                name="gds-games",
                requires=["GDSSpec"],
                description="Game theory DSL",
            ),
            Component(
                name="gds-stockflow",
                requires=["GDSSpec"],
                description="Stock-flow DSL",
            ),
            Component(
                name="gds-control",
                requires=["GDSSpec"],
                provides=["ControlAPI"],
                description="Control DSL",
            ),
            Component(
                name="gds-owl",
                requires=["GDSSpec"],
                description="OWL/SHACL/SPARQL",
            ),
            Component(
                name="gds-sim",
                provides=["SimAPI"],
                description="Simulation engine",
            ),
            Component(
                name="gds-analysis",
                requires=["GDSSpec", "SimAPI", "ODEAPI"],
                description="Reachability + metrics",
            ),
            Component(
                name="gds-continuous",
                provides=["ODEAPI"],
                description="ODE engine",
            ),
            Component(
                name="gds-symbolic",
                requires=["ControlAPI"],
                description="SymPy + Hamiltonian",
            ),
        ],
        interfaces=[
            InterfaceDef(
                name="GDSSpec",
                provided_by="gds-framework",
                description="Spec API",
            ),
            InterfaceDef(
                name="SimAPI",
                provided_by="gds-sim",
                description="Sim API",
            ),
            InterfaceDef(
                name="ODEAPI",
                provided_by="gds-continuous",
                description="ODE API",
            ),
            InterfaceDef(
                name="ControlAPI",
                provided_by="gds-control",
                description="Control API",
            ),
        ],
        connectors=[
            Connector(
                name="d1",
                source="gds-framework",
                source_interface="GDSSpec",
                target="gds-games",
                target_interface="GDSSpec",
            ),
            Connector(
                name="d2",
                source="gds-framework",
                source_interface="GDSSpec",
                target="gds-stockflow",
                target_interface="GDSSpec",
            ),
            Connector(
                name="d3",
                source="gds-framework",
                source_interface="GDSSpec",
                target="gds-control",
                target_interface="GDSSpec",
            ),
            Connector(
                name="d4",
                source="gds-framework",
                source_interface="GDSSpec",
                target="gds-owl",
                target_interface="GDSSpec",
            ),
            Connector(
                name="d5",
                source="gds-control",
                source_interface="ControlAPI",
                target="gds-symbolic",
                target_interface="ControlAPI",
            ),
            Connector(
                name="d6",
                source="gds-framework",
                source_interface="GDSSpec",
                target="gds-analysis",
                target_interface="GDSSpec",
            ),
            Connector(
                name="d7",
                source="gds-sim",
                source_interface="SimAPI",
                target="gds-analysis",
                target_interface="SimAPI",
            ),
            Connector(
                name="d8",
                source="gds-continuous",
                source_interface="ODEAPI",
                target="gds-analysis",
                target_interface="ODEAPI",
            ),
        ],
    )
    return (comp_model,)


@app.cell
def component_results(
    comp_model,
    compile_component,
    compile_component_to_system,
    mo,
    project_canonical,
    system_to_mermaid,
    verify,
):
    _spec = compile_component(comp_model)
    _ir = compile_component_to_system(comp_model)
    _report = verify(_ir)
    _canonical = project_canonical(_spec)

    _sv = ", ".join(f"{e}.{v}" for e, v in _canonical.state_variables)
    _mf = ", ".join(_canonical.mechanism_blocks) or "(none)"
    mo.md(
        f"""
        **Blocks:** {len(_spec.blocks)} |
        **Verification errors:** {_report.errors}

        **Canonical:** h = g (stateless)
        - Boundary (U): {", ".join(_canonical.boundary_blocks)}
        - Policy (g): {", ".join(_canonical.policy_blocks)}
        - Mechanism (f): {_mf}
        - State (X): {_sv or "(none)"}
        """
    )

    _mermaid = system_to_mermaid(_ir)
    mo.mermaid(_mermaid)
    return


@app.cell
def dfd_model(
    DFDModel,
    DataFlow,
    DataStore,
    ExternalEntity,
    Process,
    compile_dfd,
    compile_dfd_to_system,
    mo,
    project_canonical,
    system_to_mermaid,
    verify,
):
    mo.md("## 2. DFD — User Data Pipeline")

    _dfd = DFDModel(
        name="GDS User Pipeline",
        description="Data flow from spec definition to analysis",
        external_entities=[
            ExternalEntity(name="User", description="Modeler"),
            ExternalEntity(name="DSL", description="Domain language"),
        ],
        processes=[
            Process(name="Register Spec", description="Build GDSSpec"),
            Process(name="Compile", description="Block tree to SystemIR"),
            Process(name="Verify", description="G + SC checks"),
            Process(name="Export to OWL", description="Serialize to RDF"),
            Process(name="Adapt to Sim", description="spec_to_model()"),
            Process(name="Simulate", description="Run trajectories"),
            Process(name="Analyze", description="Reachability + metrics"),
        ],
        data_stores=[
            DataStore(name="GDSSpec Store", description="Spec registry"),
            DataStore(name="SystemIR Store", description="Flat IR"),
            DataStore(name="RDF Graph", description="Turtle/OWL"),
            DataStore(name="Trajectory Store", description="Results"),
        ],
        data_flows=[
            DataFlow(
                name="f1",
                source="User",
                target="Register Spec",
                data="types, entities, blocks",
            ),
            DataFlow(
                name="f2", source="DSL", target="Register Spec", data="domain model"
            ),
            DataFlow(
                name="f3",
                source="Register Spec",
                target="GDSSpec Store",
                data="GDSSpec",
            ),
            DataFlow(
                name="f4",
                source="GDSSpec Store",
                target="Compile",
                data="spec + block tree",
            ),
            DataFlow(
                name="f5", source="Compile", target="SystemIR Store", data="SystemIR"
            ),
            DataFlow(
                name="f6", source="SystemIR Store", target="Verify", data="SystemIR"
            ),
            DataFlow(
                name="f7", source="Verify", target="User", data="VerificationReport"
            ),
            DataFlow(
                name="f8",
                source="GDSSpec Store",
                target="Export to OWL",
                data="GDSSpec",
            ),
            DataFlow(
                name="f9", source="Export to OWL", target="RDF Graph", data="Turtle"
            ),
            DataFlow(
                name="f10",
                source="GDSSpec Store",
                target="Adapt to Sim",
                data="GDSSpec",
            ),
            DataFlow(
                name="f11",
                source="Adapt to Sim",
                target="Simulate",
                data="gds_sim.Model",
            ),
            DataFlow(
                name="f12", source="Simulate", target="Trajectory Store", data="Results"
            ),
            DataFlow(
                name="f13",
                source="Trajectory Store",
                target="Analyze",
                data="trajectory",
            ),
            DataFlow(
                name="f14", source="Analyze", target="User", data="R(x), distances"
            ),
        ],
    )

    _spec = compile_dfd(_dfd)
    _ir = compile_dfd_to_system(_dfd)
    _report = verify(_ir)
    _canonical = project_canonical(_spec)

    mo.md(
        f"""
        **Blocks:** {len(_spec.blocks)} |
        **Verification errors:** {_report.errors}

        **Canonical:** h = f . g (full dynamical system)
        - Boundary (U): {", ".join(_canonical.boundary_blocks)}
        - Policy (g): {", ".join(_canonical.policy_blocks)}
        - Mechanism (f): {", ".join(_canonical.mechanism_blocks)}
        - State (X): {", ".join(f"{e}.{v}" for e, v in _canonical.state_variables)}
        """
    )

    mo.mermaid(system_to_mermaid(_ir))
    return


@app.cell
def erd_model(
    Attribute,
    Cardinality,
    ERDEntity,
    ERDModel,
    ERDRelationship,
    compile_erd,
    compile_erd_to_system,
    mo,
    project_canonical,
    system_to_mermaid,
    verify,
):
    mo.md("## 3. ERD — GDS Data Model")

    _erd = ERDModel(
        name="GDS Data Model",
        description="Pydantic model graph of gds-framework",
        entities=[
            ERDEntity(
                name="GDSSpec",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                ],
            ),
            ERDEntity(
                name="Block",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="kind", type="str"),
                ],
            ),
            ERDEntity(
                name="Interface",
                attributes=[
                    Attribute(name="forward_in", type="tuple[Port]"),
                    Attribute(name="forward_out", type="tuple[Port]"),
                ],
            ),
            ERDEntity(
                name="Port",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="type_tokens", type="frozenset"),
                ],
            ),
            ERDEntity(
                name="TypeDef",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="python_type", type="type"),
                ],
            ),
            ERDEntity(
                name="Entity",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                ],
            ),
            ERDEntity(
                name="StateVariable",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                    Attribute(name="symbol", type="str", is_nullable=True),
                ],
            ),
            ERDEntity(
                name="SpecWiring",
                attributes=[
                    Attribute(name="name", type="str", is_primary_key=True),
                ],
            ),
            ERDEntity(
                name="Wire",
                attributes=[
                    Attribute(name="source", type="str"),
                    Attribute(name="target", type="str"),
                ],
            ),
        ],
        relationships=[
            ERDRelationship(
                name="has_block",
                source="GDSSpec",
                target="Block",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="has_interface",
                source="Block",
                target="Interface",
                cardinality=Cardinality.ONE_TO_ONE,
            ),
            ERDRelationship(
                name="has_port",
                source="Interface",
                target="Port",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="has_type",
                source="GDSSpec",
                target="TypeDef",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="has_entity",
                source="GDSSpec",
                target="Entity",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="has_variable",
                source="Entity",
                target="StateVariable",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="typed_by",
                source="StateVariable",
                target="TypeDef",
                cardinality=Cardinality.MANY_TO_ONE,
            ),
            ERDRelationship(
                name="has_wiring",
                source="GDSSpec",
                target="SpecWiring",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
            ERDRelationship(
                name="has_wire",
                source="SpecWiring",
                target="Wire",
                cardinality=Cardinality.ONE_TO_MANY,
            ),
        ],
    )

    _spec = compile_erd(_erd)
    _ir = compile_erd_to_system(_erd)
    _report = verify(_ir)
    _canonical = project_canonical(_spec)

    n_state_vars = len(_canonical.state_variables)
    mo.md(
        f"""
        **Entities:** {len(_erd.entities)} |
        **Relationships:** {len(_erd.relationships)} |
        **State variables (X):** {n_state_vars}

        **Canonical:** h = f (pure state, no external inputs)
        - Mechanism (f): {", ".join(_canonical.mechanism_blocks)}
        """
    )

    mo.mermaid(system_to_mermaid(_ir))
    return


@app.cell
def summary(mo):
    mo.md("""## Canonical Spectrum

| Diagram | dim(X) | dim(f) | dim(g) | Form | Character |
|---------|--------|--------|--------|------|-----------|
| Component | 0 | 0 | 6 | h = g | Stateless API composition |
| DFD | 4 | 4 | 7 | h = f . g | Full dynamical pipeline |
| ERD | 20 | 9 | 0 | h = f | Pure state (closed system) |

The three canonical forms span the full spectrum of GDS
dynamical character -- from stateless (games-like) through full
dynamics (control-like) to pure state (data model). This
validates that GDS's canonical decomposition h = f . g is
genuinely universal across diagram types.
""")
    return


if __name__ == "__main__":
    app.run()

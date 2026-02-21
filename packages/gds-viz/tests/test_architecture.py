"""Tests for View 3 — Architecture renderer."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds_viz.architecture import spec_to_mermaid


def _minimal_spec() -> GDSSpec:
    """Build a minimal spec with one block per role and one entity."""
    count_type = TypeDef(name="Count", python_type=float)

    sensor = BoundaryAction(
        name="Sensor",
        interface=Interface(forward_out=(port("Signal"),)),
    )
    decide = Policy(
        name="Decide",
        interface=Interface(
            forward_in=(port("Signal"),),
            forward_out=(port("Action"),),
        ),
    )
    update = Mechanism(
        name="Update",
        interface=Interface(forward_in=(port("Action"),)),
        updates=[("Pop", "count")],
    )

    pop_entity = Entity(
        name="Pop",
        variables={
            "count": StateVariable(name="count", typedef=count_type, symbol="N"),
        },
    )

    spec = GDSSpec(name="Test")
    spec.register_type(count_type)
    spec.register_entity(pop_entity)
    spec.register_block(sensor)
    spec.register_block(decide)
    spec.register_block(update)
    spec.register_wiring(
        SpecWiring(
            name="main",
            block_names=["Sensor", "Decide", "Update"],
            wires=[
                Wire(source="Sensor", target="Decide"),
                Wire(source="Decide", target="Update"),
            ],
        )
    )
    return spec


class TestArchitectureRoleGroups:
    def test_default_groups_by_role(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "flowchart TD" in out
        assert "Boundary (U)" in out
        assert "Policy (g)" in out
        assert "Mechanism (f)" in out

    def test_empty_role_omitted(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        # No control blocks registered
        assert "Control" not in out

    def test_boundary_block_has_stadium_shape(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "Sensor([Sensor])" in out

    def test_mechanism_block_has_double_bracket_shape(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "Update[[Update]]" in out

    def test_policy_block_has_rectangle_shape(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "Decide[Decide]" in out


class TestArchitectureTagGroups:
    def test_group_by_tag(self):
        spec = _minimal_spec()
        # Tag blocks with domain
        spec.blocks["Sensor"] = spec.blocks["Sensor"].with_tag("domain", "Input")
        spec.blocks["Decide"] = spec.blocks["Decide"].with_tag("domain", "Logic")
        spec.blocks["Update"] = spec.blocks["Update"].with_tag("domain", "State")

        out = spec_to_mermaid(spec, group_by="domain")
        assert "Input" in out
        assert "Logic" in out
        assert "State" in out

    def test_untagged_blocks_go_to_ungrouped(self):
        spec = _minimal_spec()
        # Only tag one block
        spec.blocks["Sensor"] = spec.blocks["Sensor"].with_tag("domain", "Input")

        out = spec_to_mermaid(spec, group_by="domain")
        assert "Ungrouped" in out
        assert "Input" in out


class TestArchitectureEntities:
    def test_entity_cylinders_rendered(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        # Cylinder shape with entity name (prefixed ID)
        assert 'entity_Pop[("Pop' in out
        assert "count" in out

    def test_entity_symbol_shown(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        # StateVariable has symbol="N"
        assert "count: N" in out

    def test_mechanism_to_entity_dotted_edges(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "Update -.-> entity_Pop" in out

    def test_entities_hidden_when_show_entities_false(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec, show_entities=False)
        # No cylinder nodes
        assert 'entity_Pop[("' not in out
        assert "-.-> entity_Pop" not in out


class TestArchitectureWires:
    def test_dependency_edges_rendered(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec)
        assert "Sensor --> Decide" in out or "Sensor --" in out

    def test_wires_hidden_when_show_wires_false(self):
        spec = _minimal_spec()
        out = spec_to_mermaid(spec, show_wires=False)
        # Dependency edges should not appear (entity edges may still appear)
        lines = out.split("\n")
        wire_lines = [line for line in lines if "Sensor" in line and "Decide" in line]
        assert len(wire_lines) == 0

    def test_wire_label_from_space(self):
        spec = _minimal_spec()
        # Add a space and reference it in wiring
        from gds.spaces import Space

        sig_space = Space(
            name="SignalSpace", fields={"val": TypeDef(name="Count", python_type=float)}
        )
        spec.register_space(sig_space)
        # Re-register wiring with space label
        spec.wirings.clear()
        spec.register_wiring(
            SpecWiring(
                name="main",
                block_names=["Sensor", "Decide", "Update"],
                wires=[
                    Wire(source="Sensor", target="Decide", space="SignalSpace"),
                    Wire(source="Decide", target="Update"),
                ],
            )
        )
        out = spec_to_mermaid(spec)
        assert "SignalSpace" in out


class TestArchitectureIntegration:
    def test_sir_epidemic(self):
        sir = __import__("pytest").importorskip("sir_epidemic")
        spec = sir.model.build_spec()
        out = spec_to_mermaid(spec)

        assert "flowchart TD" in out
        # 5 blocks across roles
        assert "Boundary (U)" in out
        assert "Policy (g)" in out
        assert "Mechanism (f)" in out
        # 3 entities
        assert "Susceptible" in out
        assert "Infected" in out
        assert "Recovered" in out

    def test_prisoners_dilemma(self):
        pd = __import__("pytest").importorskip("prisoners_dilemma")
        spec = pd.model.build_spec()
        out = spec_to_mermaid(spec)

        assert "flowchart TD" in out
        assert "Alice_Decision" in out or "Alice Decision" in out
        assert "Bob_Decision" in out or "Bob Decision" in out
        # 3 entities (Alice, Bob, Game)
        assert "Alice" in out
        assert "Bob" in out

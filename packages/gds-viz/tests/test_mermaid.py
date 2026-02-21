"""Tests for Mermaid visualization utilities."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.ir.models import (
    BlockIR,
    CompositionType,
    FlowDirection,
    HierarchyNodeIR,
    SystemIR,
    WiringIR,
)
from gds.types.interface import Interface, port
from gds_viz import block_to_mermaid, system_to_mermaid


class TestSystemToMermaid:
    def test_flat_diagram_has_flowchart_header(self):
        system = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A"), BlockIR(name="B")],
        )
        mermaid = system_to_mermaid(system)
        assert "flowchart TD" in mermaid

    def test_renders_blocks(self):
        system = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="Block A", signature=("Input", "Output", "", "")),
                BlockIR(name="Block B", signature=("Output", "Result", "", "")),
            ],
        )
        mermaid = system_to_mermaid(system)
        assert "Block_A[Block A]" in mermaid
        assert "Block_B[Block B]" in mermaid

    def test_renders_boundary_action_with_stadium_shape(self):
        system = SystemIR(
            name="Test",
            blocks=[BlockIR(name="Sensor", signature=("", "Temperature", "", ""))],
        )
        mermaid = system_to_mermaid(system)
        assert "Sensor([Sensor])" in mermaid

    def test_renders_terminal_mechanism_with_double_brackets(self):
        system = SystemIR(
            name="Test",
            blocks=[BlockIR(name="Update", signature=("Delta", "", "", ""))],
        )
        mermaid = system_to_mermaid(system)
        assert "Update[[Update]]" in mermaid

    def test_renders_covariant_wiring(self):
        system = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "X", "", "")),
                BlockIR(name="B", signature=("X", "", "", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="signal",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        mermaid = system_to_mermaid(system)
        assert "A --signal--> B" in mermaid

    def test_renders_contravariant_wiring_as_backward_arrow(self):
        system = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A"),
                BlockIR(name="B"),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="cost",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ],
        )
        mermaid = system_to_mermaid(system)
        assert "B <--cost--- A" in mermaid

    def test_renders_feedback_wiring_as_thick_arrow(self):
        system = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="Controller"),
                BlockIR(name="Plant"),
            ],
            wirings=[
                WiringIR(
                    source="Plant",
                    target="Controller",
                    label="feedback",
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                )
            ],
        )
        mermaid = system_to_mermaid(system)
        assert "Plant ==feedback==> Controller" in mermaid

    def test_renders_temporal_wiring_as_dashed_arrow(self):
        system = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="Update"),
                BlockIR(name="Compute"),
            ],
            wirings=[
                WiringIR(
                    source="Update",
                    target="Compute",
                    label="state",
                    direction=FlowDirection.COVARIANT,
                    is_temporal=True,
                )
            ],
        )
        mermaid = system_to_mermaid(system)
        assert "Update -.state..-> Compute" in mermaid

    def test_sanitizes_block_names_with_spaces(self):
        system = SystemIR(
            name="Test",
            blocks=[BlockIR(name="Temperature Sensor")],
        )
        mermaid = system_to_mermaid(system)
        assert "Temperature_Sensor" in mermaid
        # Original name appears in label
        assert "Temperature Sensor" in mermaid

    def test_hierarchy_mode_creates_subgraphs(self):
        hierarchy = HierarchyNodeIR(
            id="root",
            name="Pipeline",
            composition_type=CompositionType.SEQUENTIAL,
            children=[
                HierarchyNodeIR(id="leaf_a", name="A", block_name="A"),
                HierarchyNodeIR(id="leaf_b", name="B", block_name="B"),
            ],
        )
        system = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A"), BlockIR(name="B")],
            hierarchy=hierarchy,
        )
        mermaid = system_to_mermaid(system, show_hierarchy=True)
        assert "subgraph" in mermaid
        assert "Sequential (>>)" in mermaid


class TestBlockToMermaid:
    def test_converts_simple_stack(self):
        observe = BoundaryAction(
            name="Observe",
            interface=Interface(forward_out=(port("Signal"),)),
        )
        decide = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Action"),),
            ),
        )
        pipeline = observe >> decide
        mermaid = block_to_mermaid(pipeline)
        assert "flowchart TD" in mermaid
        assert "Observe" in mermaid
        assert "Decide" in mermaid

    def test_converts_parallel_composition(self):
        a = Mechanism(
            name="Update A",
            interface=Interface(forward_in=(port("Delta A"),)),
            updates=[("Entity A", "state")],
        )
        b = Mechanism(
            name="Update B",
            interface=Interface(forward_in=(port("Delta B"),)),
            updates=[("Entity B", "state")],
        )
        parallel = a | b
        mermaid = block_to_mermaid(parallel)
        assert "Update_A" in mermaid
        assert "Update_B" in mermaid

    def test_uses_block_name_as_system_name(self):
        block = BoundaryAction(
            name="Test Block",
            interface=Interface(forward_out=(port("Out"),)),
        )
        # Compile happens internally
        mermaid = block_to_mermaid(block)
        assert "flowchart TD" in mermaid


class TestFullExample:
    def test_sir_epidemic_diagram(self):
        from sir_epidemic.model import build_system

        system = build_system()
        mermaid = system_to_mermaid(system)

        # Check key elements
        assert "flowchart TD" in mermaid
        assert "Contact_Process([Contact Process])" in mermaid  # BoundaryAction
        assert "Infection_Policy[Infection Policy]" in mermaid  # Policy
        assert (
            "Update_Susceptible[[Update Susceptible]]" in mermaid
        )  # Terminal Mechanism

        # Check wirings
        assert "-->" in mermaid  # covariant arrows

    def test_thermostat_with_feedback(self):
        from thermostat.model import build_system

        system = build_system()
        mermaid = system_to_mermaid(system)

        # Check feedback wiring
        feedback_wirings = [w for w in system.wirings if w.is_feedback]
        assert len(feedback_wirings) == 1
        assert "==" in mermaid  # thick arrow for feedback

    def test_lotka_volterra_with_temporal_loop(self):
        from lotka_volterra.model import build_system

        system = build_system()
        mermaid = system_to_mermaid(system)

        # Check temporal wiring
        temporal_wirings = [w for w in system.wirings if w.is_temporal]
        assert len(temporal_wirings) == 2
        assert "-." in mermaid  # dashed arrow for temporal

    def test_prisoners_dilemma_complex(self):
        from prisoners_dilemma.model import build_system

        system = build_system()
        mermaid = system_to_mermaid(system)

        # Should have 6 blocks
        assert len(system.blocks) == 6
        assert "Alice_Decision" in mermaid
        assert "Bob_Decision" in mermaid
        assert "Payoff_Realization" in mermaid

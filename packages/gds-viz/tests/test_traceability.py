"""Tests for Views 5 & 6 — Parameter influence and traceability."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds_viz.traceability import params_to_mermaid, trace_to_mermaid


def _param_spec() -> GDSSpec:
    """Spec with parameters, blocks, and entities for traceability tests."""
    rate_type = TypeDef(name="Rate", python_type=float)
    count_type = TypeDef(name="Count", python_type=float)

    sensor = BoundaryAction(
        name="Sensor",
        interface=Interface(forward_out=(port("Signal"),)),
        params_used=["threshold"],
    )
    decide = Policy(
        name="Decide",
        interface=Interface(
            forward_in=(port("Signal"),),
            forward_out=(port("Action"),),
        ),
        params_used=["rate", "threshold"],
    )
    update = Mechanism(
        name="Update",
        interface=Interface(forward_in=(port("Action"),)),
        updates=[("Pop", "count")],
    )

    pop = Entity(
        name="Pop",
        variables={
            "count": StateVariable(name="count", typedef=count_type, symbol="N")
        },
    )

    spec = GDSSpec(name="Test")
    spec.register_type(rate_type)
    spec.register_type(count_type)
    spec.register_entity(pop)
    spec.register_block(sensor)
    spec.register_block(decide)
    spec.register_block(update)
    spec.register_parameter("rate", rate_type)
    spec.register_parameter("threshold", rate_type)
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


class TestParamInfluence:
    def test_renders_parameter_nodes(self):
        spec = _param_spec()
        out = params_to_mermaid(spec)
        assert "flowchart LR" in out
        assert 'param_rate{{"rate"}}' in out
        assert 'param_threshold{{"threshold"}}' in out

    def test_param_to_block_edges(self):
        spec = _param_spec()
        out = params_to_mermaid(spec)
        assert "param_rate -.-> Decide" in out
        assert "param_threshold -.-> Sensor" in out
        assert "param_threshold -.-> Decide" in out

    def test_block_to_entity_edges(self):
        spec = _param_spec()
        out = params_to_mermaid(spec)
        assert "Update -.-> entity_Pop" in out

    def test_block_dependency_edges(self):
        spec = _param_spec()
        out = params_to_mermaid(spec)
        assert "Sensor --> Decide" in out
        assert "Decide --> Update" in out

    def test_entity_node_rendered(self):
        spec = _param_spec()
        out = params_to_mermaid(spec)
        assert 'entity_Pop[("Pop' in out
        assert "N" in out

    def test_no_params_shows_message(self):
        spec = GDSSpec(name="Empty")
        spec.register_block(
            BoundaryAction(name="B", interface=Interface(forward_out=(port("X"),)))
        )
        out = params_to_mermaid(spec)
        assert "No parameters defined" in out

    def test_sir_integration(self):
        from sir_epidemic.model import build_spec

        spec = build_spec()
        out = params_to_mermaid(spec)
        assert "param_beta" in out
        assert "param_gamma" in out
        assert "param_contact_rate" in out
        assert "entity_Susceptible" in out
        assert "entity_Infected" in out
        assert "entity_Recovered" in out

    def test_pd_no_params(self):
        from prisoners_dilemma.model import build_spec

        spec = build_spec()
        out = params_to_mermaid(spec)
        assert "No parameters defined" in out


class TestTraceability:
    def test_renders_target_node(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert 'target(["Pop.count (N)"])' in out

    def test_direct_mechanism_thick_edge(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert "Update ==> target" in out

    def test_affecting_blocks_included(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert "Sensor[Sensor]" in out
        assert "Decide[Decide]" in out
        assert "Update[Update]" in out

    def test_parameters_shown(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert 'param_rate{{"rate"}}' in out
        assert 'param_threshold{{"threshold"}}' in out

    def test_param_to_block_edges(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert "param_rate -.-> Decide" in out
        assert "param_threshold -.-> Sensor" in out

    def test_dependency_chain_edges(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert "Sensor --> Decide" in out
        assert "Decide --> Update" in out

    def test_right_to_left_layout(self):
        spec = _param_spec()
        out = trace_to_mermaid(spec, "Pop", "count")
        assert "flowchart RL" in out

    def test_sir_trace_integration(self):
        from sir_epidemic.model import build_spec

        spec = build_spec()
        out = trace_to_mermaid(spec, "Susceptible", "count")
        assert "Update_Susceptible ==> target" in out
        assert "Contact_Process" in out
        assert "Infection_Policy" in out
        assert "param_beta" in out

    def test_thermostat_trace_integration(self):
        from thermostat.model import build_spec

        spec = build_spec()
        out = trace_to_mermaid(spec, "Room", "temperature")
        assert "Update_Room ==> target" in out
        assert "PID_Controller" in out
        assert "param_setpoint" in out
        assert "param_Kp" in out

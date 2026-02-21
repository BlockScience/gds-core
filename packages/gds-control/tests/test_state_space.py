"""State-space correspondence tests: (A,B,C,D) ↔ (X,U,g,f).

Validates the structural mapping between classical control state-space form
and GDS canonical decomposition.
"""

import pytest

from gds.blocks.composition import StackComposition, Wiring
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port

from gds_control.dsl.compile import (
    ControlSpace,
    ControlType,
    MeasurementSpace,
    MeasurementType,
    ReferenceSpace,
    ReferenceType,
    StateSpace,
    StateType,
    compile_model,
    compile_to_system,
)
from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.model import ControlModel


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def double_integrator_model():
    """Double integrator: 2 states, 1 input, 2 sensors, 1 controller."""
    return ControlModel(
        name="Double Integrator",
        states=[
            State(name="position", initial=0.0),
            State(name="velocity", initial=0.0),
        ],
        inputs=[Input(name="force")],
        sensors=[
            Sensor(name="pos_sensor", observes=["position"]),
            Sensor(name="vel_sensor", observes=["velocity"]),
        ],
        controllers=[
            Controller(
                name="PD",
                reads=["pos_sensor", "vel_sensor", "force"],
                drives=["position", "velocity"],
            ),
        ],
    )


@pytest.fixture
def dsl_spec(double_integrator_model):
    return compile_model(double_integrator_model)


@pytest.fixture
def dsl_canonical(dsl_spec):
    return project_canonical(dsl_spec)


@pytest.fixture
def dsl_ir(double_integrator_model):
    return compile_to_system(double_integrator_model)


# ── TestStateSpaceCorrespondence ────────────────────────────


class TestStateSpaceCorrespondence:
    """Verify (A,B,C,D) ↔ (X,U,g,f) structural mapping."""

    def test_state_dim_matches_x(self, dsl_canonical):
        """|X| = 2 → dim(x) = rows(A)."""
        assert len(dsl_canonical.state_variables) == 2

    def test_input_dim_matches_u(self, dsl_canonical):
        """|U| = 1 → dim(u) = cols(B)."""
        assert len(dsl_canonical.input_ports) == 1

    def test_sensors_in_policy(self, dsl_canonical):
        """Sensors are in policy_blocks → C is in g."""
        assert "pos_sensor" in dsl_canonical.policy_blocks
        assert "vel_sensor" in dsl_canonical.policy_blocks

    def test_controller_in_policy(self, dsl_canonical):
        """Controller is in policy_blocks → control law is in g."""
        assert "PD" in dsl_canonical.policy_blocks

    def test_dynamics_are_mechanisms(self, dsl_canonical):
        """|f| = 2 dynamics mechanisms → state transition."""
        assert len(dsl_canonical.mechanism_blocks) == 2
        assert "position Dynamics" in dsl_canonical.mechanism_blocks
        assert "velocity Dynamics" in dsl_canonical.mechanism_blocks

    def test_no_control_blocks(self, dsl_canonical):
        """ControlAction unused → no control_blocks."""
        assert len(dsl_canonical.control_blocks) == 0

    def test_update_map(self, dsl_canonical):
        """Each mechanism updates one state."""
        update_dict = {name: targets for name, targets in dsl_canonical.update_map}
        assert ("position", "value") in update_dict["position Dynamics"]
        assert ("velocity", "value") in update_dict["velocity Dynamics"]

    def test_decision_ports(self, dsl_canonical):
        """Decision space D covers sensor + controller outputs."""
        port_names = {p_name for _, p_name in dsl_canonical.decision_ports}
        assert "pos_sensor Measurement" in port_names
        assert "vel_sensor Measurement" in port_names
        assert "PD Control" in port_names


# ── TestCrossBuilt ──────────────────────────────────────────


class TestCrossBuilt:
    """Same model built with raw GDS primitives — structural equivalence."""

    @pytest.fixture
    def hand_spec(self):
        spec = GDSSpec(name="Double Integrator")

        # Types & spaces
        spec.collect(StateType, ReferenceType, MeasurementType, ControlType)
        spec.collect(StateSpace, ReferenceSpace, MeasurementSpace, ControlSpace)

        # Entities
        spec.register_entity(
            Entity(
                name="position",
                variables={
                    "value": StateVariable(
                        name="value",
                        typedef=StateType,
                        description="State variable for position",
                    ),
                },
                description="State entity for 'position'",
            )
        )
        spec.register_entity(
            Entity(
                name="velocity",
                variables={
                    "value": StateVariable(
                        name="value",
                        typedef=StateType,
                        description="State variable for velocity",
                    ),
                },
                description="State entity for 'velocity'",
            )
        )

        # Blocks — input
        spec.register_block(
            BoundaryAction(
                name="force",
                interface=Interface(
                    forward_out=(port("force Reference"),),
                ),
            )
        )

        # Blocks — sensors
        spec.register_block(
            Policy(
                name="pos_sensor",
                interface=Interface(
                    forward_in=(port("position State"),),
                    forward_out=(port("pos_sensor Measurement"),),
                ),
            )
        )
        spec.register_block(
            Policy(
                name="vel_sensor",
                interface=Interface(
                    forward_in=(port("velocity State"),),
                    forward_out=(port("vel_sensor Measurement"),),
                ),
            )
        )

        # Blocks — controller
        spec.register_block(
            Policy(
                name="PD",
                interface=Interface(
                    forward_in=(
                        port("pos_sensor Measurement"),
                        port("vel_sensor Measurement"),
                        port("force Reference"),
                    ),
                    forward_out=(port("PD Control"),),
                ),
            )
        )

        # Blocks — dynamics mechanisms
        spec.register_block(
            Mechanism(
                name="position Dynamics",
                interface=Interface(
                    forward_in=(port("PD Control"),),
                    forward_out=(port("position State"),),
                ),
                updates=[("position", "value")],
            )
        )
        spec.register_block(
            Mechanism(
                name="velocity Dynamics",
                interface=Interface(
                    forward_in=(port("PD Control"),),
                    forward_out=(port("velocity State"),),
                ),
                updates=[("velocity", "value")],
            )
        )

        # Wirings
        spec.register_wiring(
            SpecWiring(
                name="Double Integrator Wiring",
                block_names=[b for b in spec.blocks],
                wires=[
                    Wire(
                        source="PD",
                        target="position Dynamics",
                        space="ControlSpace",
                    ),
                    Wire(
                        source="PD",
                        target="velocity Dynamics",
                        space="ControlSpace",
                    ),
                ],
                description="Auto-generated wiring for control model 'Double Integrator'",
            )
        )

        return spec

    @pytest.fixture
    def hand_canonical(self, hand_spec):
        return project_canonical(hand_spec)

    @pytest.fixture
    def hand_ir(self, hand_spec):
        blocks = hand_spec.blocks

        # Tier 1: input + sensors in parallel
        tier1 = blocks["force"] | blocks["pos_sensor"] | blocks["vel_sensor"]

        # Tier 2: controller
        tier2_block = blocks["PD"]

        # Tier 1 → Tier 2 wirings
        t1_blocks = [blocks["force"], blocks["pos_sensor"], blocks["vel_sensor"]]
        t2_blocks = [blocks["PD"]]
        t1_to_t2_wirings = []
        for fb in t1_blocks:
            for out_port in fb.interface.forward_out:
                for tb in t2_blocks:
                    for in_port in tb.interface.forward_in:
                        if out_port.type_tokens & in_port.type_tokens:
                            t1_to_t2_wirings.append(
                                Wiring(
                                    source_block=fb.name,
                                    source_port=out_port.name,
                                    target_block=tb.name,
                                    target_port=in_port.name,
                                )
                            )

        root = StackComposition(
            name=f"{tier1.name} >> {tier2_block.name}",
            first=tier1,
            second=tier2_block,
            wiring=t1_to_t2_wirings,
        )

        # Tier 3: dynamics in parallel
        tier3 = blocks["position Dynamics"] | blocks["velocity Dynamics"]

        # Tier 2 → Tier 3 wirings
        t3_blocks = [blocks["position Dynamics"], blocks["velocity Dynamics"]]
        t2_to_t3_wirings = []
        for out_port in tier2_block.interface.forward_out:
            for tb in t3_blocks:
                for in_port in tb.interface.forward_in:
                    if out_port.type_tokens & in_port.type_tokens:
                        t2_to_t3_wirings.append(
                            Wiring(
                                source_block=tier2_block.name,
                                source_port=out_port.name,
                                target_block=tb.name,
                                target_port=in_port.name,
                            )
                        )

        root = StackComposition(
            name=f"{root.name} >> {tier3.name}",
            first=root,
            second=tier3,
            wiring=t2_to_t3_wirings,
        )

        # Temporal loop
        temporal_wirings = [
            Wiring(
                source_block="position Dynamics",
                source_port="position State",
                target_block="pos_sensor",
                target_port="position State",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="velocity Dynamics",
                source_port="velocity State",
                target_block="vel_sensor",
                target_port="velocity State",
                direction=FlowDirection.COVARIANT,
            ),
        ]
        root = root.loop(temporal_wirings)
        return compile_system("Double Integrator", root)

    # ── Spec equivalence ────────────────────────────────────

    def test_entity_names_match(self, dsl_spec, hand_spec):
        assert set(dsl_spec.entities.keys()) == set(hand_spec.entities.keys())

    def test_block_names_match(self, dsl_spec, hand_spec):
        assert set(dsl_spec.blocks.keys()) == set(hand_spec.blocks.keys())

    def test_block_role_types_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.blocks:
            assert isinstance(hand_spec.blocks[name], type(dsl_spec.blocks[name]))

    def test_block_forward_in_ports_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.blocks:
            dsl_ports = {p.name for p in dsl_spec.blocks[name].interface.forward_in}
            hand_ports = {p.name for p in hand_spec.blocks[name].interface.forward_in}
            assert dsl_ports == hand_ports, f"Block {name!r} forward_in mismatch"

    def test_block_forward_out_ports_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.blocks:
            dsl_ports = {p.name for p in dsl_spec.blocks[name].interface.forward_out}
            hand_ports = {p.name for p in hand_spec.blocks[name].interface.forward_out}
            assert dsl_ports == hand_ports, f"Block {name!r} forward_out mismatch"

    def test_mechanism_updates_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.blocks:
            dsl_block = dsl_spec.blocks[name]
            hand_block = hand_spec.blocks[name]
            if isinstance(dsl_block, Mechanism):
                assert set(map(tuple, dsl_block.updates)) == set(
                    map(tuple, hand_block.updates)
                )

    # ── Canonical equivalence ───────────────────────────────

    def test_state_variables_match(self, dsl_canonical, hand_canonical):
        assert set(dsl_canonical.state_variables) == set(hand_canonical.state_variables)

    def test_boundary_blocks_match(self, dsl_canonical, hand_canonical):
        assert set(dsl_canonical.boundary_blocks) == set(hand_canonical.boundary_blocks)

    def test_policy_blocks_match(self, dsl_canonical, hand_canonical):
        assert set(dsl_canonical.policy_blocks) == set(hand_canonical.policy_blocks)

    def test_mechanism_blocks_match(self, dsl_canonical, hand_canonical):
        assert set(dsl_canonical.mechanism_blocks) == set(
            hand_canonical.mechanism_blocks
        )

    def test_update_map_match(self, dsl_canonical, hand_canonical):
        dsl_map = {name: targets for name, targets in dsl_canonical.update_map}
        hand_map = {name: targets for name, targets in hand_canonical.update_map}
        assert dsl_map == hand_map

    # ── SystemIR equivalence ────────────────────────────────

    def test_ir_block_count(self, dsl_ir, hand_ir):
        assert len(dsl_ir.blocks) == len(hand_ir.blocks)

    def test_ir_block_names(self, dsl_ir, hand_ir):
        assert {b.name for b in dsl_ir.blocks} == {b.name for b in hand_ir.blocks}

    def test_ir_wiring_count(self, dsl_ir, hand_ir):
        assert len(dsl_ir.wirings) == len(hand_ir.wirings)

    def test_ir_temporal_count(self, dsl_ir, hand_ir):
        dsl_temporal = [w for w in dsl_ir.wirings if w.is_temporal]
        hand_temporal = [w for w in hand_ir.wirings if w.is_temporal]
        assert len(dsl_temporal) == len(hand_temporal)

    def test_ir_temporal_pairs(self, dsl_ir, hand_ir):
        dsl_pairs = {(w.source, w.target) for w in dsl_ir.wirings if w.is_temporal}
        hand_pairs = {(w.source, w.target) for w in hand_ir.wirings if w.is_temporal}
        assert dsl_pairs == hand_pairs


# ── TestSISO ────────────────────────────────────────────────


class TestSISO:
    @pytest.fixture
    def model(self):
        return ControlModel(
            name="SISO",
            states=[State(name="x")],
            inputs=[Input(name="r")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )

    def test_canonical_invariants(self, model):
        spec = compile_model(model)
        c = project_canonical(spec)
        assert len(c.state_variables) == 1
        assert len(c.mechanism_blocks) == 1
        assert len(c.boundary_blocks) == 1
        assert len(c.policy_blocks) == 2
        assert len(c.control_blocks) == 0


# ── TestMIMO ────────────────────────────────────────────────


class TestMIMO:
    @pytest.fixture
    def model(self):
        return ControlModel(
            name="MIMO",
            states=[State(name="x1"), State(name="x2"), State(name="x3")],
            inputs=[Input(name="r1"), Input(name="r2")],
            sensors=[
                Sensor(name="y1", observes=["x1", "x2"]),
                Sensor(name="y2", observes=["x2", "x3"]),
            ],
            controllers=[
                Controller(name="K1", reads=["y1", "r1"], drives=["x1", "x2"]),
                Controller(name="K2", reads=["y2", "r2"], drives=["x2", "x3"]),
            ],
        )

    def test_canonical_invariants(self, model):
        spec = compile_model(model)
        c = project_canonical(spec)
        assert len(c.state_variables) == 3
        assert len(c.mechanism_blocks) == 3
        assert len(c.boundary_blocks) == 2
        assert len(c.policy_blocks) == 4
        assert len(c.control_blocks) == 0


# ── TestOpenLoop ────────────────────────────────────────────


class TestOpenLoop:
    @pytest.fixture
    def model(self):
        return ControlModel(
            name="Open Loop",
            states=[State(name="x")],
            inputs=[Input(name="u")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["u"], drives=["x"])],
        )

    def test_canonical_invariants(self, model):
        spec = compile_model(model)
        c = project_canonical(spec)
        assert len(c.state_variables) == 1
        assert len(c.mechanism_blocks) == 1
        assert len(c.boundary_blocks) == 1
        assert len(c.policy_blocks) == 2
        assert len(c.control_blocks) == 0


# ── TestCanonicalInvariants ─────────────────────────────────


class TestCanonicalInvariants:
    """Parametric invariants across model archetypes."""

    @pytest.fixture(
        params=[
            # (name, n_states, n_inputs, n_sensors, n_controllers)
            ("tiny", 1, 1, 1, 1),
            ("medium", 3, 2, 2, 2),
            ("large", 5, 3, 4, 3),
        ]
    )
    def archetype(self, request):
        name, n_s, n_i, n_sens, n_ctrl = request.param
        states = [State(name=f"x{i}") for i in range(n_s)]
        inputs = [Input(name=f"r{i}") for i in range(n_i)]
        sensors = [
            Sensor(name=f"y{i}", observes=[f"x{i % n_s}"]) for i in range(n_sens)
        ]
        controllers = [
            Controller(
                name=f"K{i}",
                reads=[f"y{i % n_sens}", f"r{i % n_i}"],
                drives=[f"x{i % n_s}"],
            )
            for i in range(n_ctrl)
        ]
        model = ControlModel(
            name=name,
            states=states,
            inputs=inputs,
            sensors=sensors,
            controllers=controllers,
        )
        spec = compile_model(model)
        canonical = project_canonical(spec)
        return model, spec, canonical

    def test_state_count(self, archetype):
        model, _, canonical = archetype
        assert len(canonical.state_variables) == len(model.states)

    def test_mechanism_count(self, archetype):
        model, _, canonical = archetype
        assert len(canonical.mechanism_blocks) == len(model.states)

    def test_boundary_count(self, archetype):
        model, _, canonical = archetype
        assert len(canonical.boundary_blocks) == len(model.inputs)

    def test_policy_count(self, archetype):
        model, _, canonical = archetype
        assert len(canonical.policy_blocks) == len(model.sensors) + len(
            model.controllers
        )

    def test_decision_port_count(self, archetype):
        model, _, canonical = archetype
        assert len(canonical.decision_ports) == len(model.sensors) + len(
            model.controllers
        )

    def test_no_control_blocks(self, archetype):
        _, _, canonical = archetype
        assert len(canonical.control_blocks) == 0

    def test_role_partition_complete(self, archetype):
        _, spec, canonical = archetype
        all_canonical = (
            set(canonical.boundary_blocks)
            | set(canonical.policy_blocks)
            | set(canonical.mechanism_blocks)
            | set(canonical.control_blocks)
        )
        assert all_canonical == set(spec.blocks.keys())

    def test_role_partition_disjoint(self, archetype):
        _, _, canonical = archetype
        sets = [
            set(canonical.boundary_blocks),
            set(canonical.policy_blocks),
            set(canonical.mechanism_blocks),
            set(canonical.control_blocks),
        ]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i] & sets[j] == set()

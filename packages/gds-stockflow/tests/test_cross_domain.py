"""Cross-domain comparison: DSL-compiled vs hand-built GDSSpec.

Builds a predator-prey system two ways:
  Path A — StockFlowModel DSL → compile_model() → GDSSpec
  Path B — Hand-built GDSSpec using raw GDS primitives

Then asserts structural equivalence at three levels:
  1. GDSSpec (entities, blocks, ports, wirings, parameters)
  2. CanonicalGDS (state variables, role classification, update map)
  3. SystemIR (block count, wiring count, temporal wirings)
"""

import pytest

from gds.blocks.composition import StackComposition, Wiring
from gds.blocks.roles import Mechanism, Policy
from gds.canonical import project_canonical
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port

from stockflow.dsl.compile import (
    LevelSpace,
    LevelType,
    RateSpace,
    RateType,
    SignalSpace,
    SignalType,
    UnconstrainedLevelSpace,
    UnconstrainedLevelType,
    compile_model,
    compile_to_system,
)
from stockflow.dsl.elements import Auxiliary, Flow, Stock
from stockflow.dsl.model import StockFlowModel


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def predator_prey_model():
    """The StockFlowModel DSL declaration."""
    return StockFlowModel(
        name="Predator Prey",
        stocks=[
            Stock(name="Prey", initial=100.0),
            Stock(name="Predator", initial=20.0),
        ],
        flows=[
            Flow(name="Prey Births", target="Prey"),
            Flow(name="Prey Deaths", source="Prey"),
            Flow(name="Predator Births", target="Predator"),
            Flow(name="Predator Deaths", source="Predator"),
        ],
        auxiliaries=[
            Auxiliary(name="Prey Growth", inputs=["Prey"]),
            Auxiliary(name="Predation", inputs=["Prey", "Predator"]),
            Auxiliary(name="Predator Growth", inputs=["Predator", "Prey"]),
            Auxiliary(name="Predator Decline", inputs=["Predator"]),
        ],
    )


@pytest.fixture
def dsl_spec(predator_prey_model):
    """Path A: DSL-compiled GDSSpec."""
    return compile_model(predator_prey_model)


@pytest.fixture
def hand_spec():
    """Path B: Hand-built GDSSpec using raw GDS primitives.

    Mirrors the exact structure the compiler produces: same block names,
    port names, role types, entities, wirings, and type/space definitions.
    """
    spec = GDSSpec(name="Predator Prey")

    # 1. Types — reuse compiler's TypeDef instances for identity
    spec.collect(LevelType, UnconstrainedLevelType, RateType, SignalType)

    # 2. Spaces — reuse compiler's Space instances
    spec.collect(LevelSpace, UnconstrainedLevelSpace, RateSpace, SignalSpace)

    # 3. Entities
    spec.register_entity(
        Entity(
            name="Prey",
            variables={
                "level": StateVariable(
                    name="level",
                    typedef=LevelType,
                    description="Accumulated level of Prey",
                ),
            },
            description="State entity for stock 'Prey'",
        )
    )
    spec.register_entity(
        Entity(
            name="Predator",
            variables={
                "level": StateVariable(
                    name="level",
                    typedef=LevelType,
                    description="Accumulated level of Predator",
                ),
            },
            description="State entity for stock 'Predator'",
        )
    )

    # 4. Blocks — auxiliaries (Policy)
    spec.register_block(
        Policy(
            name="Prey Growth",
            interface=Interface(
                forward_in=(port("Prey Level"),),
                forward_out=(port("Prey Growth Signal"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Predation",
            interface=Interface(
                forward_in=(port("Prey Level"), port("Predator Level")),
                forward_out=(port("Predation Signal"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Predator Growth",
            interface=Interface(
                forward_in=(port("Predator Level"), port("Prey Level")),
                forward_out=(port("Predator Growth Signal"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Predator Decline",
            interface=Interface(
                forward_in=(port("Predator Level"),),
                forward_out=(port("Predator Decline Signal"),),
            ),
        )
    )

    # 4b. Blocks — flows (Policy, no forward_in)
    spec.register_block(
        Policy(
            name="Prey Births",
            interface=Interface(
                forward_out=(port("Prey Births Rate"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Prey Deaths",
            interface=Interface(
                forward_out=(port("Prey Deaths Rate"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Predator Births",
            interface=Interface(
                forward_out=(port("Predator Births Rate"),),
            ),
        )
    )
    spec.register_block(
        Policy(
            name="Predator Deaths",
            interface=Interface(
                forward_out=(port("Predator Deaths Rate"),),
            ),
        )
    )

    # 4c. Blocks — stock mechanisms
    spec.register_block(
        Mechanism(
            name="Prey Accumulation",
            interface=Interface(
                forward_in=(port("Prey Births Rate"), port("Prey Deaths Rate")),
                forward_out=(port("Prey Level"),),
            ),
            updates=[("Prey", "level")],
        )
    )
    spec.register_block(
        Mechanism(
            name="Predator Accumulation",
            interface=Interface(
                forward_in=(
                    port("Predator Births Rate"),
                    port("Predator Deaths Rate"),
                ),
                forward_out=(port("Predator Level"),),
            ),
            updates=[("Predator", "level")],
        )
    )

    # 5. Wirings
    spec.register_wiring(
        SpecWiring(
            name="Predator Prey Wiring",
            block_names=[b for b in spec.blocks],
            wires=[
                Wire(
                    source="Prey Births",
                    target="Prey Accumulation",
                    space="RateSpace",
                ),
                Wire(
                    source="Prey Deaths",
                    target="Prey Accumulation",
                    space="RateSpace",
                ),
                Wire(
                    source="Predator Births",
                    target="Predator Accumulation",
                    space="RateSpace",
                ),
                Wire(
                    source="Predator Deaths",
                    target="Predator Accumulation",
                    space="RateSpace",
                ),
            ],
            description=("Auto-generated wiring for stock-flow model 'Predator Prey'"),
        )
    )

    # 6. No parameters (no converters in this model)

    return spec


@pytest.fixture
def dsl_ir(predator_prey_model):
    """Path A: DSL-compiled SystemIR."""
    return compile_to_system(predator_prey_model)


@pytest.fixture
def hand_ir(hand_spec):
    """Path B: Hand-built composition tree → SystemIR.

    Mirrors the compiler's 3-tier parallel-sequential structure with
    temporal loop, built from the hand_spec blocks.
    """
    blocks = hand_spec.blocks

    # Tier 1: auxiliaries in parallel
    aux_names = ["Prey Growth", "Predation", "Predator Growth", "Predator Decline"]
    aux_blocks = [blocks[n] for n in aux_names]
    aux_tier = aux_blocks[0]
    for b in aux_blocks[1:]:
        aux_tier = aux_tier | b

    # Tier 2: flows in parallel
    flow_names = ["Prey Births", "Prey Deaths", "Predator Births", "Predator Deaths"]
    flow_blocks = [blocks[n] for n in flow_names]
    flow_tier = flow_blocks[0]
    for b in flow_blocks[1:]:
        flow_tier = flow_tier | b

    # Tier 3: mechanisms in parallel
    mech_names = ["Prey Accumulation", "Predator Accumulation"]
    mech_blocks = [blocks[n] for n in mech_names]
    mech_tier = mech_blocks[0]
    for b in mech_blocks[1:]:
        mech_tier = mech_tier | b

    # Sequential: aux >> flow (no wirings — flows have no forward_in)
    root = aux_tier >> flow_tier

    # Sequential: (aux >> flow) >> mech (explicit wirings for rate ports)
    flow_to_mech_wirings = []
    for fb in flow_blocks:
        out_port = fb.interface.forward_out[0]
        for mb in mech_blocks:
            for in_port in mb.interface.forward_in:
                if out_port.type_tokens & in_port.type_tokens:
                    flow_to_mech_wirings.append(
                        Wiring(
                            source_block=fb.name,
                            source_port=out_port.name,
                            target_block=mb.name,
                            target_port=in_port.name,
                        )
                    )

    root = StackComposition(
        name=f"{root.name} >> {mech_tier.name}",
        first=root,
        second=mech_tier,
        wiring=flow_to_mech_wirings,
    )

    # Temporal loop: stock levels → auxiliaries at t+1
    temporal_wirings = [
        # Prey Level → Prey Growth, Predation, Predator Growth
        Wiring(
            source_block="Prey Accumulation",
            source_port="Prey Level",
            target_block="Prey Growth",
            target_port="Prey Level",
            direction=FlowDirection.COVARIANT,
        ),
        Wiring(
            source_block="Prey Accumulation",
            source_port="Prey Level",
            target_block="Predation",
            target_port="Prey Level",
            direction=FlowDirection.COVARIANT,
        ),
        Wiring(
            source_block="Prey Accumulation",
            source_port="Prey Level",
            target_block="Predator Growth",
            target_port="Prey Level",
            direction=FlowDirection.COVARIANT,
        ),
        # Predator Level → Predation, Predator Growth, Predator Decline
        Wiring(
            source_block="Predator Accumulation",
            source_port="Predator Level",
            target_block="Predation",
            target_port="Predator Level",
            direction=FlowDirection.COVARIANT,
        ),
        Wiring(
            source_block="Predator Accumulation",
            source_port="Predator Level",
            target_block="Predator Growth",
            target_port="Predator Level",
            direction=FlowDirection.COVARIANT,
        ),
        Wiring(
            source_block="Predator Accumulation",
            source_port="Predator Level",
            target_block="Predator Decline",
            target_port="Predator Level",
            direction=FlowDirection.COVARIANT,
        ),
    ]

    root = root.loop(temporal_wirings)
    return compile_system("Predator Prey", root)


# ── Level 1: GDSSpec equivalence ────────────────────────────────


class TestSpecEquivalence:
    """GDSSpec-level structural equivalence between DSL and hand-built."""

    def test_entity_names_match(self, dsl_spec, hand_spec):
        assert set(dsl_spec.entities.keys()) == set(hand_spec.entities.keys())

    def test_entity_variables_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.entities:
            dsl_vars = set(dsl_spec.entities[name].variables.keys())
            hand_vars = set(hand_spec.entities[name].variables.keys())
            assert dsl_vars == hand_vars, f"Entity {name!r} variable mismatch"

    def test_block_names_match(self, dsl_spec, hand_spec):
        assert set(dsl_spec.blocks.keys()) == set(hand_spec.blocks.keys())

    def test_block_role_types_match(self, dsl_spec, hand_spec):
        for name in dsl_spec.blocks:
            dsl_block = dsl_spec.blocks[name]
            hand_block = hand_spec.blocks[name]
            assert isinstance(hand_block, type(dsl_block)), (
                f"Block {name!r}: DSL is {type(dsl_block).__name__}, "
                f"hand-built is {type(hand_block).__name__}"
            )

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
                ), f"Mechanism {name!r} update targets mismatch"

    def test_parameter_schema_match(self, dsl_spec, hand_spec):
        assert dsl_spec.parameter_schema.names() == hand_spec.parameter_schema.names()

    def test_both_specs_validate(self, dsl_spec, hand_spec):
        assert dsl_spec.validate_spec() == []
        assert hand_spec.validate_spec() == []


# ── Level 2: Canonical equivalence ──────────────────────────────


class TestCanonicalEquivalence:
    """CanonicalGDS-level equivalence between DSL and hand-built."""

    @pytest.fixture
    def dsl_canonical(self, dsl_spec):
        return project_canonical(dsl_spec)

    @pytest.fixture
    def hand_canonical(self, hand_spec):
        return project_canonical(hand_spec)

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

    def test_decision_ports_match(self, dsl_canonical, hand_canonical):
        assert set(dsl_canonical.decision_ports) == set(hand_canonical.decision_ports)

    def test_update_map_match(self, dsl_canonical, hand_canonical):
        dsl_map = {name: targets for name, targets in dsl_canonical.update_map}
        hand_map = {name: targets for name, targets in hand_canonical.update_map}
        assert dsl_map == hand_map


# ── Level 3: SystemIR equivalence ──────────────────────────────


class TestSystemIREquivalence:
    """SystemIR-level equivalence between DSL and hand-built."""

    def test_block_count_match(self, dsl_ir, hand_ir):
        assert len(dsl_ir.blocks) == len(hand_ir.blocks)

    def test_block_names_match(self, dsl_ir, hand_ir):
        dsl_names = {b.name for b in dsl_ir.blocks}
        hand_names = {b.name for b in hand_ir.blocks}
        assert dsl_names == hand_names

    def test_wiring_count_match(self, dsl_ir, hand_ir):
        assert len(dsl_ir.wirings) == len(hand_ir.wirings)

    def test_temporal_wiring_count_match(self, dsl_ir, hand_ir):
        dsl_temporal = [w for w in dsl_ir.wirings if w.is_temporal]
        hand_temporal = [w for w in hand_ir.wirings if w.is_temporal]
        assert len(dsl_temporal) == len(hand_temporal)

    def test_temporal_wiring_pairs_match(self, dsl_ir, hand_ir):
        dsl_pairs = {(w.source, w.target) for w in dsl_ir.wirings if w.is_temporal}
        hand_pairs = {(w.source, w.target) for w in hand_ir.wirings if w.is_temporal}
        assert dsl_pairs == hand_pairs

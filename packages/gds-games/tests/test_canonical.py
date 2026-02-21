"""Canonical projection tests for OGS → GDS bridge.

Validates that OGS patterns produce correct canonical decompositions
when projected through compile_pattern_to_spec() → project_canonical().

Key structural claim: games are pure policy. f = ∅, everything in g.
No Mechanisms, no state variables, no update map.

Three archetype tiers:
1. Simple sequential (CovariantFunction pipeline)
2. Feedback (reactive decision agent)
3. Parallel (multi-agent)

Plus parametric invariants and cross-built equivalence.
"""

import pytest

from gds.blocks.roles import Policy
from gds.canonical import CanonicalGDS, project_canonical
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.types.interface import Interface, port

from ogs.dsl.composition import Flow, SequentialComposition
from ogs.dsl.games import (
    CovariantFunction,
    DecisionGame,
    DeletionGame,
    DuplicationGame,
)
from ogs.dsl.library import reactive_decision_agent
from ogs.dsl.pattern import Pattern, PatternInput
from ogs.dsl.spec_bridge import compile_pattern_to_spec
from ogs.dsl.types import InputType, Signature
from ogs.ir.models import CompositionType


# ── Helper: build patterns ──────────────────────────────────────


def _simple_sequential_pattern() -> Pattern:
    """Two covariant functions in sequence: A >> B."""
    a = CovariantFunction(
        name="Transform A",
        signature=Signature(
            x=(port("Raw Input"),),
            y=(port("Intermediate"),),
        ),
    )
    b = CovariantFunction(
        name="Transform B",
        signature=Signature(
            x=(port("Intermediate"),),
            y=(port("Final Output"),),
        ),
    )
    composite = a >> b
    return Pattern(
        name="Simple Sequential",
        game=composite,
        composition_type=CompositionType.SEQUENTIAL,
    )


def _parallel_agents_pattern() -> Pattern:
    """Two decision games in parallel: Agent1 | Agent2."""
    agent1 = DecisionGame(
        name="Agent 1",
        signature=Signature(
            x=(port("Obs A"),),
            y=(port("Choice A"),),
            r=(port("Payoff A"),),
        ),
    )
    agent2 = DecisionGame(
        name="Agent 2",
        signature=Signature(
            x=(port("Obs B"),),
            y=(port("Choice B"),),
            r=(port("Payoff B"),),
        ),
    )
    composite = agent1 | agent2
    return Pattern(
        name="Parallel Agents",
        game=composite,
        composition_type=CompositionType.PARALLEL,
    )


def _feedback_pattern() -> Pattern:
    """Reactive decision agent — the canonical feedback archetype."""
    agent = reactive_decision_agent()
    return Pattern(
        name="Reactive Decision",
        game=agent,
        composition_type=CompositionType.FEEDBACK,
    )


def _sequential_with_inputs_pattern() -> Pattern:
    """Sequential pipeline with external inputs."""
    func = CovariantFunction(
        name="Processor",
        signature=Signature(
            x=(port("Signal"),),
            y=(port("Result"),),
        ),
    )
    return Pattern(
        name="With Inputs",
        game=func,
        inputs=[
            PatternInput(
                name="External Signal",
                input_type=InputType.SENSOR,
                target_game="Processor",
                flow_label="Signal",
            ),
        ],
        composition_type=CompositionType.SEQUENTIAL,
    )


def _mixed_game_types_pattern() -> Pattern:
    """Pattern using diverse game types: duplication + decision + deletion."""
    dup = DuplicationGame(
        name="Broadcast",
        signature=Signature(
            x=(port("Source"),),
            y=(port("Copy A"), port("Copy B")),
        ),
    )
    dec = DecisionGame(
        name="Choose",
        signature=Signature(
            x=(port("Copy A"),),
            y=(port("Action"),),
            r=(port("Reward"),),
        ),
    )
    delete = DeletionGame(
        name="Discard",
        signature=Signature(
            x=(port("Copy B"),),
        ),
    )
    # dup >> (dec | delete)
    inner = SequentialComposition(
        name="Broadcast >> Choose | Discard",
        first=dup,
        second=dec | delete,
        wiring=[
            Flow(
                source_game="Broadcast",
                source_port="Copy A",
                target_game="Choose",
                target_port="Copy A",
            ),
            Flow(
                source_game="Broadcast",
                source_port="Copy B",
                target_game="Discard",
                target_port="Copy B",
            ),
        ],
    )
    return Pattern(
        name="Mixed Types",
        game=inner,
        composition_type=CompositionType.SEQUENTIAL,
    )


# ── Test: Simple Sequential ─────────────────────────────────────


class TestSimpleSequential:
    """Two covariant functions: pure forward pipeline."""

    @pytest.fixture()
    def spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_simple_sequential_pattern())

    @pytest.fixture()
    def canonical(self, spec: GDSSpec) -> CanonicalGDS:
        return project_canonical(spec)

    def test_spec_has_two_blocks(self, spec: GDSSpec) -> None:
        assert len(spec.blocks) == 2

    def test_all_blocks_are_policy(self, spec: GDSSpec) -> None:
        for block in spec.blocks.values():
            assert isinstance(block, Policy)

    def test_canonical_f_is_empty(self, canonical: CanonicalGDS) -> None:
        """Games don't update state — f = ∅."""
        assert canonical.mechanism_blocks == ()

    def test_canonical_x_is_empty(self, canonical: CanonicalGDS) -> None:
        """No entities — X = ∅."""
        assert canonical.state_variables == ()

    def test_canonical_g_contains_all_games(self, canonical: CanonicalGDS) -> None:
        assert set(canonical.policy_blocks) == {"Transform A", "Transform B"}

    def test_no_control_blocks(self, canonical: CanonicalGDS) -> None:
        assert canonical.control_blocks == ()

    def test_no_boundary_blocks(self, canonical: CanonicalGDS) -> None:
        assert canonical.boundary_blocks == ()

    def test_decision_ports_from_forward_out(self, canonical: CanonicalGDS) -> None:
        """D = forward_out ports of all Policy blocks."""
        port_names = {name for _, name in canonical.decision_ports}
        assert "Intermediate" in port_names
        assert "Final Output" in port_names

    def test_update_map_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.update_map == ()


# ── Test: Parallel Agents ───────────────────────────────────────


class TestParallelAgents:
    """Two decision games in parallel — independent agents."""

    @pytest.fixture()
    def spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_parallel_agents_pattern())

    @pytest.fixture()
    def canonical(self, spec: GDSSpec) -> CanonicalGDS:
        return project_canonical(spec)

    def test_two_policy_blocks(self, canonical: CanonicalGDS) -> None:
        assert len(canonical.policy_blocks) == 2

    def test_both_agents_in_g(self, canonical: CanonicalGDS) -> None:
        assert set(canonical.policy_blocks) == {"Agent 1", "Agent 2"}

    def test_f_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.mechanism_blocks == ()

    def test_no_state(self, canonical: CanonicalGDS) -> None:
        assert canonical.state_variables == ()

    def test_decision_ports(self, canonical: CanonicalGDS) -> None:
        port_names = {name for _, name in canonical.decision_ports}
        assert "Choice A" in port_names
        assert "Choice B" in port_names


# ── Test: Feedback (Reactive Decision Agent) ────────────────────


class TestFeedbackCanonical:
    """The canonical reactive decision agent with feedback loops."""

    @pytest.fixture()
    def spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_feedback_pattern())

    @pytest.fixture()
    def canonical(self, spec: GDSSpec) -> CanonicalGDS:
        return project_canonical(spec)

    def test_five_policy_blocks(self, canonical: CanonicalGDS) -> None:
        """CB, History, Policy, RD, Outcome — all Policy."""
        assert len(canonical.policy_blocks) == 5

    def test_all_games_in_g(self, canonical: CanonicalGDS) -> None:
        expected = {
            "Context Builder",
            "History",
            "Policy",
            "Reactive Decision",
            "Outcome",
        }
        assert set(canonical.policy_blocks) == expected

    def test_f_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.mechanism_blocks == ()

    def test_x_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.state_variables == ()

    def test_no_control_blocks(self, canonical: CanonicalGDS) -> None:
        assert canonical.control_blocks == ()

    def test_update_map_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.update_map == ()


# ── Test: Pattern with External Inputs ──────────────────────────


class TestPatternWithInputs:
    """Pattern with PatternInput → BoundaryAction mapping."""

    @pytest.fixture()
    def spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_sequential_with_inputs_pattern())

    @pytest.fixture()
    def canonical(self, spec: GDSSpec) -> CanonicalGDS:
        return project_canonical(spec)

    def test_boundary_block_from_input(self, canonical: CanonicalGDS) -> None:
        assert "External Signal" in canonical.boundary_blocks

    def test_policy_block_from_game(self, canonical: CanonicalGDS) -> None:
        assert "Processor" in canonical.policy_blocks

    def test_input_ports(self, canonical: CanonicalGDS) -> None:
        """U = BoundaryAction forward_out ports."""
        port_names = {name for _, name in canonical.input_ports}
        assert "Signal" in port_names

    def test_f_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.mechanism_blocks == ()


# ── Test: Mixed Game Types ──────────────────────────────────────


class TestMixedGameTypes:
    """Duplication + Decision + Deletion — all map to Policy."""

    @pytest.fixture()
    def spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_mixed_game_types_pattern())

    @pytest.fixture()
    def canonical(self, spec: GDSSpec) -> CanonicalGDS:
        return project_canonical(spec)

    def test_three_policy_blocks(self, canonical: CanonicalGDS) -> None:
        assert len(canonical.policy_blocks) == 3

    def test_all_game_types_are_policy(self, canonical: CanonicalGDS) -> None:
        expected = {"Broadcast", "Choose", "Discard"}
        assert set(canonical.policy_blocks) == expected

    def test_f_empty(self, canonical: CanonicalGDS) -> None:
        assert canonical.mechanism_blocks == ()


# ── Test: Parametric Canonical Invariants ───────────────────────


ALL_PATTERNS = [
    _simple_sequential_pattern,
    _parallel_agents_pattern,
    _feedback_pattern,
    _sequential_with_inputs_pattern,
    _mixed_game_types_pattern,
]


class TestCanonicalInvariants:
    """Parametric invariants that hold across all OGS archetypes."""

    @pytest.fixture(params=ALL_PATTERNS, ids=lambda f: f.__name__)
    def pair(self, request) -> tuple[Pattern, CanonicalGDS]:
        pattern = request.param()
        spec = compile_pattern_to_spec(pattern)
        canonical = project_canonical(spec)
        return pattern, canonical

    def test_f_always_empty(self, pair) -> None:
        """Games never produce Mechanisms — f = ∅ universally."""
        _, canonical = pair
        assert canonical.mechanism_blocks == ()

    def test_x_always_empty(self, pair) -> None:
        """No entities — X = ∅ universally."""
        _, canonical = pair
        assert canonical.state_variables == ()

    def test_no_control_blocks(self, pair) -> None:
        """ControlAction is never used."""
        _, canonical = pair
        assert canonical.control_blocks == ()

    def test_update_map_always_empty(self, pair) -> None:
        """No Mechanisms → no updates."""
        _, canonical = pair
        assert canonical.update_map == ()

    def test_game_count_matches_policy_plus_boundary(self, pair) -> None:
        """Every block is either Policy or BoundaryAction."""
        pattern, canonical = pair
        n_games = len(pattern.game.flatten())
        n_inputs = len(pattern.inputs)
        n_policy = len(canonical.policy_blocks)
        n_boundary = len(canonical.boundary_blocks)
        assert n_policy + n_boundary == n_games + n_inputs

    def test_role_partition_is_complete_and_disjoint(self, pair) -> None:
        """All blocks classified, no overlaps."""
        _, canonical = pair
        all_classified = (
            set(canonical.boundary_blocks)
            | set(canonical.control_blocks)
            | set(canonical.policy_blocks)
            | set(canonical.mechanism_blocks)
        )
        total = (
            len(canonical.boundary_blocks)
            + len(canonical.control_blocks)
            + len(canonical.policy_blocks)
            + len(canonical.mechanism_blocks)
        )
        # No duplicates
        assert len(all_classified) == total
        # All blocks accounted for (boundary + policy = total)
        assert total == len(canonical.policy_blocks) + len(canonical.boundary_blocks)


# ── Test: Cross-Built Equivalence ───────────────────────────────


class TestCrossBuiltEquivalence:
    """Compare DSL-compiled spec to hand-built GDSSpec for the simple sequential case."""

    @pytest.fixture()
    def dsl_spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_simple_sequential_pattern())

    @pytest.fixture()
    def hand_spec(self) -> GDSSpec:
        """Hand-built GDSSpec equivalent of the simple sequential pattern."""
        spec = GDSSpec(name="Simple Sequential", description="Hand-built")

        spec.register_block(
            Policy(
                name="Transform A",
                interface=Interface(
                    forward_in=(port("Raw Input"),),
                    forward_out=(port("Intermediate"),),
                ),
            )
        )
        spec.register_block(
            Policy(
                name="Transform B",
                interface=Interface(
                    forward_in=(port("Intermediate"),),
                    forward_out=(port("Final Output"),),
                ),
            )
        )

        spec.register_wiring(
            SpecWiring(
                name="Simple Sequential Wiring",
                block_names=["Transform A", "Transform B"],
                wires=[
                    Wire(
                        source="Transform A",
                        target="Transform B",
                        space="Intermediate Flow",
                    ),
                ],
                description="Hand-built wiring",
            )
        )

        return spec

    def test_same_block_names(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        assert set(dsl_spec.blocks.keys()) == set(hand_spec.blocks.keys())

    def test_same_block_roles(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        for name in dsl_spec.blocks:
            assert type(dsl_spec.blocks[name]) is type(hand_spec.blocks[name])

    def test_same_port_names(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        for name in dsl_spec.blocks:
            dsl_out = {p.name for p in dsl_spec.blocks[name].interface.forward_out}
            hand_out = {p.name for p in hand_spec.blocks[name].interface.forward_out}
            assert dsl_out == hand_out

            dsl_in = {p.name for p in dsl_spec.blocks[name].interface.forward_in}
            hand_in = {p.name for p in hand_spec.blocks[name].interface.forward_in}
            assert dsl_in == hand_in

    def test_canonical_equivalence(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        dsl_can = project_canonical(dsl_spec)
        hand_can = project_canonical(hand_spec)

        assert set(dsl_can.policy_blocks) == set(hand_can.policy_blocks)
        assert set(dsl_can.boundary_blocks) == set(hand_can.boundary_blocks)
        assert set(dsl_can.mechanism_blocks) == set(hand_can.mechanism_blocks)
        assert dsl_can.state_variables == hand_can.state_variables
        assert set(dsl_can.decision_ports) == set(hand_can.decision_ports)


# ── Test: Feedback Cross-Built Equivalence ──────────────────────


class TestFeedbackCrossBuilt:
    """Cross-built equivalence for the reactive decision agent."""

    @pytest.fixture()
    def dsl_spec(self) -> GDSSpec:
        return compile_pattern_to_spec(_feedback_pattern())

    @pytest.fixture()
    def hand_spec(self) -> GDSSpec:
        """Hand-built GDSSpec for the reactive decision agent."""
        spec = GDSSpec(name="Reactive Decision", description="Hand-built")

        # Context Builder: CovariantFunction(x=[Event, Constraint, Primitive], y=[Obs,Ctx])
        spec.register_block(
            Policy(
                name="Context Builder",
                interface=Interface(
                    forward_in=(port("Event"), port("Constraint"), port("Primitive")),
                    forward_out=(port("Observation, Context"),),
                ),
            )
        )

        # History: DecisionGame(x=[Primitive], y=[Latest History], r=[History Update])
        spec.register_block(
            Policy(
                name="History",
                interface=Interface(
                    forward_in=(port("Primitive"),),
                    forward_out=(port("Latest History"),),
                    backward_in=(port("History Update"),),
                ),
            )
        )

        # Policy: DecisionGame(x=[Latest History, Primitive], y=[Latest Policy], r=[Experience], s=[History Update])
        spec.register_block(
            Policy(
                name="Policy",
                interface=Interface(
                    forward_in=(port("Latest History"), port("Primitive")),
                    forward_out=(port("Latest Policy"),),
                    backward_in=(port("Experience"),),
                    backward_out=(port("History Update"),),
                ),
            )
        )

        # Reactive Decision: DecisionGame(x=[Obs,Ctx + Latest Policy], y=[Decision], r=[Outcome], s=[Experience])
        spec.register_block(
            Policy(
                name="Reactive Decision",
                interface=Interface(
                    forward_in=(port("Observation, Context"), port("Latest Policy")),
                    forward_out=(port("Decision"),),
                    backward_in=(port("Outcome"),),
                    backward_out=(port("Experience"),),
                ),
            )
        )

        # Outcome: DecisionGame(x=[Decision, Primitive], s=[Outcome])
        spec.register_block(
            Policy(
                name="Outcome",
                interface=Interface(
                    forward_in=(port("Decision"), port("Primitive")),
                    backward_out=(port("Outcome"),),
                ),
            )
        )

        return spec

    def test_same_block_count(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        assert len(dsl_spec.blocks) == len(hand_spec.blocks)

    def test_same_block_names(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        assert set(dsl_spec.blocks.keys()) == set(hand_spec.blocks.keys())

    def test_all_policy(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        for name in dsl_spec.blocks:
            assert isinstance(dsl_spec.blocks[name], Policy)
            assert isinstance(hand_spec.blocks[name], Policy)

    def test_same_forward_out_ports(
        self, dsl_spec: GDSSpec, hand_spec: GDSSpec
    ) -> None:
        for name in dsl_spec.blocks:
            dsl_ports = {p.name for p in dsl_spec.blocks[name].interface.forward_out}
            hand_ports = {p.name for p in hand_spec.blocks[name].interface.forward_out}
            assert dsl_ports == hand_ports, f"forward_out mismatch for {name}"

    def test_same_forward_in_ports(self, dsl_spec: GDSSpec, hand_spec: GDSSpec) -> None:
        for name in dsl_spec.blocks:
            dsl_ports = {p.name for p in dsl_spec.blocks[name].interface.forward_in}
            hand_ports = {p.name for p in hand_spec.blocks[name].interface.forward_in}
            assert dsl_ports == hand_ports, f"forward_in mismatch for {name}"

    def test_canonical_role_equivalence(
        self, dsl_spec: GDSSpec, hand_spec: GDSSpec
    ) -> None:
        dsl_can = project_canonical(dsl_spec)
        hand_can = project_canonical(hand_spec)
        assert set(dsl_can.policy_blocks) == set(hand_can.policy_blocks)
        assert dsl_can.mechanism_blocks == hand_can.mechanism_blocks == ()
        assert dsl_can.control_blocks == hand_can.control_blocks == ()

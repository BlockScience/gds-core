"""Tests for the 7 new APIs introduced in gds-games.

Covers:
  #4  Flow accepts str | OpenGame for game refs
  #3  FeedbackFlow (CONTRAVARIANT default)
  #6  ParallelComposition.from_list() + parallel() free function
  #1  reactive_decision_agent() flags (include_outcome, include_feedback)
  #2  multi_agent_composition()
  #5  Pattern.specialize()
  #7  discover_patterns() registry
"""

import sys
import types
from pathlib import Path

import pytest

from gds.ir.models import FlowDirection

from ogs.dsl import (
    FeedbackLoop,
    Flow,
    ParallelComposition,
    Pattern,
    SequentialComposition,
    compile_to_ir,
    context_builder,
    outcome,
    parallel,
    policy,
    reactive_decision,
    reactive_decision_agent,
)
from ogs.dsl.composition import FeedbackFlow
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.dsl.library import multi_agent_composition
from ogs.dsl.pattern import (
    ActionSpace,
    PatternInput,
    StateInitialization,
    TerminalCondition,
)
from ogs.dsl.types import CompositionType, InputType, Signature, port
from ogs.registry import discover_patterns


# ---------------------------------------------------------------------------
# #4 — Flow accepts OpenGame objects (coerces to name string)
# ---------------------------------------------------------------------------


class TestFlowObjectRef:
    """Flow should accept OpenGame instances and coerce them to name strings."""

    def _games(self):
        g1 = CovariantFunction(name="G1", interface=Signature(y=(port("X"),)))
        g2 = CovariantFunction(name="G2", interface=Signature(x=(port("X"),)))
        return g1, g2

    def test_string_source_still_works(self):
        g1, g2 = self._games()
        f = Flow(source_game="G1", source_port="X", target_game="G2", target_port="X")
        assert f.source_game == "G1"
        assert f.target_game == "G2"

    def test_object_source_coerced_to_name(self):
        g1, g2 = self._games()
        f = Flow(source_game=g1, source_port="X", target_game="G2", target_port="X")
        assert f.source_game == "G1"
        assert isinstance(f.source_game, str)

    def test_object_target_coerced_to_name(self):
        g1, g2 = self._games()
        f = Flow(source_game="G1", source_port="X", target_game=g2, target_port="X")
        assert f.target_game == "G2"
        assert isinstance(f.target_game, str)

    def test_both_objects_coerced(self):
        g1, g2 = self._games()
        f = Flow(source_game=g1, source_port="X", target_game=g2, target_port="X")
        assert f.source_game == "G1"
        assert f.target_game == "G2"

    def test_gds_interop_source_block_property(self):
        g1, _ = self._games()
        f = Flow(source_game=g1, source_port="X", target_game="G2", target_port="X")
        assert f.source_block == f.source_game == "G1"

    def test_gds_interop_target_block_property(self):
        _, g2 = self._games()
        f = Flow(source_game="G1", source_port="X", target_game=g2, target_port="X")
        assert f.target_block == f.target_game == "G2"

    def test_flow_is_frozen(self):
        f = Flow(source_game="A", source_port="p", target_game="B", target_port="q")
        with pytest.raises(Exception):
            f.source_game = "C"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# #3 — FeedbackFlow (CONTRAVARIANT default)
# ---------------------------------------------------------------------------


class TestFeedbackFlow:
    """FeedbackFlow is a Flow subclass with direction defaulting to CONTRAVARIANT."""

    def test_default_direction_is_contravariant(self):
        ff = FeedbackFlow(
            source_game="Outcome",
            source_port="Outcome",
            target_game="Reactive Decision",
            target_port="Outcome",
        )
        assert ff.direction == FlowDirection.CONTRAVARIANT

    def test_plain_flow_default_is_covariant(self):
        f = Flow(source_game="A", source_port="p", target_game="B", target_port="q")
        assert f.direction == FlowDirection.COVARIANT

    def test_feedback_flow_inherits_object_ref_coercion(self):
        g1 = DecisionGame(name="Router", interface=Signature(s=(port("Outcome"),)))
        g2 = DecisionGame(name="Agent", interface=Signature(r=(port("Outcome"),)))
        ff = FeedbackFlow(
            source_game=g1, source_port="Outcome", target_game=g2, target_port="Outcome"
        )
        assert ff.source_game == "Router"
        assert ff.target_game == "Agent"
        assert ff.direction == FlowDirection.CONTRAVARIANT

    def test_direction_can_be_overridden(self):
        ff = FeedbackFlow(
            source_game="A",
            source_port="p",
            target_game="B",
            target_port="q",
            direction=FlowDirection.COVARIANT,
        )
        assert ff.direction == FlowDirection.COVARIANT

    def test_is_subclass_of_flow(self):
        assert issubclass(FeedbackFlow, Flow)

    def test_feedback_flow_is_frozen(self):
        ff = FeedbackFlow(
            source_game="A", source_port="p", target_game="B", target_port="q"
        )
        with pytest.raises(Exception):
            ff.source_game = "C"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# #6 — ParallelComposition.from_list() + parallel() free function
# ---------------------------------------------------------------------------


class TestParallelFromList:
    """ParallelComposition.from_list() composes N games into one parallel composition."""

    def _game(self, name: str) -> CovariantFunction:
        return CovariantFunction(name=name, interface=Signature())

    def test_two_games(self):
        g1, g2 = self._game("G1"), self._game("G2")
        par = ParallelComposition.from_list([g1, g2])
        assert isinstance(par, ParallelComposition)
        assert len(par.flatten()) == 2

    def test_three_games(self):
        games = [self._game(f"G{i}") for i in range(1, 4)]
        par = ParallelComposition.from_list(games)
        assert isinstance(par, ParallelComposition)
        assert len(par.flatten()) == 3

    def test_five_games(self):
        games = [self._game(f"Agent {i}") for i in range(1, 6)]
        par = ParallelComposition.from_list(games)
        names = {g.name for g in par.flatten()}
        assert names == {f"Agent {i}" for i in range(1, 6)}

    def test_requires_at_least_two(self):
        with pytest.raises(ValueError, match="at least 2"):
            ParallelComposition.from_list([self._game("Solo")])

    def test_requires_nonempty(self):
        with pytest.raises(ValueError, match="at least 2"):
            ParallelComposition.from_list([])

    def test_name_override(self):
        g1, g2 = self._game("A"), self._game("B")
        par = ParallelComposition.from_list([g1, g2], name="Custom Name")
        assert par.name == "Custom Name"

    def test_default_name_is_pipe_joined(self):
        g1, g2 = self._game("Alpha"), self._game("Beta")
        par = ParallelComposition.from_list([g1, g2])
        assert par.name == "Alpha | Beta"


class TestParallelFreeFunction:
    """parallel() is a convenience wrapper for ParallelComposition.from_list()."""

    def _game(self, name: str) -> CovariantFunction:
        return CovariantFunction(name=name, interface=Signature())

    def test_returns_parallel_composition(self):
        par = parallel([self._game("A"), self._game("B")])
        assert isinstance(par, ParallelComposition)

    def test_delegates_to_from_list(self):
        games = [self._game(f"X{i}") for i in range(3)]
        par = parallel(games)
        assert len(par.flatten()) == 3

    def test_name_override(self):
        par = parallel([self._game("A"), self._game("B")], name="My Parallel")
        assert par.name == "My Parallel"

    def test_raises_on_single_game(self):
        with pytest.raises(ValueError, match="at least 2"):
            parallel([self._game("Lone")])


# ---------------------------------------------------------------------------
# #1 — reactive_decision_agent() flags
# ---------------------------------------------------------------------------


class TestReactiveDecisionAgentFlags:
    """All 4 combinations of (include_outcome, include_feedback) flags."""

    def test_default_is_feedback_loop_with_five_games(self):
        agent = reactive_decision_agent()
        assert isinstance(agent, FeedbackLoop)
        assert len(agent.flatten()) == 5
        names = {g.name for g in agent.flatten()}
        assert "Outcome" in names

    def test_include_outcome_true_include_feedback_true(self):
        agent = reactive_decision_agent(include_outcome=True, include_feedback=True)
        assert isinstance(agent, FeedbackLoop)
        assert len(agent.flatten()) == 5
        # 3 contravariant feedback flows
        contra_flows = [
            f
            for f in agent.feedback_wiring
            if f.direction == FlowDirection.CONTRAVARIANT
        ]
        assert len(contra_flows) == 3

    def test_include_outcome_false_include_feedback_true(self):
        agent = reactive_decision_agent(include_outcome=False, include_feedback=True)
        assert isinstance(agent, FeedbackLoop)
        assert len(agent.flatten()) == 4
        names = {g.name for g in agent.flatten()}
        assert "Outcome" not in names
        # 2 feedback flows (no outcome → no outcome→RD flow)
        assert len(agent.feedback_wiring) == 2

    def test_include_outcome_true_include_feedback_false(self):
        agent = reactive_decision_agent(include_outcome=True, include_feedback=False)
        assert isinstance(agent, SequentialComposition)
        assert len(agent.flatten()) == 5
        names = {g.name for g in agent.flatten()}
        assert "Outcome" in names

    def test_include_outcome_false_include_feedback_false(self):
        agent = reactive_decision_agent(include_outcome=False, include_feedback=False)
        assert isinstance(agent, SequentialComposition)
        assert len(agent.flatten()) == 4
        names = {g.name for g in agent.flatten()}
        assert "Outcome" not in names

    def test_name_propagates_to_composition(self):
        agent = reactive_decision_agent("My Agent")
        assert agent.name == "My Agent"

    def test_domain_tags_set_on_inner_games(self):
        agent = reactive_decision_agent(
            "My Agent", include_outcome=True, include_feedback=True
        )
        for g in agent.flatten():
            assert g.get_tag("domain") == "My Agent"

    def test_open_loop_compiles(self):
        """An open-loop (no feedback) agent should compile to IR without errors."""
        agent = reactive_decision_agent(
            "Open Agent", include_outcome=False, include_feedback=False
        )
        p = Pattern(name="Open Agent Pattern", game=agent)
        ir = compile_to_ir(p)
        assert len(ir.games) == 4

    def test_full_loop_passes_verification(self):
        """Full feedback loop should pass all verification checks."""
        from ogs.verification.engine import verify

        agent = reactive_decision_agent(include_outcome=True, include_feedback=True)
        p = Pattern(
            name="Full Agent",
            game=agent,
            inputs=[
                PatternInput(
                    name="Sensor",
                    input_type=InputType.SENSOR,
                    target_game="Context Builder",
                    flow_label="Event",
                ),
                PatternInput(
                    name="Resources",
                    input_type=InputType.RESOURCE,
                    target_game="Context Builder",
                    flow_label="Constraint",
                ),
                PatternInput(
                    name="External World",
                    input_type=InputType.EXTERNAL_WORLD,
                    target_game="Outcome",
                    flow_label="Primitive",
                ),
                PatternInput(
                    name="Choice Set",
                    input_type=InputType.RESOURCE,
                    target_game="Context Builder",
                    flow_label="Primitive",
                ),
                PatternInput(
                    name="History Init",
                    input_type=InputType.INITIALIZATION,
                    target_game="History",
                    flow_label="Primitive",
                ),
                PatternInput(
                    name="Policy Init",
                    input_type=InputType.INITIALIZATION,
                    target_game="Policy",
                    flow_label="Primitive",
                ),
            ],
            composition_type=CompositionType.FEEDBACK,
        )
        ir = compile_to_ir(p)
        report = verify(ir)
        assert report.errors == 0, "; ".join(
            f.message for f in report.findings if not f.passed
        )


# ---------------------------------------------------------------------------
# #2 — multi_agent_composition()
# ---------------------------------------------------------------------------


class TestMultiAgentComposition:
    """multi_agent_composition() builds N-agent parallel + router + feedback loop."""

    def _router(self, name: str = "Decision Router") -> DecisionGame:
        return DecisionGame(
            name=name,
            interface=Signature(
                x=(port("Decision"),),
                s=(port("Outcome"), port("Experience"), port("History Update")),
            ),
        )

    def _agent(self, label: str) -> SequentialComposition:
        return reactive_decision_agent(
            label, include_outcome=False, include_feedback=False
        )

    def test_returns_feedback_loop(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={
                "outcome": ("Outcome", "Outcome"),
                "experience": ("Experience", "Experience"),
                "history": ("History Update", "History Update"),
            },
        )
        assert isinstance(result, FeedbackLoop)

    def test_two_agents_correct_game_count(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        # 2 agents × 4 games each + 1 router = 9
        assert len(result.flatten()) == 9

    def test_three_agents_correct_game_count(self):
        agents = [self._agent(f"Agent {i}") for i in range(1, 4)]
        router = self._router()
        result = multi_agent_composition(
            agents=agents,
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        # 3 agents × 4 games each + 1 router = 13
        assert len(result.flatten()) == 13

    def test_feedback_wiring_count(self):
        """N agents × K feedback channels = N×K FeedbackFlow entries."""
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        feedback_port_map = {
            "outcome": ("Outcome", "Outcome"),
            "experience": ("Experience", "Experience"),
            "history": ("History Update", "History Update"),
        }
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map=feedback_port_map,
        )
        # 2 agents × 3 channels = 6 flows
        assert len(result.feedback_wiring) == 6

    def test_all_feedback_flows_are_contravariant(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        for flow in result.feedback_wiring:
            assert flow.direction == FlowDirection.CONTRAVARIANT

    def test_feedback_sources_point_to_router(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router("Router")
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        for flow in result.feedback_wiring:
            assert flow.source_game == "Router"

    def test_feedback_targets_cover_all_agents(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        target_games = {f.target_game for f in result.feedback_wiring}
        assert "Agent 1" in target_games
        assert "Agent 2" in target_games

    def test_name_override(self):
        a1, a2 = self._agent("A1"), self._agent("A2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={},
            name="My Loop",
        )
        assert result.name == "My Loop"

    def test_default_name_contains_router_name(self):
        a1, a2 = self._agent("A1"), self._agent("A2")
        router = self._router("MyRouter")
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={},
        )
        assert "MyRouter" in result.name

    def test_requires_at_least_two_agents(self):
        with pytest.raises(ValueError, match="at least 2"):
            multi_agent_composition(
                agents=[self._agent("Solo")],
                router=self._router(),
                feedback_port_map={},
            )

    def test_compiles_to_ir(self):
        a1, a2 = self._agent("Agent 1"), self._agent("Agent 2")
        router = self._router()
        result = multi_agent_composition(
            agents=[a1, a2],
            router=router,
            feedback_port_map={"outcome": ("Outcome", "Outcome")},
        )
        p = Pattern(name="Multi Agent", game=result)
        ir = compile_to_ir(p)
        assert len(ir.games) == 9
        assert len([f for f in ir.flows if f.is_feedback]) >= 2


# ---------------------------------------------------------------------------
# #5 — Pattern.specialize()
# ---------------------------------------------------------------------------


class TestPatternSpecialize:
    """Pattern.specialize() creates a derived Pattern sharing the same game tree."""

    def _base(self) -> Pattern:
        agent = reactive_decision_agent()
        return Pattern(
            name="Base Pattern",
            game=agent,
            inputs=[
                PatternInput(
                    name="Sensor",
                    input_type=InputType.SENSOR,
                    target_game="Context Builder",
                    flow_label="Event",
                ),
            ],
            terminal_conditions=[
                TerminalCondition(
                    name="Done", actions={"Agent": "ACCEPT"}, outcome="success"
                ),
            ],
            action_spaces=[
                ActionSpace(game="Reactive Decision", actions=["A", "B"]),
            ],
            initializations=[
                StateInitialization(symbol="h_0", space="H", game="History"),
            ],
            composition_type=CompositionType.FEEDBACK,
            source="test",
        )

    def test_returns_new_pattern_instance(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived is not base

    def test_new_name_applied(self):
        base = self._base()
        derived = base.specialize(name="Specialized Pattern")
        assert derived.name == "Specialized Pattern"

    def test_game_tree_shared(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.game is base.game

    def test_inputs_inherited_by_default(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert len(derived.inputs) == len(base.inputs)
        assert derived.inputs[0].name == "Sensor"

    def test_inputs_can_be_replaced(self):
        base = self._base()
        new_inputs = [
            PatternInput(
                name="NewInput",
                input_type=InputType.RESOURCE,
                target_game="Context Builder",
                flow_label="Constraint",
            )
        ]
        derived = base.specialize(name="Derived", inputs=new_inputs)
        assert len(derived.inputs) == 1
        assert derived.inputs[0].name == "NewInput"

    def test_terminal_conditions_inherited(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.terminal_conditions == base.terminal_conditions

    def test_terminal_conditions_overridable(self):
        base = self._base()
        new_tc = [TerminalCondition(name="New TC", actions={}, outcome="fail")]
        derived = base.specialize(name="Derived", terminal_conditions=new_tc)
        assert len(derived.terminal_conditions) == 1
        assert derived.terminal_conditions[0].name == "New TC"

    def test_action_spaces_inherited(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.action_spaces == base.action_spaces

    def test_action_spaces_overridable(self):
        base = self._base()
        new_as = [ActionSpace(game="G", actions=["X"])]
        derived = base.specialize(name="Derived", action_spaces=new_as)
        assert derived.action_spaces[0].game == "G"

    def test_initializations_inherited(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.initializations == base.initializations

    def test_initializations_overridable(self):
        base = self._base()
        new_init = [StateInitialization(symbol="p_0", space="P")]
        derived = base.specialize(name="Derived", initializations=new_init)
        assert derived.initializations[0].symbol == "p_0"

    def test_composition_type_inherited(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.composition_type == base.composition_type

    def test_composition_type_overridable(self):
        base = self._base()
        derived = base.specialize(
            name="Derived", composition_type=CompositionType.SEQUENTIAL
        )
        assert derived.composition_type == CompositionType.SEQUENTIAL

    def test_source_inherited(self):
        base = self._base()
        derived = base.specialize(name="Derived")
        assert derived.source == "test"

    def test_source_overridable(self):
        base = self._base()
        derived = base.specialize(name="Derived", source="application")
        assert derived.source == "application"

    def test_base_pattern_unchanged(self):
        base = self._base()
        base.specialize(
            name="Child",
            terminal_conditions=[],
            action_spaces=[],
        )
        # base must be unmodified
        assert base.name == "Base Pattern"
        assert (
            base.terminal_conditions is not None and len(base.terminal_conditions) == 1
        )

    def test_derived_pattern_compiles(self):
        base = self._base()
        derived = base.specialize(
            name="Derived Compile Test",
            terminal_conditions=[
                TerminalCondition(
                    name="End", actions={"Agent": "REJECT"}, outcome="failure"
                )
            ],
        )
        ir = compile_to_ir(derived)
        assert ir.name == "Derived Compile Test"
        assert len(ir.games) == 5


# ---------------------------------------------------------------------------
# #7 — discover_patterns() registry
# ---------------------------------------------------------------------------


class TestDiscoverPatterns:
    """discover_patterns() scans a directory and returns {stem: Pattern}."""

    def _make_pattern_module(
        self, tmp_path: Path, name: str, pattern_name: str
    ) -> None:
        content = f"""\
from ogs.dsl.games import DecisionGame
from ogs.dsl.pattern import Pattern
from ogs.dsl.types import Signature

game = DecisionGame(name="{pattern_name}", interface=Signature())
pattern = Pattern(name="{pattern_name}", game=game)
"""
        (tmp_path / f"{name}.py").write_text(content)

    def test_returns_dict(self, tmp_path):
        self._make_pattern_module(tmp_path, "my_pattern", "My Pattern")
        result = discover_patterns(tmp_path)
        assert isinstance(result, dict)

    def test_discovers_single_pattern(self, tmp_path):
        self._make_pattern_module(tmp_path, "my_pattern", "My Pattern")
        result = discover_patterns(tmp_path)
        assert "my_pattern" in result
        assert isinstance(result["my_pattern"], Pattern)

    def test_discovers_multiple_patterns(self, tmp_path):
        for stem in ("alpha", "beta", "gamma"):
            self._make_pattern_module(tmp_path, stem, stem.title())
        result = discover_patterns(tmp_path)
        assert set(result.keys()) == {"alpha", "beta", "gamma"}

    def test_skips_private_modules(self, tmp_path):
        self._make_pattern_module(tmp_path, "public", "Public")
        # _private.py should be skipped
        (tmp_path / "_private.py").write_text(
            "from ogs.dsl.games import DecisionGame\n"
            "from ogs.dsl.pattern import Pattern\n"
            "from ogs.dsl.types import Signature\n"
            "game = DecisionGame(name='Private', interface=Signature())\n"
            "pattern = Pattern(name='Private', game=game)\n"
        )
        result = discover_patterns(tmp_path)
        assert "public" in result
        assert "_private" not in result

    def test_skips_init_module(self, tmp_path):
        self._make_pattern_module(tmp_path, "real", "Real Pattern")
        (tmp_path / "__init__.py").write_text("")
        result = discover_patterns(tmp_path)
        assert "__init__" not in result
        assert "real" in result

    def test_skips_files_without_pattern_attribute(self, tmp_path):
        (tmp_path / "no_pattern.py").write_text("x = 42\n")
        result = discover_patterns(tmp_path)
        assert "no_pattern" not in result

    def test_skips_files_that_fail_to_import(self, tmp_path):
        (tmp_path / "broken.py").write_text("raise RuntimeError('intentional')\n")
        self._make_pattern_module(tmp_path, "good", "Good")
        result = discover_patterns(tmp_path)
        assert "good" in result
        assert "broken" not in result

    def test_custom_attribute_name(self, tmp_path):
        (tmp_path / "custom.py").write_text(
            "from ogs.dsl.games import DecisionGame\n"
            "from ogs.dsl.pattern import Pattern\n"
            "from ogs.dsl.types import Signature\n"
            "game = DecisionGame(name='Custom', interface=Signature())\n"
            "my_pattern = Pattern(name='Custom', game=game)\n"
        )
        result = discover_patterns(tmp_path, attribute="my_pattern")
        assert "custom" in result

    def test_empty_directory(self, tmp_path):
        result = discover_patterns(tmp_path)
        assert result == {}

    def test_raises_for_nonexistent_directory(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        with pytest.raises(NotADirectoryError):
            discover_patterns(missing)

    def test_raises_for_file_path(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("")
        with pytest.raises(NotADirectoryError):
            discover_patterns(f)

    def test_returns_pattern_objects_by_name(self, tmp_path):
        self._make_pattern_module(tmp_path, "check", "My Checked Pattern")
        result = discover_patterns(tmp_path)
        assert result["check"].name == "My Checked Pattern"

    def test_discovered_patterns_compile(self, tmp_path):
        self._make_pattern_module(tmp_path, "compile_me", "Compile Me")
        result = discover_patterns(tmp_path)
        ir = compile_to_ir(result["compile_me"])
        assert ir.name == "Compile Me"

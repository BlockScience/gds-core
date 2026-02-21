"""Tests for the typed DSL."""

import pytest

from gds.blocks.errors import GDSTypeError

from ogs.dsl import (
    ActionSpace,
    CorecursiveLoop,
    CounitGame,
    CovariantFunction,
    ContravariantFunction,
    DecisionGame,
    DeletionGame,
    DSLTypeError,
    DuplicationGame,
    FeedbackLoop,
    Flow,
    ParallelComposition,
    Pattern,
    PatternInput,
    SequentialComposition,
    StateInitialization,
    TerminalCondition,
    compile_to_ir,
    context_builder,
    history,
    outcome,
    policy,
    port,
    reactive_decision,
    reactive_decision_agent,
)
from ogs.dsl.types import Signature
from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    GameType,
    HierarchyNodeIR,
    InputType,
)


# ---------------------------------------------------------------------------
# types.py
# ---------------------------------------------------------------------------


class TestPort:
    def test_port_helper(self):
        p = port("Latest Policy")
        assert p.name == "Latest Policy"
        assert p.type_tokens == frozenset({"latest policy"})

    def test_port_multi_token(self):
        p = port("Observation, Context")
        assert "observation" in p.type_tokens
        assert "context" in p.type_tokens

    def test_port_frozen(self):
        p = port("Test")
        with pytest.raises(Exception):
            p.name = "Changed"  # type: ignore[reportAttributeAccessIssue]


class TestSignature:
    def test_empty_signature(self):
        s = Signature()
        assert s.x == ()
        assert s.y == ()
        assert s.r == ()
        assert s.s == ()

    def test_signature_with_ports(self):
        s = Signature(
            x=(port("A"),),
            y=(port("B"), port("C")),
        )
        assert len(s.x) == 1
        assert len(s.y) == 2


# ---------------------------------------------------------------------------
# games.py
# ---------------------------------------------------------------------------


class TestDecisionGame:
    def test_basic(self):
        g = DecisionGame(
            name="Test",
            interface=Signature(
                x=(port("Obs"),),
                y=(port("Choice"),),
                r=(port("Utility"),),
                s=(port("Coutility"),),
            ),
        )
        assert g.game_type == GameType.DECISION
        assert g.name == "Test"

    def test_flatten(self):
        g = DecisionGame(
            name="Test",
            interface=Signature(x=(port("A"),), y=(port("B"),)),
        )
        flat = g.flatten()
        assert len(flat) == 1
        assert flat[0] is g


class TestCovariantFunction:
    def test_basic(self):
        g = CovariantFunction(
            name="F",
            interface=Signature(x=(port("In"),), y=(port("Out"),)),
        )
        assert g.game_type == GameType.FUNCTION_COVARIANT

    def test_rejects_contravariant(self):
        with pytest.raises(DSLTypeError, match="contravariant"):
            CovariantFunction(
                name="Bad",
                interface=Signature(
                    x=(port("In"),),
                    y=(port("Out"),),
                    r=(port("Utility"),),
                ),
            )


class TestContravariantFunction:
    def test_basic(self):
        g = ContravariantFunction(
            name="F",
            interface=Signature(r=(port("In"),), s=(port("Out"),)),
        )
        assert g.game_type == GameType.FUNCTION_CONTRAVARIANT

    def test_rejects_covariant(self):
        with pytest.raises(DSLTypeError, match="covariant"):
            ContravariantFunction(
                name="Bad",
                interface=Signature(
                    x=(port("In"),),
                    r=(port("Utility"),),
                ),
            )


# ---------------------------------------------------------------------------
# New atomic game types
# ---------------------------------------------------------------------------


class TestDeletionGame:
    def test_basic(self):
        g = DeletionGame(
            name="Del",
            interface=Signature(x=(port("Input"),)),
        )
        assert g.game_type == GameType.DELETION
        assert g.signature.y == ()

    def test_rejects_nonempty_y(self):
        with pytest.raises(DSLTypeError, match="empty Y"):
            DeletionGame(
                name="Bad",
                interface=Signature(x=(port("In"),), y=(port("Out"),)),
            )

    def test_flatten(self):
        g = DeletionGame(name="Del", interface=Signature(x=(port("In"),)))
        assert len(g.flatten()) == 1


class TestDuplicationGame:
    def test_basic(self):
        g = DuplicationGame(
            name="Dup",
            interface=Signature(
                x=(port("Input"),),
                y=(port("Copy1"), port("Copy2")),
            ),
        )
        assert g.game_type == GameType.DUPLICATION
        assert len(g.signature.y) == 2

    def test_rejects_single_y(self):
        with pytest.raises(DSLTypeError, match="2\\+ Y ports"):
            DuplicationGame(
                name="Bad",
                interface=Signature(
                    x=(port("In"),),
                    y=(port("Out"),),
                ),
            )

    def test_rejects_empty_y(self):
        with pytest.raises(DSLTypeError, match="2\\+ Y ports"):
            DuplicationGame(name="Bad", interface=Signature(x=(port("In"),)))


class TestCounitGame:
    def test_basic(self):
        g = CounitGame(
            name="Counit",
            interface=Signature(
                x=(port("Input"),),
                s=(port("Input"),),
            ),
        )
        assert g.game_type == GameType.COUNIT
        assert g.signature.y == ()
        assert g.signature.r == ()

    def test_rejects_nonempty_y(self):
        with pytest.raises(DSLTypeError, match="empty Y"):
            CounitGame(
                name="Bad",
                interface=Signature(
                    x=(port("In"),),
                    y=(port("Out"),),
                    s=(port("In"),),
                ),
            )

    def test_rejects_nonempty_r(self):
        with pytest.raises(DSLTypeError, match="empty R"):
            CounitGame(
                name="Bad",
                interface=Signature(
                    x=(port("In"),),
                    r=(port("Util"),),
                    s=(port("In"),),
                ),
            )


# ---------------------------------------------------------------------------
# composition.py
# ---------------------------------------------------------------------------


class TestSequentialComposition:
    def test_auto_wire_matching_tokens(self):
        g1 = CovariantFunction(
            name="F1",
            interface=Signature(x=(port("A"),), y=(port("B"),)),
        )
        g2 = CovariantFunction(
            name="F2",
            interface=Signature(x=(port("B"),), y=(port("C"),)),
        )
        seq = g1 >> g2
        assert isinstance(seq, SequentialComposition)
        assert seq.name == "F1 >> F2"

    def test_type_mismatch_without_wiring(self):
        g1 = CovariantFunction(
            name="F1",
            interface=Signature(x=(port("A"),), y=(port("B"),)),
        )
        g2 = CovariantFunction(
            name="F2",
            interface=Signature(x=(port("X"),), y=(port("Y"),)),
        )
        with pytest.raises(GDSTypeError, match="no overlap"):
            _ = g1 >> g2

    def test_explicit_wiring_skips_type_check(self):
        g1 = CovariantFunction(
            name="F1",
            interface=Signature(x=(port("A"),), y=(port("B"),)),
        )
        g2 = CovariantFunction(
            name="F2",
            interface=Signature(x=(port("X"),), y=(port("Y"),)),
        )
        # With explicit wiring, no type error
        seq = SequentialComposition(
            name="F1 >> F2",
            first=g1,
            second=g2,
            wiring=[
                Flow(
                    source_game="F1",
                    source_port="B",
                    target_game="F2",
                    target_port="X",
                ),
            ],
        )
        assert isinstance(seq, SequentialComposition)

    def test_flatten(self):
        g1 = CovariantFunction(name="F1", interface=Signature(y=(port("B"),)))
        g2 = CovariantFunction(name="F2", interface=Signature(x=(port("B"),)))
        seq = g1 >> g2
        flat = seq.flatten()
        assert len(flat) == 2
        assert flat[0].name == "F1"
        assert flat[1].name == "F2"


class TestParallelComposition:
    def test_basic(self):
        g1 = CovariantFunction(
            name="F1",
            interface=Signature(x=(port("A"),), y=(port("B"),)),
        )
        g2 = CovariantFunction(
            name="F2",
            interface=Signature(x=(port("C"),), y=(port("D"),)),
        )
        par = g1 | g2
        assert isinstance(par, ParallelComposition)
        assert len(par.signature.x) == 2
        assert len(par.signature.y) == 2

    def test_flatten(self):
        g1 = CovariantFunction(name="F1", interface=Signature())
        g2 = CovariantFunction(name="F2", interface=Signature())
        par = g1 | g2
        assert len(par.flatten()) == 2


class TestFeedbackLoop:
    def test_basic(self):
        g = DecisionGame(
            name="D",
            interface=Signature(
                x=(port("Obs"),),
                y=(port("Choice"),),
                r=(port("Utility"),),
                s=(port("Coutility"),),
            ),
        )
        fb = g.feedback(
            [
                Flow(
                    source_game="D",
                    source_port="Coutility",
                    target_game="D",
                    target_port="Utility",
                    direction=FlowDirection.CONTRAVARIANT,
                ),
            ]
        )
        assert isinstance(fb, FeedbackLoop)
        assert fb.signature == g.signature

    def test_flatten_preserves_inner(self):
        g = DecisionGame(name="D", interface=Signature())
        fb = g.feedback([])
        assert len(fb.flatten()) == 1


class TestCorecursiveLoop:
    def test_basic(self):
        g = DecisionGame(
            name="D",
            interface=Signature(
                x=(port("Obs"),),
                y=(port("Choice"),),
                r=(port("Utility"),),
                s=(port("Coutility"),),
            ),
        )
        cl = g.corecursive(
            [
                Flow(
                    source_game="D",
                    source_port="Choice",
                    target_game="D",
                    target_port="Obs",
                ),
            ],
            exit_condition="max rounds",
        )
        assert isinstance(cl, CorecursiveLoop)
        assert cl.signature == g.signature
        assert cl.exit_condition == "max rounds"

    def test_rejects_contravariant_wiring(self):
        g = DecisionGame(name="D", interface=Signature())
        with pytest.raises(GDSTypeError, match="COVARIANT"):
            CorecursiveLoop(
                name="Bad",
                inner=g,
                temporal_wiring=[
                    Flow(
                        source_game="D",
                        source_port="X",
                        target_game="D",
                        target_port="Y",
                        direction=FlowDirection.CONTRAVARIANT,
                    ),
                ],
            )

    def test_flatten_preserves_inner(self):
        g = DecisionGame(name="D", interface=Signature())
        cl = g.corecursive([])
        assert len(cl.flatten()) == 1

    def test_signature_preserved(self):
        sig = Signature(
            x=(port("A"),),
            y=(port("B"),),
            r=(port("C"),),
            s=(port("D"),),
        )
        g = DecisionGame(name="D", interface=sig)
        cl = g.corecursive([])
        assert cl.signature == sig


# ---------------------------------------------------------------------------
# pattern.py
# ---------------------------------------------------------------------------


class TestTerminalCondition:
    def test_basic(self):
        tc = TerminalCondition(
            name="Agreement",
            actions={"Agent 1": "ACCEPT", "Agent 2": "PROPOSE"},
            outcome="success",
        )
        assert tc.name == "Agreement"
        assert tc.actions["Agent 1"] == "ACCEPT"

    def test_with_description(self):
        tc = TerminalCondition(
            name="Failure",
            actions={"Agent 1": "REJECT"},
            outcome="failure",
            description="Negotiation fails",
            payoff_description="Zero payoff",
        )
        assert tc.description == "Negotiation fails"


class TestActionSpace:
    def test_basic(self):
        a = ActionSpace(
            game="Agent 1",
            actions=["ACCEPT", "REJECT", "PROPOSE"],
        )
        assert a.game == "Agent 1"
        assert len(a.actions) == 3
        assert a.constraints == []

    def test_with_constraints(self):
        a = ActionSpace(
            game="Agent 1",
            actions=["ACCEPT", "REJECT"],
            constraints=["Cannot ACCEPT in round 1"],
        )
        assert len(a.constraints) == 1


class TestStateInitialization:
    def test_basic(self):
        s = StateInitialization(
            symbol="h_0",
            space="H",
            description="Initial history",
            game="History",
        )
        assert s.symbol == "h_0"
        assert s.space == "H"

    def test_defaults(self):
        s = StateInitialization(symbol="x", space="X")
        assert s.description == ""
        assert s.game == ""


class TestPattern:
    def test_basic(self):
        g = DecisionGame(name="D", interface=Signature())
        p = Pattern(name="Test", game=g)
        assert p.name == "Test"
        assert p.source == "dsl"

    def test_with_inputs(self):
        g = DecisionGame(name="D", interface=Signature())
        p = Pattern(
            name="Test",
            game=g,
            inputs=[
                PatternInput(name="In1", input_type=InputType.SENSOR),
            ],
        )
        assert len(p.inputs) == 1


# ---------------------------------------------------------------------------
# library.py
# ---------------------------------------------------------------------------


class TestLibraryFactories:
    def test_context_builder(self):
        cb = context_builder()
        assert cb.name == "Context Builder"
        assert cb.game_type == GameType.FUNCTION_COVARIANT
        assert len(cb.signature.x) == 3
        assert len(cb.signature.y) == 1

    def test_history(self):
        h = history()
        assert h.name == "History"
        assert h.game_type == GameType.DECISION
        assert len(h.signature.r) == 1

    def test_policy(self):
        p = policy()
        assert p.name == "Policy"
        assert p.game_type == GameType.DECISION
        assert len(p.signature.s) == 1

    def test_outcome(self):
        o = outcome()
        assert o.name == "Outcome"
        assert o.game_type == GameType.DECISION
        assert len(o.signature.s) == 1

    def test_reactive_decision(self):
        rd = reactive_decision()
        assert rd.name == "Reactive Decision"
        assert rd.game_type == GameType.DECISION
        assert len(rd.signature.x) == 2
        assert len(rd.signature.r) == 1
        assert len(rd.signature.s) == 1

    def test_reactive_decision_agent(self):
        agent = reactive_decision_agent()
        assert isinstance(agent, FeedbackLoop)
        assert len(agent.flatten()) == 5
        names = {g.name for g in agent.flatten()}
        assert names == {
            "Context Builder",
            "History",
            "Policy",
            "Reactive Decision",
            "Outcome",
        }


# ---------------------------------------------------------------------------
# compile.py
# ---------------------------------------------------------------------------


class TestCompileToIR:
    def test_game_count(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        assert len(ir.games) == 5

    def test_game_names(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        names = {g.name for g in ir.games}
        assert names == {
            "Context Builder",
            "History",
            "Policy",
            "Reactive Decision",
            "Outcome",
        }

    def test_game_types(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        type_map = {g.name: g.game_type for g in ir.games}
        assert type_map["Context Builder"] == GameType.FUNCTION_COVARIANT
        assert type_map["Policy"] == GameType.DECISION
        assert type_map["History"] == GameType.DECISION
        assert type_map["Reactive Decision"] == GameType.DECISION
        assert type_map["Outcome"] == GameType.DECISION

    def test_signatures(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        sig_map = {g.name: g.signature for g in ir.games}

        # Context Builder: X has 3 parts, Y has 1
        cb_x, cb_y, cb_r, cb_s = sig_map["Context Builder"]
        assert "Event" in cb_x
        assert "Constraint" in cb_x
        assert "Observation, Context" in cb_y
        assert cb_r == ""
        assert cb_s == ""

    def test_flow_count(self):
        agent = reactive_decision_agent()
        p = Pattern(
            name="Test",
            game=agent,
            inputs=[
                PatternInput(
                    name="Sensor",
                    input_type=InputType.SENSOR,
                    target_game="Context Builder",
                    flow_label="Event",
                ),
            ],
        )
        ir = compile_to_ir(p)
        # 4 covariant wiring flows + 3 feedback flows + 1 input flow = 8
        assert len(ir.flows) == 8

    def test_input_flows(self):
        agent = reactive_decision_agent()
        p = Pattern(
            name="Test",
            game=agent,
            inputs=[
                PatternInput(
                    name="Sensor",
                    input_type=InputType.SENSOR,
                    target_game="Context Builder",
                    flow_label="Event",
                ),
            ],
        )
        ir = compile_to_ir(p)
        sensor_flows = [f for f in ir.flows if f.source == "Sensor"]
        assert len(sensor_flows) == 1
        assert sensor_flows[0].target == "Context Builder"
        assert sensor_flows[0].label == "Event"

    def test_feedback_flows(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        feedback_flows = [f for f in ir.flows if f.is_feedback]
        assert len(feedback_flows) == 3

    def test_composition_type(self):
        agent = reactive_decision_agent()
        p = Pattern(
            name="Test",
            game=agent,
            composition_type=CompositionType.FEEDBACK,
        )
        ir = compile_to_ir(p)
        assert ir.composition_type == CompositionType.FEEDBACK

    def test_source_is_dsl(self):
        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        assert ir.source_canvas == "dsl"


class TestCompileVerification:
    """Verify that DSL-compiled IR passes through the verification engine."""

    def test_zero_errors(self):
        """Reactive Decision Pattern from DSL should have 0 verification errors."""
        from ogs.verification.engine import verify

        agent = reactive_decision_agent()
        p = Pattern(
            name="Reactive Decision Pattern",
            game=agent,
            inputs=[
                PatternInput(
                    name="Sensor Input",
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
                    name="History Initialization",
                    input_type=InputType.INITIALIZATION,
                    target_game="History",
                    flow_label="Primitive",
                ),
                PatternInput(
                    name="Policy Initialization",
                    input_type=InputType.INITIALIZATION,
                    target_game="Policy",
                    flow_label="Primitive",
                ),
            ],
            composition_type=CompositionType.FEEDBACK,
        )
        ir = compile_to_ir(p)
        report = verify(ir)
        assert report.errors == 0, (
            f"Expected 0 errors, got {report.errors}: "
            + "; ".join(f.message for f in report.findings if not f.passed)
        )


class TestCompileCorecursive:
    """Test compilation of patterns with corecursive loops."""

    def test_corecursive_flows_generated(self):
        g = DecisionGame(
            name="D",
            interface=Signature(
                x=(port("Obs"),),
                y=(port("Choice"),),
                r=(port("Utility"),),
                s=(port("Coutility"),),
            ),
        )
        cl = g.corecursive(
            [
                Flow(
                    source_game="D",
                    source_port="Choice",
                    target_game="D",
                    target_port="Obs",
                ),
            ]
        )
        p = Pattern(
            name="Test Corec", game=cl, composition_type=CompositionType.CORECURSIVE
        )
        ir = compile_to_ir(p)
        corec_flows = [f for f in ir.flows if f.is_corecursive]
        assert len(corec_flows) == 1
        assert corec_flows[0].label == "Choice"
        assert corec_flows[0].is_corecursive is True

    def test_terminal_conditions_pass_through(self):
        g = DecisionGame(name="D", interface=Signature())
        p = Pattern(
            name="Test",
            game=g,
            terminal_conditions=[
                TerminalCondition(
                    name="Done",
                    actions={"D": "ACCEPT"},
                    outcome="success",
                ),
            ],
        )
        ir = compile_to_ir(p)
        assert ir.terminal_conditions is not None
        assert len(ir.terminal_conditions) == 1
        assert ir.terminal_conditions[0].name == "Done"
        assert ir.terminal_conditions[0].outcome == "success"

    def test_action_spaces_pass_through(self):
        g = DecisionGame(name="D", interface=Signature())
        p = Pattern(
            name="Test",
            game=g,
            action_spaces=[
                ActionSpace(game="D", actions=["A", "B"]),
            ],
        )
        ir = compile_to_ir(p)
        assert ir.action_spaces is not None
        assert len(ir.action_spaces) == 1
        assert ir.action_spaces[0].actions == ["A", "B"]

    def test_initializations_pass_through(self):
        g = DecisionGame(name="D", interface=Signature())
        p = Pattern(
            name="Test",
            game=g,
            initializations=[
                StateInitialization(symbol="h_0", space="H", game="History"),
            ],
        )
        ir = compile_to_ir(p)
        assert ir.initialization is not None
        assert len(ir.initialization) == 1
        assert ir.initialization[0].symbol == "h_0"


class TestCompileRoundTrip:
    """Test that DSL IR can be serialized and deserialized."""

    def test_json_round_trip(self, tmp_path):
        from ogs.ir.serialization import IRDocument, IRMetadata, load_ir, save_ir

        agent = reactive_decision_agent()
        p = Pattern(name="Test", game=agent)
        ir = compile_to_ir(p)
        doc = IRDocument(
            patterns=[ir],
            metadata=IRMetadata(source_canvases=["dsl"]),
        )

        out_path = tmp_path / "test.json"
        save_ir(doc, out_path)
        loaded = load_ir(out_path)

        assert len(loaded.patterns) == 1
        assert loaded.patterns[0].name == "Test"
        assert len(loaded.patterns[0].games) == 5


# ---------------------------------------------------------------------------
# Operator syntax
# ---------------------------------------------------------------------------


class TestOperatorSyntax:
    def test_rshift(self):
        g1 = CovariantFunction(name="F1", interface=Signature(y=(port("X"),)))
        g2 = CovariantFunction(name="F2", interface=Signature(x=(port("X"),)))
        result = g1 >> g2
        assert isinstance(result, SequentialComposition)

    def test_pipe(self):
        g1 = CovariantFunction(name="F1", interface=Signature())
        g2 = CovariantFunction(name="F2", interface=Signature())
        result = g1 | g2
        assert isinstance(result, ParallelComposition)

    def test_chained_operators(self):
        g1 = CovariantFunction(name="F1", interface=Signature(y=(port("X"),)))
        g2 = CovariantFunction(
            name="F2", interface=Signature(x=(port("X"),), y=(port("Y"),))
        )
        g3 = CovariantFunction(name="F3", interface=Signature(x=(port("Y"),)))
        result = g1 >> g2 >> g3
        assert isinstance(result, SequentialComposition)
        assert len(result.flatten()) == 3


# ---------------------------------------------------------------------------
# Hierarchy extraction
# ---------------------------------------------------------------------------


def _collect_leaves(node: HierarchyNodeIR) -> list[str]:
    """Collect all leaf game names from a hierarchy tree."""
    if node.block_name is not None:
        return [node.block_name]
    result = []
    for c in node.children:
        result.extend(_collect_leaves(c))
    return result


class TestHierarchyExtraction:
    """Verify that composition hierarchy is correctly extracted and flattened."""

    def _compile_rd(self):
        agent = reactive_decision_agent()
        return compile_to_ir(Pattern(name="Reactive Decision", game=agent))

    def test_reactive_decision_has_hierarchy(self):
        ir = self._compile_rd()
        assert ir.hierarchy is not None

    def test_reactive_decision_root_is_feedback(self):
        ir = self._compile_rd()
        assert ir.hierarchy is not None
        assert ir.hierarchy.composition_type == CompositionType.FEEDBACK

    def test_reactive_decision_sequential_flattened(self):
        """The >>-chain of 5 games should flatten into a single sequential group."""
        ir = self._compile_rd()
        assert ir.hierarchy is not None
        seq = ir.hierarchy.children[0]
        assert seq.composition_type == CompositionType.SEQUENTIAL
        # All 5 games should be direct children (flattened from binary tree)
        assert len(seq.children) == 5
        assert all(c.game_name is not None for c in seq.children)

    def test_reactive_decision_leaf_names_match_games(self):
        ir = self._compile_rd()
        assert ir.hierarchy is not None
        leaf_names = set(_collect_leaves(ir.hierarchy))
        game_names = {g.name for g in ir.games}
        assert leaf_names == game_names

    def test_hierarchy_serialization_roundtrip(self):
        """HierarchyNodeIR should survive JSON serialization."""
        ir = self._compile_rd()
        assert ir.hierarchy is not None
        json_str = ir.hierarchy.model_dump_json()
        restored = HierarchyNodeIR.model_validate_json(json_str)
        assert restored.id == ir.hierarchy.id
        assert len(_collect_leaves(restored)) == len(ir.games)

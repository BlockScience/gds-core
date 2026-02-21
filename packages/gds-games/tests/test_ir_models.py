"""Tests for IR data models."""

import pytest
from pydantic import ValidationError

from ogs.ir.models import (
    ActionSpaceIR,
    CompositionType,
    FlowDirection,
    FlowIR,
    FlowType,
    GameType,
    InputIR,
    InputType,
    OpenGameIR,
    PatternIR,
    StateInitializationIR,
    TerminalConditionIR,
)


def _make_game(**overrides) -> OpenGameIR:
    defaults: dict[str, object] = dict(
        name="Test Game",
        game_type=GameType.DECISION,
        signature=("X", "Y", "R", "S"),
        color_code=1,
    )
    defaults.update(overrides)
    return OpenGameIR(**defaults)  # type: ignore[arg-type]


def _make_flow(**overrides) -> FlowIR:
    defaults: dict[str, object] = dict(
        source="A",
        target="B",
        label="test flow",
        flow_type=FlowType.OBSERVATION,
        direction=FlowDirection.COVARIANT,
    )
    defaults.update(overrides)
    return FlowIR(**defaults)  # type: ignore[arg-type]


class TestOpenGameIR:
    def test_create_minimal(self):
        game = _make_game()
        assert game.name == "Test Game"
        assert game.game_type == GameType.DECISION
        assert game.signature == ("X", "Y", "R", "S")
        assert game.logic == ""
        assert game.constraints == []

    def test_create_full(self):
        game = _make_game(
            logic="u = g0(x_T, x_C; p)",
            gds_function="g0",
            constraints=["u in U(x_T, x_C)"],
            parent_pattern="Reactive Decision Pattern",
            contained_nodes=["logic card", "label"],
        )
        assert game.gds_function == "g0"
        assert len(game.constraints) == 1

    def test_json_round_trip(self):
        game = _make_game(logic="test logic")
        json_str = game.model_dump_json()
        restored = OpenGameIR.model_validate_json(json_str)
        assert restored == game

    def test_invalid_game_type(self):
        with pytest.raises(ValidationError):
            _make_game(game_type="invalid_type")

    def test_all_game_types(self):
        for gt in GameType:
            game = _make_game(game_type=gt)
            assert game.game_type == gt


class TestFlowIR:
    def test_create(self):
        flow = _make_flow()
        assert flow.source == "A"
        assert flow.is_feedback is False

    def test_contravariant(self):
        flow = _make_flow(
            direction=FlowDirection.CONTRAVARIANT,
            flow_type=FlowType.UTILITY_COUTILITY,
            is_feedback=True,
        )
        assert flow.direction == FlowDirection.CONTRAVARIANT
        assert flow.is_feedback is True

    def test_json_round_trip(self):
        flow = _make_flow(is_feedback=True)
        restored = FlowIR.model_validate_json(flow.model_dump_json())
        assert restored == flow


class TestInputIR:
    def test_create(self):
        inp = InputIR(
            name="Sensor Input",
            input_type=InputType.SENSOR,
            schema_hint="(X_T, x_T in X_T)",
            shape="pill",
        )
        assert inp.name == "Sensor Input"
        assert inp.input_type == InputType.SENSOR

    def test_json_round_trip(self):
        inp = InputIR(name="Test", input_type=InputType.RESOURCE)
        restored = InputIR.model_validate_json(inp.model_dump_json())
        assert restored == inp


class TestPatternIR:
    def test_create_minimal(self):
        pattern = PatternIR(
            name="Test Pattern",
            composition_type=CompositionType.SEQUENTIAL,
            source_canvas="test.canvas",
        )
        assert pattern.games == []
        assert pattern.flows == []
        assert pattern.inputs == []
        assert pattern.terminal_conditions is None

    def test_create_full(self):
        pattern = PatternIR(
            name="Reactive Decision Pattern",
            games=[_make_game()],
            flows=[_make_flow()],
            inputs=[InputIR(name="Sensor", input_type=InputType.SENSOR)],
            composition_type=CompositionType.FEEDBACK,
            terminal_conditions=[
                TerminalConditionIR(
                    name="Agreement",
                    actions={"Agent 1": "ACCEPT"},
                    outcome="success",
                ),
            ],
            action_spaces=[
                ActionSpaceIR(game="Agent 1", actions=["ACCEPT", "REJECT"]),
            ],
            initialization=[
                StateInitializationIR(
                    symbol="h0", space="H", description="Initial history"
                ),
            ],
            source_canvas="reactive.canvas",
            source_spec_notes="notes.md",
        )
        assert len(pattern.games) == 1
        assert pattern.composition_type == CompositionType.FEEDBACK
        assert pattern.terminal_conditions is not None
        assert pattern.action_spaces is not None
        assert pattern.initialization is not None
        assert len(pattern.terminal_conditions) == 1
        assert len(pattern.action_spaces) == 1
        assert len(pattern.initialization) == 1

    def test_json_round_trip(self):
        pattern = PatternIR(
            name="Test",
            games=[_make_game()],
            flows=[_make_flow()],
            composition_type=CompositionType.FEEDBACK,
            source_canvas="test.canvas",
        )
        json_str = pattern.model_dump_json()
        restored = PatternIR.model_validate_json(json_str)
        assert restored.name == pattern.name
        assert len(restored.games) == 1
        assert restored.games[0].signature == ("X", "Y", "R", "S")


class TestFlowIRCorecursive:
    def test_default_false(self):
        flow = _make_flow()
        assert flow.is_corecursive is False

    def test_set_true(self):
        flow = _make_flow(is_corecursive=True)
        assert flow.is_corecursive is True

    def test_json_round_trip(self):
        flow = _make_flow(is_corecursive=True)
        restored = FlowIR.model_validate_json(flow.model_dump_json())
        assert restored.is_corecursive is True


class TestTerminalConditionIR:
    def test_create(self):
        tc = TerminalConditionIR(
            name="Agreement",
            actions={"Agent 1": "ACCEPT", "Agent 2": "PROPOSE"},
            outcome="success",
            description="Negotiation succeeds",
            payoff_description="Both agents receive payoff",
        )
        assert tc.name == "Agreement"
        assert tc.outcome == "success"
        assert tc.actions["Agent 1"] == "ACCEPT"

    def test_json_round_trip(self):
        tc = TerminalConditionIR(
            name="Failure",
            actions={"Agent 1": "REJECT"},
            outcome="failure",
        )
        restored = TerminalConditionIR.model_validate_json(tc.model_dump_json())
        assert restored == tc


class TestActionSpaceIR:
    def test_create(self):
        a = ActionSpaceIR(
            game="Agent 1",
            actions=["ACCEPT", "REJECT", "PROPOSE"],
            constraints=["Cannot ACCEPT in round 1"],
        )
        assert a.game == "Agent 1"
        assert len(a.actions) == 3
        assert len(a.constraints) == 1

    def test_default_constraints(self):
        a = ActionSpaceIR(game="Agent 1", actions=["ACCEPT"])
        assert a.constraints == []

    def test_json_round_trip(self):
        a = ActionSpaceIR(game="Agent 1", actions=["ACCEPT", "REJECT"])
        restored = ActionSpaceIR.model_validate_json(a.model_dump_json())
        assert restored == a


class TestStateInitializationIR:
    def test_create(self):
        s = StateInitializationIR(
            symbol="h_0",
            space="H",
            description="Initial history",
            game="History",
        )
        assert s.symbol == "h_0"
        assert s.space == "H"
        assert s.game == "History"

    def test_defaults(self):
        s = StateInitializationIR(symbol="x", space="X")
        assert s.description == ""
        assert s.game == ""

    def test_json_round_trip(self):
        s = StateInitializationIR(symbol="h_0", space="H")
        restored = StateInitializationIR.model_validate_json(s.model_dump_json())
        assert restored == s

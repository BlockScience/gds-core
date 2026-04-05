"""Tests for Pattern.compile() and Pattern.compile_system() convenience methods."""

from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds.types.interface import port
from gds_domains.games.dsl.games import CovariantFunction, DecisionGame
from gds_domains.games.dsl.pattern import Pattern, PatternInput
from gds_domains.games.dsl.types import CompositionType, InputType, Signature


def _sequential_pattern() -> Pattern:
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
    return Pattern(
        name="Simple Sequential",
        game=a >> b,
        composition_type=CompositionType.SEQUENTIAL,
    )


def _pattern_with_inputs() -> Pattern:
    agent = DecisionGame(
        name="Agent",
        signature=Signature(
            x=(port("Observation"),),
            y=(port("Action"),),
            r=(port("Reward"),),
        ),
    )
    return Pattern(
        name="Agent With Input",
        game=agent,
        inputs=[
            PatternInput(
                name="External Signal",
                input_type=InputType.EXTERNAL_WORLD,
                target_game="Agent",
                flow_label="Observation",
            ),
        ],
        composition_type=CompositionType.SEQUENTIAL,
    )


class TestPatternCompile:
    """Pattern.compile() returns a GDSSpec."""

    def test_returns_gds_spec(self):
        spec = _sequential_pattern().compile()
        assert isinstance(spec, GDSSpec)

    def test_spec_name_matches_pattern(self):
        spec = _sequential_pattern().compile()
        assert spec.name == "Simple Sequential"

    def test_spec_contains_blocks(self):
        spec = _sequential_pattern().compile()
        assert len(spec.blocks) >= 2

    def test_compile_with_inputs(self):
        spec = _pattern_with_inputs().compile()
        assert isinstance(spec, GDSSpec)
        assert "External Signal" in spec.blocks

    def test_matches_standalone_function(self):
        """compile() produces the same result as calling the standalone function."""
        from gds_domains.games.dsl.spec_bridge import compile_pattern_to_spec

        pattern = _sequential_pattern()
        assert pattern.compile().name == compile_pattern_to_spec(pattern).name


class TestPatternCompileSystem:
    """Pattern.compile_system() returns a SystemIR."""

    def test_returns_system_ir(self):
        sir = _sequential_pattern().compile_system()
        assert isinstance(sir, SystemIR)

    def test_system_ir_has_blocks(self):
        sir = _sequential_pattern().compile_system()
        assert len(sir.blocks) >= 2

    def test_compile_system_with_inputs(self):
        sir = _pattern_with_inputs().compile_system()
        assert isinstance(sir, SystemIR)

    def test_matches_standalone_pipeline(self):
        """compile_system() produces the same result as the standalone pipeline."""
        from gds_domains.games.dsl.compile import compile_to_ir

        pattern = _sequential_pattern()
        expected = compile_to_ir(pattern).to_system_ir()
        result = pattern.compile_system()
        assert len(result.blocks) == len(expected.blocks)
        assert len(result.wirings) == len(expected.wirings)

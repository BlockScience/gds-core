"""Tests for PatternIR.to_system_ir() projection to GDS SystemIR."""

from gds.ir.models import BlockIR, InputIR, SystemIR, WiringIR
from gds.ir.models import CompositionType as GDSCompositionType
from ogs.dsl.compile import compile_to_ir
from ogs.dsl.library import reactive_decision_agent
from ogs.dsl.pattern import Pattern
from ogs.ir.models import CompositionType


def _build_reactive_decision_ir():
    agent = reactive_decision_agent()
    p = Pattern(
        name="Reactive Decision",
        game=agent,
        composition_type=CompositionType.FEEDBACK,
    )
    return compile_to_ir(p)


class TestToSystemIR:
    """Verify that to_system_ir() produces valid GDS SystemIR."""

    def test_returns_system_ir(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert isinstance(system, SystemIR)

    def test_name_preserved(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert system.name == pattern_ir.name

    def test_block_count_matches(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert len(system.blocks) == len(pattern_ir.games)

    def test_blocks_are_block_ir(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        for block in system.blocks:
            assert isinstance(block, BlockIR)

    def test_wiring_count_matches(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert len(system.wirings) == len(pattern_ir.flows)

    def test_wirings_are_wiring_ir(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        for wiring in system.wirings:
            assert isinstance(wiring, WiringIR)

    def test_composition_type_is_gds(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert isinstance(system.composition_type, GDSCompositionType)

    def test_input_count_matches(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert len(system.inputs) == len(pattern_ir.inputs)

    def test_inputs_are_typed_input_ir(self):
        """Projected inputs should be GDS InputIR instances, not dicts."""
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        for inp in system.inputs:
            assert isinstance(inp, InputIR)

    def test_feedback_maps_to_feedback(self):
        """Reactive decision uses FEEDBACK — should map directly."""
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        assert system.composition_type == GDSCompositionType.FEEDBACK

    def test_block_metadata_has_constraints_and_tags(self):
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        for block in system.blocks:
            assert "constraints" in block.metadata
            assert "tags" in block.metadata

    def test_corecursive_flows_map_to_temporal(self):
        """Flows with is_corecursive=True should map to is_temporal=True."""
        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        for flow, wiring in zip(pattern_ir.flows, system.wirings):
            assert wiring.is_temporal == flow.is_corecursive


class TestGDSChecksViaProjection:
    """Verify that GDS generic checks pass on projected SystemIR."""

    def test_gds_checks_pass(self):
        from gds.verification.engine import ALL_CHECKS as GDS_ALL_CHECKS

        pattern_ir = _build_reactive_decision_ir()
        system = pattern_ir.to_system_ir()
        findings = []
        for check_fn in GDS_ALL_CHECKS:
            findings.extend(check_fn(system))
        errors = [f for f in findings if not f.passed and f.severity.value == "error"]
        assert errors == [], f"GDS checks found errors: {errors}"

    def test_verify_with_gds_checks(self):
        """Test the include_gds_checks=True parameter on OGS verify()."""
        from ogs.verification.engine import verify

        pattern_ir = _build_reactive_decision_ir()
        report = verify(pattern_ir, include_gds_checks=True)
        errors = [
            f for f in report.findings if not f.passed and f.severity.value == "error"
        ]
        assert errors == [], f"Verification with GDS checks found errors: {errors}"

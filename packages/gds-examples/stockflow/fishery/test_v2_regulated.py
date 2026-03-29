"""Tests for the Gordon-Schaefer fishery V2 (regulated) variant.

Exercises the ControlAction output map and SC-010 routing check.
"""

from gds.blocks.roles import ControlAction
from gds.verification.spec_checks import check_control_action_routing

from fishery.v2_regulated import build_v2_canonical, build_v2_spec, catch_observation


class TestV2Spec:
    def test_build_v2_spec(self):
        spec = build_v2_spec()
        errors = spec.validate_spec()
        assert errors == []

    def test_catch_observation_is_control_action(self):
        assert isinstance(catch_observation, ControlAction)

    def test_catch_observation_has_output(self):
        ports = [p.name for p in catch_observation.interface.forward_out]
        assert "Observed Total Catch" in ports

    def test_catch_observation_reads_state(self):
        ports = [p.name for p in catch_observation.interface.forward_in]
        assert "Total Harvest" in ports
        assert "Population Level" in ports


class TestV2Canonical:
    def test_canonical_has_control_blocks(self):
        canonical = build_v2_canonical()
        assert "Catch Observation" in canonical.control_blocks

    def test_canonical_has_output_ports(self):
        canonical = build_v2_canonical()
        assert len(canonical.output_ports) >= 1
        block_names = [name for name, _ in canonical.output_ports]
        assert "Catch Observation" in block_names

    def test_formula_includes_output_map(self):
        canonical = build_v2_canonical()
        formula = canonical.formula()
        assert "y = C" in formula
        assert "(x, d)" in formula

    def test_output_map_has_observes(self):
        """output_map captures the (entity, var) pairs from observes."""
        canonical = build_v2_canonical()
        assert len(canonical.output_map) == 1
        name, observes = canonical.output_map[0]
        assert name == "Catch Observation"
        assert ("Fish Population", "level") in observes


class TestV2Verification:
    def test_sc010_passes(self):
        """SC-010: Catch Observation does not wire to Policy in SpecWiring."""
        spec = build_v2_spec()
        findings = check_control_action_routing(spec)
        assert all(f.passed for f in findings)

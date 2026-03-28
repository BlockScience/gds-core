"""Tests for the GDS Ecosystem self-model."""

from gds import project_canonical, verify
from software.gds_ecosystem.model import build_model, build_spec, build_system


class TestEcosystemModel:
    def test_model_builds(self):
        model = build_model()
        assert model.name == "GDS Ecosystem"
        assert len(model.components) == 9
        assert len(model.connectors) == 8

    def test_spec_compiles(self):
        spec = build_spec()
        assert spec.name == "GDS Ecosystem"
        assert len(spec.blocks) == 9
        errors = spec.validate_spec()
        assert errors == []

    def test_system_compiles(self):
        ir = build_system()
        assert ir.name == "GDS Ecosystem"
        assert len(ir.blocks) == 9

    def test_canonical_is_stateless(self):
        """The ecosystem has no state — h = g."""
        spec = build_spec()
        canonical = project_canonical(spec)
        assert canonical.mechanism_blocks == ()
        assert canonical.state_variables == ()
        assert len(canonical.boundary_blocks) == 3  # providers
        assert len(canonical.policy_blocks) == 6  # consumers

    def test_providers_are_boundary(self):
        """Provider packages become BoundaryActions."""
        spec = build_spec()
        canonical = project_canonical(spec)
        providers = set(canonical.boundary_blocks)
        assert "gds-framework" in providers
        assert "gds-sim" in providers
        assert "gds-continuous" in providers

    def test_consumers_are_policy(self):
        """Consumer packages become Policies."""
        spec = build_spec()
        canonical = project_canonical(spec)
        consumers = set(canonical.policy_blocks)
        assert "gds-games" in consumers
        assert "gds-analysis" in consumers
        assert "gds-symbolic" in consumers

    def test_verification(self):
        """Generic verification runs (G-002 expected on boundary/terminal)."""
        ir = build_system()
        report = verify(ir)
        # G-002 fires on boundary (no inputs) and terminal (no outputs)
        # blocks — expected for a pure dependency graph
        g002 = [f for f in report.findings if f.check_id == "G-002"]
        assert len(g002) > 0  # expected failures

    def test_mermaid_output(self):
        """Mermaid diagram generates without error."""
        from gds_viz import system_to_mermaid

        ir = build_system()
        mermaid = system_to_mermaid(ir)
        assert "gds-framework" in mermaid or "gds_framework" in mermaid
        assert "GDSSpec" in mermaid

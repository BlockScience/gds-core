"""Tests for the 'Build Your First Model' getting started guide.

Each stage is tested independently. Tests verify that each stage
produces valid GDS output without errors.
"""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.ir.models import FlowDirection
from gds.verification.engine import verify
from gds.verification.generic_checks import (
    check_g004_dangling_wirings,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
)

# ══════════════════════════════════════════════════════════════
# Stage 1: Minimal Model
# ══════════════════════════════════════════════════════════════


class TestStage1Minimal:
    def test_spec_builds(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        assert spec.name == "Minimal Thermostat"

    def test_spec_has_one_entity(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        assert len(spec.entities) == 1
        assert "Room" in spec.entities

    def test_spec_has_two_blocks(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        assert len(spec.blocks) == 2
        assert "Heater" in spec.blocks
        assert "Update Temperature" in spec.blocks

    def test_block_roles(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        assert isinstance(spec.blocks["Heater"], BoundaryAction)
        assert isinstance(spec.blocks["Update Temperature"], Mechanism)

    def test_spec_validates(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_system_compiles(self):
        from guides.getting_started.stage1_minimal import build_system

        system = build_system()
        assert system.name == "Minimal Thermostat"
        assert len(system.blocks) == 2

    def test_system_has_wiring(self):
        from guides.getting_started.stage1_minimal import build_system

        system = build_system()
        assert len(system.wirings) >= 1

    def test_mechanism_updates_room(self):
        from guides.getting_started.stage1_minimal import update_temperature

        assert update_temperature.updates == [("Room", "temperature")]

    def test_heater_has_no_forward_in(self):
        from guides.getting_started.stage1_minimal import heater

        assert heater.interface.forward_in == ()


# ══════════════════════════════════════════════════════════════
# Stage 2: Feedback
# ══════════════════════════════════════════════════════════════


class TestStage2Feedback:
    def test_spec_builds(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        assert spec.name == "Thermostat with Feedback"

    def test_spec_has_four_blocks(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        assert len(spec.blocks) == 4

    def test_spec_has_policy_blocks(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        assert isinstance(spec.blocks["Sensor"], Policy)
        assert isinstance(spec.blocks["Controller"], Policy)

    def test_spec_has_setpoint_parameter(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        assert "setpoint" in spec.parameters

    def test_spec_validates(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_system_compiles(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        assert system.name == "Thermostat with Feedback"
        assert len(system.blocks) == 4

    def test_system_has_temporal_wiring(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 1

    def test_temporal_wiring_is_covariant(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert temporal[0].direction == FlowDirection.COVARIANT

    def test_temporal_wiring_connects_mechanism_to_sensor(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert temporal[0].source == "Update Temperature"
        assert temporal[0].target == "Sensor"

    def test_no_feedback_wirings(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 0


# ══════════════════════════════════════════════════════════════
# Stage 3: DSL
# ══════════════════════════════════════════════════════════════


class TestStage3DSL:
    def test_model_builds(self):
        from guides.getting_started.stage3_dsl import build_model

        model = build_model()
        assert model.name == "Thermostat DSL"

    def test_model_has_one_state(self):
        from guides.getting_started.stage3_dsl import build_model

        model = build_model()
        assert len(model.states) == 1
        assert model.states[0].name == "temperature"

    def test_model_has_one_input(self):
        from guides.getting_started.stage3_dsl import build_model

        model = build_model()
        assert len(model.inputs) == 1
        assert model.inputs[0].name == "heater"

    def test_model_has_one_sensor(self):
        from guides.getting_started.stage3_dsl import build_model

        model = build_model()
        assert len(model.sensors) == 1
        assert model.sensors[0].name == "temp_sensor"

    def test_model_has_one_controller(self):
        from guides.getting_started.stage3_dsl import build_model

        model = build_model()
        assert len(model.controllers) == 1
        assert model.controllers[0].name == "thermo"

    def test_spec_compiles(self):
        from guides.getting_started.stage3_dsl import build_spec

        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_one_entity(self):
        from guides.getting_started.stage3_dsl import build_spec

        spec = build_spec()
        assert len(spec.entities) == 1
        assert "temperature" in spec.entities

    def test_spec_has_four_blocks(self):
        from guides.getting_started.stage3_dsl import build_spec

        spec = build_spec()
        assert len(spec.blocks) == 4

    def test_spec_block_roles(self):
        from guides.getting_started.stage3_dsl import build_spec

        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 1
        assert len(policies) == 2
        assert len(mechanisms) == 1

    def test_system_compiles(self):
        from guides.getting_started.stage3_dsl import build_system

        system = build_system()
        assert system.name == "Thermostat DSL"

    def test_system_has_temporal_loop(self):
        from guides.getting_started.stage3_dsl import build_system

        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 1

    def test_canonical_projection(self):
        from guides.getting_started.stage3_dsl import build_canonical

        canonical = build_canonical()
        assert len(canonical.state_variables) == 1
        assert len(canonical.boundary_blocks) == 1
        assert len(canonical.mechanism_blocks) == 1
        assert len(canonical.policy_blocks) == 2


# ══════════════════════════════════════════════════════════════
# Stage 4: Verification and Visualization
# ══════════════════════════════════════════════════════════════


class TestStage4VerifyViz:
    def test_generic_checks_pass(self):
        from guides.getting_started.stage3_dsl import build_system
        from guides.getting_started.stage4_verify_viz import run_generic_checks

        system = build_system()
        report = run_generic_checks(system)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]

    def test_semantic_checks_produce_output(self):
        from guides.getting_started.stage3_dsl import build_spec
        from guides.getting_started.stage4_verify_viz import run_semantic_checks

        spec = build_spec()
        results = run_semantic_checks(spec)
        assert len(results) > 0

    def test_semantic_checks_all_pass(self):
        from guides.getting_started.stage3_dsl import build_spec
        from guides.getting_started.stage4_verify_viz import run_semantic_checks

        spec = build_spec()
        results = run_semantic_checks(spec)
        failures = [r for r in results if "FAIL" in r]
        assert failures == [], f"Semantic check failures: {failures}"

    def test_structural_view_is_mermaid(self):
        from guides.getting_started.stage3_dsl import build_system
        from guides.getting_started.stage4_verify_viz import (
            generate_structural_view,
        )

        system = build_system()
        mermaid = generate_structural_view(system)
        assert "flowchart" in mermaid
        assert "heater" in mermaid.lower() or "temp_sensor" in mermaid.lower()

    def test_architecture_view_is_mermaid(self):
        from guides.getting_started.stage3_dsl import build_spec
        from guides.getting_started.stage4_verify_viz import (
            generate_architecture_view,
        )

        spec = build_spec()
        mermaid = generate_architecture_view(spec)
        assert "flowchart" in mermaid
        assert "subgraph" in mermaid

    def test_canonical_view_is_mermaid(self):
        from guides.getting_started.stage3_dsl import build_spec
        from guides.getting_started.stage4_verify_viz import (
            generate_canonical_view,
        )

        spec = build_spec()
        mermaid = generate_canonical_view(spec)
        assert "flowchart" in mermaid
        assert "X_t" in mermaid


# ══════════════════════════════════════════════════════════════
# Stage 5: Query
# ══════════════════════════════════════════════════════════════


class TestStage5Query:
    def test_query_builds(self):
        from guides.getting_started.stage5_query import build_query

        query = build_query()
        assert query is not None

    def test_entity_update_map(self):
        from guides.getting_started.stage5_query import (
            build_query,
            show_entity_updates,
        )

        query = build_query()
        updates = show_entity_updates(query)
        assert "temperature" in updates
        assert "value" in updates["temperature"]
        assert len(updates["temperature"]["value"]) == 1

    def test_blocks_by_role(self):
        from guides.getting_started.stage5_query import (
            build_query,
            show_blocks_by_role,
        )

        query = build_query()
        by_role = show_blocks_by_role(query)
        assert len(by_role["boundary"]) == 1
        assert len(by_role["policy"]) == 2
        assert len(by_role["mechanism"]) == 1

    def test_causal_chain(self):
        from guides.getting_started.stage5_query import (
            build_query,
            show_causal_chain,
        )

        query = build_query()
        affecting = show_causal_chain(query, "temperature", "value")
        assert "temperature Dynamics" in affecting

    def test_dependency_graph(self):
        from guides.getting_started.stage5_query import (
            build_query,
            show_dependency_graph,
        )

        query = build_query()
        graph = show_dependency_graph(query)
        # The graph should have at least one entry
        assert len(graph) >= 1


# ══════════════════════════════════════════════════════════════
# Cross-stage: GDS verification on manual stages too
# ══════════════════════════════════════════════════════════════


class TestCrossStageVerification:
    """Verify that manually-built models (stages 1 and 2) also pass
    the same structural and semantic checks as the DSL model."""

    def test_stage1_generic_checks(self):
        from guides.getting_started.stage1_minimal import build_system

        system = build_system()
        checks = [
            check_g004_dangling_wirings,
            check_g006_covariant_acyclicity,
        ]
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]

    def test_stage1_completeness(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_stage1_determinism(self):
        from guides.getting_started.stage1_minimal import build_spec

        spec = build_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_stage2_generic_checks(self):
        from guides.getting_started.stage2_feedback import build_system

        system = build_system()
        checks = [
            check_g004_dangling_wirings,
            check_g006_covariant_acyclicity,
        ]
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]

    def test_stage2_completeness(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_stage2_canonical_wellformedness(self):
        from guides.getting_started.stage2_feedback import build_spec

        spec = build_spec()
        findings = check_canonical_wellformedness(spec)
        assert all(f.passed for f in findings)

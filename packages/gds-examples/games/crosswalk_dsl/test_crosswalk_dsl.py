"""Tests for the OGS DSL version of the Crosswalk Problem."""

from pathlib import Path
from tempfile import TemporaryDirectory

from crosswalk_dsl.model import (
    build_game,
    build_ir,
    build_pattern,
    build_spec,
    pedestrian_decision,
    run_reports,
    run_verification,
    safety_check,
    traffic_transition,
)
from ogs.dsl.composition import SequentialComposition
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.ir.models import (
    CompositionType,
    GameType,
    PatternIR,
)
from ogs.reports.generator import (
    generate_implementation_checklist,
    generate_interface_contracts,
    generate_system_overview,
    generate_verification_summary,
)
from ogs.verification.findings import VerificationReport
from ogs.viz import (
    architecture_by_domain_to_mermaid,
    architecture_by_role_to_mermaid,
    flow_topology_to_mermaid,
    generate_all_views,
    hierarchy_to_mermaid,
    structural_to_mermaid,
    terminal_conditions_to_mermaid,
)

# ======================================================================
# TestModel -- atomic games and their properties
# ======================================================================


class TestModel:
    """Test the atomic game definitions."""

    def test_pedestrian_is_decision_game(self):
        assert isinstance(pedestrian_decision, DecisionGame)
        assert pedestrian_decision.game_type == GameType.DECISION

    def test_safety_check_is_covariant_function(self):
        assert isinstance(safety_check, CovariantFunction)
        assert safety_check.game_type == GameType.FUNCTION_COVARIANT

    def test_traffic_transition_is_covariant_function(self):
        assert isinstance(traffic_transition, CovariantFunction)
        assert traffic_transition.game_type == GameType.FUNCTION_COVARIANT

    def test_pedestrian_signature(self):
        sig = pedestrian_decision.signature
        assert len(sig.x) == 1
        assert len(sig.y) == 1
        assert len(sig.r) == 1
        assert len(sig.s) == 1
        assert sig.x[0].name == "Observation Signal"
        assert sig.y[0].name == "Crossing Decision"
        assert sig.r[0].name == "Traffic Outcome"
        assert sig.s[0].name == "Pedestrian Experience"

    def test_safety_check_signature(self):
        sig = safety_check.signature
        assert len(sig.x) == 1
        assert len(sig.y) == 1
        assert sig.r == ()
        assert sig.s == ()
        assert sig.x[0].name == "Crossing Decision"
        assert sig.y[0].name == "Safety Signal"

    def test_traffic_transition_signature(self):
        sig = traffic_transition.signature
        assert len(sig.x) == 1
        assert len(sig.y) == 1
        assert sig.r == ()
        assert sig.s == ()
        assert sig.x[0].name == "Safety Signal"
        assert sig.y[0].name == "Traffic Outcome"

    def test_domain_tags(self):
        assert pedestrian_decision.tags.get("domain") == "Pedestrian"
        assert safety_check.tags.get("domain") == "Infrastructure"
        assert traffic_transition.tags.get("domain") == "Environment"


# ======================================================================
# TestComposition -- game tree structure
# ======================================================================


class TestComposition:
    """Test the composition tree built by build_game()."""

    def test_build_game_returns_sequential(self):
        game = build_game()
        assert isinstance(game, SequentialComposition)

    def test_flatten_yields_three_games(self):
        game = build_game()
        flat = game.flatten()
        assert len(flat) == 3
        names = {g.name for g in flat}
        assert names == {
            "Pedestrian Decision",
            "Safety Check",
            "Traffic Transition",
        }

    def test_no_feedback_wiring(self):
        """Pure sequential -- no feedback loops in the crosswalk."""
        game = build_game()
        # SequentialComposition has no feedback_wiring attribute
        assert isinstance(game, SequentialComposition)


# ======================================================================
# TestCompile -- PatternIR and GDS spec generation
# ======================================================================


class TestCompile:
    """Test compilation to OGS IR and GDS spec."""

    def test_build_ir_returns_pattern_ir(self):
        ir = build_ir()
        assert isinstance(ir, PatternIR)
        assert ir.name == "Crosswalk Problem"

    def test_ir_has_three_games(self):
        ir = build_ir()
        assert len(ir.games) == 3

    def test_ir_has_flows(self):
        ir = build_ir()
        assert len(ir.flows) > 0

    def test_ir_composition_type(self):
        ir = build_ir()
        assert ir.composition_type == CompositionType.SEQUENTIAL

    def test_ir_has_terminal_conditions(self):
        ir = build_ir()
        assert ir.terminal_conditions is not None
        assert len(ir.terminal_conditions) == 3

    def test_terminal_condition_names(self):
        ir = build_ir()
        names = {tc.name for tc in ir.terminal_conditions}
        assert "Safe Crossing" in names
        assert "Jaywalking Accident" in names
        assert "No Crossing" in names

    def test_ir_has_action_spaces(self):
        ir = build_ir()
        assert ir.action_spaces is not None
        assert len(ir.action_spaces) == 1

    def test_action_space_actions(self):
        ir = build_ir()
        action_space = ir.action_spaces[0]
        assert action_space.game == "Pedestrian Decision"
        assert set(action_space.actions) == {"Cross", "Don't Cross"}

    def test_action_space_design_constraint(self):
        ir = build_ir()
        constraints = ir.action_spaces[0].constraints
        assert "crosswalk_location" in constraints

    def test_ir_has_inputs(self):
        ir = build_ir()
        assert len(ir.inputs) == 1
        assert ir.inputs[0].name == "Traffic Observation"

    def test_ir_has_hierarchy(self):
        ir = build_ir()
        assert ir.hierarchy is not None

    def test_build_spec_produces_gds_spec(self):
        spec = build_spec()
        assert spec.name == "Crosswalk Problem"

    def test_spec_has_blocks(self):
        spec = build_spec()
        # 3 atomic games as Policy + 1 PatternInput as BoundaryAction = 4
        assert len(spec.blocks) == 4

    def test_ir_to_system_ir(self):
        """PatternIR can project to GDS SystemIR for generic checks."""
        ir = build_ir()
        system_ir = ir.to_system_ir()
        assert system_ir.name == "Crosswalk Problem"
        assert len(system_ir.blocks) == 3

    def test_pattern_has_three_terminal_conditions(self):
        pattern = build_pattern()
        assert pattern.terminal_conditions is not None
        assert len(pattern.terminal_conditions) == 3

    def test_pattern_action_spaces(self):
        pattern = build_pattern()
        assert pattern.action_spaces is not None
        assert len(pattern.action_spaces) == 1
        assert set(pattern.action_spaces[0].actions) == {
            "Cross",
            "Don't Cross",
        }


# ======================================================================
# TestVerification -- OGS + GDS verification checks
# ======================================================================


class TestVerification:
    """Test OGS verification (domain + delegated GDS checks)."""

    def test_verification_runs(self):
        report = run_verification()
        assert isinstance(report, VerificationReport)

    def test_no_unexpected_exceptions(self):
        """OGS verification produces findings as structural annotations.
        We just verify the report completes without raising exceptions."""
        report = run_verification()
        assert isinstance(report, VerificationReport)

    def test_verification_has_findings(self):
        """Verification should produce some findings."""
        report = run_verification()
        assert len(report.findings) > 0

    def test_ogs_checks_included(self):
        """OGS-specific checks should produce findings."""
        report = run_verification()
        assert report.pattern_name == "Crosswalk Problem"


# ======================================================================
# TestVisualization -- OGS Mermaid views
# ======================================================================


class TestVisualization:
    """Test OGS visualization output."""

    def test_structural_view(self):
        ir = build_ir()
        mermaid = structural_to_mermaid(ir)
        assert "flowchart" in mermaid
        assert "Pedestrian Decision" in mermaid
        assert "Safety Check" in mermaid
        assert "Traffic Transition" in mermaid

    def test_architecture_by_role_view(self):
        ir = build_ir()
        mermaid = architecture_by_role_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_architecture_by_domain_view(self):
        ir = build_ir()
        mermaid = architecture_by_domain_to_mermaid(ir)
        assert "Pedestrian" in mermaid
        assert "Infrastructure" in mermaid
        assert "Environment" in mermaid

    def test_hierarchy_view(self):
        ir = build_ir()
        mermaid = hierarchy_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_flow_topology_view(self):
        ir = build_ir()
        mermaid = flow_topology_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_terminal_conditions_view(self):
        ir = build_ir()
        mermaid = terminal_conditions_to_mermaid(ir)
        assert "stateDiagram" in mermaid

    def test_generate_all_views(self):
        ir = build_ir()
        views = generate_all_views(ir)
        assert len(views) == 6
        assert all(isinstance(v, str) for v in views.values())


# ======================================================================
# TestReports -- OGS Markdown report generation
# ======================================================================


class TestReports:
    """Test OGS report generation."""

    def test_generate_reports_creates_files(self):
        with TemporaryDirectory() as tmpdir:
            paths = run_reports(Path(tmpdir))
            assert len(paths) > 0
            for p in paths:
                assert p.exists()
                assert p.suffix == ".md"

    def test_system_overview_report(self):
        ir = build_ir()
        content = generate_system_overview(ir)
        assert "Crosswalk Problem" in content

    def test_verification_summary_report(self):
        ir = build_ir()
        content = generate_verification_summary(ir)
        assert len(content) > 0

    def test_interface_contracts_report(self):
        ir = build_ir()
        content = generate_interface_contracts(ir)
        assert "Pedestrian Decision" in content

    def test_implementation_checklist_report(self):
        ir = build_ir()
        content = generate_implementation_checklist(ir)
        assert len(content) > 0

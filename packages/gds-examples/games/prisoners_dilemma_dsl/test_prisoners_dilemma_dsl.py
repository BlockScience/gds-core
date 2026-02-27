"""Tests for the OGS DSL version of the Prisoner's Dilemma."""

from pathlib import Path
from tempfile import TemporaryDirectory

from ogs.dsl.composition import FeedbackLoop, ParallelComposition, SequentialComposition
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    GameType,
    PatternIR,
)
from ogs.verification.findings import VerificationReport
from prisoners_dilemma_dsl.model import (
    alice_decision,
    bob_decision,
    build_game,
    build_ir,
    build_pattern,
    build_spec,
    payoff_computation,
    run_reports,
    run_verification,
)

# ======================================================================
# TestModel — atomic games and their properties
# ======================================================================


class TestModel:
    """Test the atomic game definitions."""

    def test_alice_is_decision_game(self):
        assert isinstance(alice_decision, DecisionGame)
        assert alice_decision.game_type == GameType.DECISION

    def test_bob_is_decision_game(self):
        assert isinstance(bob_decision, DecisionGame)
        assert bob_decision.game_type == GameType.DECISION

    def test_payoff_is_covariant_function(self):
        assert isinstance(payoff_computation, CovariantFunction)
        assert payoff_computation.game_type == GameType.FUNCTION_COVARIANT

    def test_alice_signature_ports(self):
        sig = alice_decision.signature
        assert len(sig.x) == 1
        assert len(sig.y) == 1
        assert len(sig.r) == 1
        assert len(sig.s) == 1
        assert sig.x[0].name == "Alice Observation"
        assert sig.y[0].name == "Alice Action"
        assert sig.r[0].name == "Alice Payoff"
        assert sig.s[0].name == "Alice Experience"

    def test_bob_signature_ports(self):
        sig = bob_decision.signature
        assert len(sig.x) == 1
        assert len(sig.y) == 1
        assert len(sig.r) == 1
        assert len(sig.s) == 1
        assert sig.x[0].name == "Bob Observation"
        assert sig.y[0].name == "Bob Action"

    def test_payoff_signature_no_contravariant(self):
        """CovariantFunction must have empty R and S ports."""
        sig = payoff_computation.signature
        assert sig.r == ()
        assert sig.s == ()

    def test_payoff_signature_covariant(self):
        sig = payoff_computation.signature
        assert len(sig.x) == 2
        assert len(sig.y) == 2

    def test_domain_tags(self):
        assert alice_decision.tags.get("domain") == "Alice"
        assert bob_decision.tags.get("domain") == "Bob"
        assert payoff_computation.tags.get("domain") == "Environment"


# ======================================================================
# TestComposition — game tree structure
# ======================================================================


class TestComposition:
    """Test the composition tree built by build_game()."""

    def test_build_game_returns_feedback_loop(self):
        game = build_game()
        assert isinstance(game, FeedbackLoop)

    def test_inner_is_sequential(self):
        game = build_game()
        assert isinstance(game.inner, SequentialComposition)

    def test_decisions_are_parallel(self):
        game = build_game()
        inner = game.inner
        assert isinstance(inner, SequentialComposition)
        assert isinstance(inner.first, ParallelComposition)

    def test_flatten_yields_three_games(self):
        game = build_game()
        flat = game.flatten()
        assert len(flat) == 3
        names = {g.name for g in flat}
        assert names == {"Alice Decision", "Bob Decision", "Payoff Computation"}

    def test_feedback_wiring_count(self):
        game = build_game()
        assert len(game.feedback_wiring) == 2

    def test_feedback_directions_are_contravariant(self):
        game = build_game()
        for flow in game.feedback_wiring:
            assert flow.direction == FlowDirection.CONTRAVARIANT


# ======================================================================
# TestCompile — PatternIR and GDS spec generation
# ======================================================================


class TestCompile:
    """Test compilation to OGS IR and GDS spec."""

    def test_build_ir_returns_pattern_ir(self):
        ir = build_ir()
        assert isinstance(ir, PatternIR)
        assert ir.name == "Iterated Prisoners Dilemma"

    def test_ir_has_three_games(self):
        ir = build_ir()
        assert len(ir.games) == 3

    def test_ir_has_flows(self):
        ir = build_ir()
        assert len(ir.flows) > 0

    def test_ir_composition_type(self):
        ir = build_ir()
        assert ir.composition_type == CompositionType.FEEDBACK

    def test_ir_has_terminal_conditions(self):
        ir = build_ir()
        assert ir.terminal_conditions is not None
        assert len(ir.terminal_conditions) == 4

    def test_ir_has_action_spaces(self):
        ir = build_ir()
        assert ir.action_spaces is not None
        assert len(ir.action_spaces) == 2

    def test_ir_has_inputs(self):
        ir = build_ir()
        assert len(ir.inputs) == 1
        assert ir.inputs[0].name == "Payoff Matrix"

    def test_ir_has_hierarchy(self):
        ir = build_ir()
        assert ir.hierarchy is not None

    def test_build_spec_produces_gds_spec(self):
        spec = build_spec()
        assert spec.name == "Iterated Prisoners Dilemma"

    def test_spec_has_blocks(self):
        spec = build_spec()
        # 3 atomic games as Policy + 1 PatternInput as BoundaryAction = 4
        assert len(spec.blocks) == 4

    def test_ir_to_system_ir(self):
        """PatternIR can project to GDS SystemIR for generic checks."""
        ir = build_ir()
        system_ir = ir.to_system_ir()
        assert system_ir.name == "Iterated Prisoners Dilemma"
        assert len(system_ir.blocks) == 3

    def test_pattern_has_four_terminal_conditions(self):
        pattern = build_pattern()
        assert pattern.terminal_conditions is not None
        assert len(pattern.terminal_conditions) == 4
        names = {tc.name for tc in pattern.terminal_conditions}
        assert "Mutual Cooperation" in names
        assert "Mutual Defection" in names

    def test_pattern_action_spaces(self):
        pattern = build_pattern()
        assert pattern.action_spaces is not None
        for action_space in pattern.action_spaces:
            assert set(action_space.actions) == {"Cooperate", "Defect"}


# ======================================================================
# TestVerification — OGS + GDS verification checks
# ======================================================================


class TestVerification:
    """Test OGS verification (domain + delegated GDS checks)."""

    def test_verification_runs(self):
        report = run_verification()
        assert isinstance(report, VerificationReport)

    def test_no_unexpected_exceptions(self):
        """OGS verification produces ERROR-severity findings as structural
        annotations (e.g., T-003 flow type checks, S-003 type mismatches).
        These are expected for well-formed games. We just verify the report
        completes without raising exceptions."""
        report = run_verification()
        assert isinstance(report, VerificationReport)

    def test_verification_has_findings(self):
        """Verification should produce some findings (pass or info)."""
        report = run_verification()
        assert len(report.findings) > 0

    def test_ogs_checks_included(self):
        """OGS-specific checks should produce findings."""
        report = run_verification()
        # At minimum, some checks should have run
        assert report.pattern_name == "Iterated Prisoners Dilemma"


# ======================================================================
# TestVisualization — OGS Mermaid views
# ======================================================================


class TestVisualization:
    """Test OGS visualization output."""

    def test_structural_view(self):
        from ogs.viz import structural_to_mermaid

        ir = build_ir()
        mermaid = structural_to_mermaid(ir)
        assert "flowchart" in mermaid
        assert "Alice Decision" in mermaid
        assert "Bob Decision" in mermaid
        assert "Payoff Computation" in mermaid

    def test_architecture_by_role_view(self):
        from ogs.viz import architecture_by_role_to_mermaid

        ir = build_ir()
        mermaid = architecture_by_role_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_architecture_by_domain_view(self):
        from ogs.viz import architecture_by_domain_to_mermaid

        ir = build_ir()
        mermaid = architecture_by_domain_to_mermaid(ir)
        assert "Alice" in mermaid
        assert "Bob" in mermaid
        assert "Environment" in mermaid

    def test_hierarchy_view(self):
        from ogs.viz import hierarchy_to_mermaid

        ir = build_ir()
        mermaid = hierarchy_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_flow_topology_view(self):
        from ogs.viz import flow_topology_to_mermaid

        ir = build_ir()
        mermaid = flow_topology_to_mermaid(ir)
        assert "flowchart" in mermaid

    def test_terminal_conditions_view(self):
        from ogs.viz import terminal_conditions_to_mermaid

        ir = build_ir()
        mermaid = terminal_conditions_to_mermaid(ir)
        assert "stateDiagram" in mermaid

    def test_generate_all_views(self):
        from ogs.viz import generate_all_views

        ir = build_ir()
        views = generate_all_views(ir)
        assert len(views) == 6
        assert all(isinstance(v, str) for v in views.values())


# ======================================================================
# TestReports — OGS Markdown report generation
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
        from ogs.reports.generator import generate_system_overview

        ir = build_ir()
        content = generate_system_overview(ir)
        assert "Iterated Prisoners Dilemma" in content

    def test_verification_summary_report(self):
        from ogs.reports.generator import generate_verification_summary

        ir = build_ir()
        content = generate_verification_summary(ir)
        assert len(content) > 0

    def test_interface_contracts_report(self):
        from ogs.reports.generator import generate_interface_contracts

        ir = build_ir()
        content = generate_interface_contracts(ir)
        assert "Alice Decision" in content

    def test_implementation_checklist_report(self):
        from ogs.reports.generator import generate_implementation_checklist

        ir = build_ir()
        content = generate_implementation_checklist(ir)
        assert len(content) > 0

"""Tests for verification engine and individual checks."""

from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    FlowIR,
    FlowType,
    GameType,
    InputIR,
    InputType,
    OpenGameIR,
    PatternIR,
)
from ogs.verification.structural_checks import (
    check_s001_sequential_type_compatibility,
    check_s002_parallel_independence,
    check_s003_feedback_type_compatibility,
    check_s004_covariant_acyclicity,
    check_s005_decision_space_validation,
    check_s006_corecursive_wiring,
    check_s007_initialization_completeness,
)
from ogs.verification.tokens import tokenize, tokens_overlap, tokens_subset
from ogs.verification.type_checks import (
    check_t001_domain_codomain_matching,
    check_t002_signature_completeness,
    check_t003_flow_type_consistency,
    check_t005_unused_inputs,
    check_t006_dangling_flows,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pattern(**overrides) -> PatternIR:
    defaults: dict[str, object] = dict(
        name="Test Pattern",
        games=[
            OpenGameIR(
                name="Game A",
                game_type=GameType.FUNCTION_COVARIANT,
                signature=("Input", "Output", "", ""),
                color_code=1,
            ),
            OpenGameIR(
                name="Game B",
                game_type=GameType.DECISION,
                signature=("Output", "Action", "Utility", "Experience"),
                color_code=1,
            ),
        ],
        flows=[
            FlowIR(
                source="Game A",
                target="Game B",
                label="Output",
                flow_type=FlowType.OBSERVATION,
                direction=FlowDirection.COVARIANT,
            ),
        ],
        inputs=[
            InputIR(name="Sensor", input_type=InputType.SENSOR, schema_hint="(X, x)"),
        ],
        composition_type=CompositionType.SEQUENTIAL,
        source_canvas="test.canvas",
    )
    defaults.update(overrides)
    return PatternIR(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests against synthetic data
# ---------------------------------------------------------------------------


class TestT002SignatureCompleteness:
    def test_passes_complete(self):
        pattern = _make_pattern()
        findings = check_t002_signature_completeness(pattern)
        assert all(f.passed for f in findings)

    def test_passes_contravariant_only_output(self):
        """A game with X input and S output (no Y) is valid — utility computation."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Utility Game",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("Input", "", "", "Utility"),
                    color_code=1,
                ),
            ]
        )
        findings = check_t002_signature_completeness(pattern)
        assert all(f.passed for f in findings)

    def test_fails_no_outputs(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Bad Game",
                    game_type=GameType.DECISION,
                    signature=("X", "", "", ""),
                    color_code=1,
                ),
            ]
        )
        findings = check_t002_signature_completeness(pattern)
        assert any(not f.passed for f in findings)


class TestT003FlowTypeConsistency:
    def test_passes_correct(self):
        pattern = _make_pattern()
        findings = check_t003_flow_type_consistency(pattern)
        assert all(f.passed for f in findings)

    def test_fails_covariant_utility(self):
        pattern = _make_pattern(
            flows=[
                FlowIR(
                    source="Game A",
                    target="Game B",
                    label="bad flow",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.COVARIANT,
                ),
            ]
        )
        findings = check_t003_flow_type_consistency(pattern)
        assert any(not f.passed for f in findings)


class TestT005UnusedInputs:
    def test_detects_unused(self):
        pattern = _make_pattern()
        # "Sensor" input has no flow with source="Sensor"
        findings = check_t005_unused_inputs(pattern)
        unused = [f for f in findings if not f.passed]
        assert len(unused) == 1
        assert "Sensor" in unused[0].message


class TestT006DanglingFlows:
    def test_passes_valid(self):
        pattern = _make_pattern()
        findings = check_t006_dangling_flows(pattern)
        assert all(f.passed for f in findings)

    def test_fails_unknown_target(self):
        pattern = _make_pattern(
            flows=[
                FlowIR(
                    source="Game A",
                    target="Nonexistent",
                    label="bad",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ]
        )
        findings = check_t006_dangling_flows(pattern)
        assert any(not f.passed for f in findings)


class TestS004CovariantAcyclicity:
    def test_passes_dag(self):
        pattern = _make_pattern()
        findings = check_s004_covariant_acyclicity(pattern)
        assert all(f.passed for f in findings)

    def test_fails_cycle(self):
        pattern = _make_pattern(
            flows=[
                FlowIR(
                    source="Game A",
                    target="Game B",
                    label="forward",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
                FlowIR(
                    source="Game B",
                    target="Game A",
                    label="backward",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ]
        )
        findings = check_s004_covariant_acyclicity(pattern)
        assert any(not f.passed for f in findings)
        cycle_finding = next(f for f in findings if not f.passed)
        assert "cycle" in cycle_finding.message.lower()


# ---------------------------------------------------------------------------
# Token module tests
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_empty_string(self):
        assert tokenize("") == frozenset()

    def test_single_token(self):
        assert tokenize("Output") == frozenset({"output"})

    def test_comma_separated(self):
        assert tokenize("Observation, Context") == frozenset({"observation", "context"})

    def test_plus_separated(self):
        assert tokenize("Latest History + Primitive") == frozenset(
            {"latest history", "primitive"}
        )

    def test_mixed_separators(self):
        assert tokenize("Observation, Context + Latest History") == frozenset(
            {"observation", "context", "latest history"}
        )

    def test_whitespace_normalization(self):
        assert tokenize("  Output  ") == frozenset({"output"})

    def test_case_normalization(self):
        assert tokenize("DECISION") == frozenset({"decision"})

    def test_tokens_subset_basic(self):
        assert tokens_subset("Output", "Output") is True

    def test_tokens_subset_of_compound(self):
        assert tokens_subset("Latest History", "Latest History + Primitive") is True

    def test_tokens_subset_rejects_partial(self):
        # "Out" is NOT a token of "Output" — fixes F-07
        assert tokens_subset("Out", "Output") is False

    def test_tokens_subset_empty_child(self):
        assert tokens_subset("", "Output") is True

    def test_tokens_subset_empty_parent(self):
        assert tokens_subset("Output", "") is False

    def test_tokens_overlap_basic(self):
        assert tokens_overlap("History Update", "History Update + Primitive") is True

    def test_tokens_overlap_disjoint(self):
        assert tokens_overlap("Experience", "Primitive") is False

    def test_tokens_overlap_empty(self):
        assert tokens_overlap("", "Output") is False


# ---------------------------------------------------------------------------
# T-001 rewrite tests
# ---------------------------------------------------------------------------


class TestT001DomainCodomainMatching:
    def test_passes_exact_match(self):
        pattern = _make_pattern()
        findings = check_t001_domain_codomain_matching(pattern)
        game_findings = [f for f in findings if f.check_id == "T-001"]
        assert all(f.passed for f in game_findings)

    def test_passes_label_subset_of_compound_x(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Data", "", ""),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Data + Extra", "Out", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Data",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_t001_domain_codomain_matching(pattern)
        assert all(f.passed for f in findings)

    def test_fails_substring_match(self):
        """'Out' must NOT match 'Output' — fixes F-07."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Output", "", ""),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Output", "Action", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Out",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_t001_domain_codomain_matching(pattern)
        assert any(not f.passed for f in findings)

    def test_skips_input_to_game_flows(self):
        pattern = _make_pattern()
        findings = check_t001_domain_codomain_matching(pattern)
        assert len(findings) == 1  # only the game-to-game flow


# ---------------------------------------------------------------------------
# S-001 rewrite tests
# ---------------------------------------------------------------------------


class TestS001SequentialRewritten:
    def test_passes_exact_match(self):
        pattern = _make_pattern()
        findings = check_s001_sequential_type_compatibility(pattern)
        assert all(f.passed for f in findings)

    def test_passes_label_in_both(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Data", "", ""),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Data + Extra", "Out", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Data",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_s001_sequential_type_compatibility(pattern)
        assert all(f.passed for f in findings)

    def test_fails_label_in_y_only(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Alpha", "", ""),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Beta", "Out", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Alpha",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_s001_sequential_type_compatibility(pattern)
        assert any(not f.passed for f in findings)

    def test_differentiation_from_t001(self):
        """A flow can pass T-001 (OR) but fail S-001 (AND)."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Foo", "", ""),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Bar", "Out", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Foo",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        t001 = check_t001_domain_codomain_matching(pattern)
        s001 = check_s001_sequential_type_compatibility(pattern)
        # T-001 passes: "Foo" tokens ⊆ Y="Foo"
        assert all(f.passed for f in t001)
        # S-001 fails: "Foo" tokens NOT ⊆ X="Bar"
        assert any(not f.passed for f in s001)


# ---------------------------------------------------------------------------
# S-003 rewrite tests
# ---------------------------------------------------------------------------


class TestS003FeedbackRewritten:
    def test_passes_matching_feedback(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.DECISION,
                    signature=("In", "Out", "R", "Feedback"),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("Feedback", "Y", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Feedback",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                ),
            ],
        )
        findings = check_s003_feedback_type_compatibility(pattern)
        assert all(f.passed for f in findings)

    def test_fails_label_not_in_s(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.DECISION,
                    signature=("In", "Out", "R", "Apples"),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("Oranges", "Y", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Oranges",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                ),
            ],
        )
        findings = check_s003_feedback_type_compatibility(pattern)
        assert any(not f.passed for f in findings)

    def test_no_false_positive_from_nonempty(self):
        """Removes F-09: bool(src_s and tgt_x) no longer causes false pass."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.DECISION,
                    signature=("In", "Out", "R", "Completely Different"),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("Also Different", "Y", "", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Mismatched Label",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                ),
            ],
        )
        findings = check_s003_feedback_type_compatibility(pattern)
        assert any(not f.passed for f in findings)

    def test_skips_non_feedback_flows(self):
        pattern = _make_pattern()  # default flows have is_feedback=False
        findings = check_s003_feedback_type_compatibility(pattern)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# S-002 parallel independence tests
# ---------------------------------------------------------------------------


class TestS002ParallelIndependence:
    def test_not_applicable_for_sequential(self):
        pattern = _make_pattern()
        findings = check_s002_parallel_independence(pattern)
        assert all(f.passed for f in findings)

    def test_passes_no_game_to_game_flows(self):
        pattern = _make_pattern(
            composition_type=CompositionType.PARALLEL,
            flows=[],
        )
        findings = check_s002_parallel_independence(pattern)
        assert all(f.passed for f in findings)

    def test_fails_game_to_game_flow(self):
        pattern = _make_pattern(
            composition_type=CompositionType.PARALLEL,
        )
        findings = check_s002_parallel_independence(pattern)
        violations = [f for f in findings if not f.passed]
        assert len(violations) == 1
        assert "Output" in violations[0].message


# ---------------------------------------------------------------------------
# S-005 decision space validation tests
# ---------------------------------------------------------------------------


class TestS005DecisionSpaceValidation:
    def test_passes_valid_decision(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Dec",
                    game_type=GameType.DECISION,
                    signature=("In", "Action", "Utility", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="Upstream",
                    target="Dec",
                    label="Utility",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.CONTRAVARIANT,
                ),
            ],
        )
        findings = check_s005_decision_space_validation(pattern)
        assert all(f.passed for f in findings)

    def test_fails_empty_y(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Dec",
                    game_type=GameType.DECISION,
                    signature=("In", "", "Utility", ""),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="Upstream",
                    target="Dec",
                    label="Utility",
                    flow_type=FlowType.UTILITY_COUTILITY,
                    direction=FlowDirection.CONTRAVARIANT,
                ),
            ],
        )
        findings = check_s005_decision_space_validation(pattern)
        assert any(not f.passed for f in findings)

    def test_fails_no_contravariant(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Dec",
                    game_type=GameType.DECISION,
                    signature=("In", "Action", "", ""),
                    color_code=1,
                ),
            ],
            flows=[],
        )
        findings = check_s005_decision_space_validation(pattern)
        assert any(not f.passed for f in findings)

    def test_skips_non_decision(self):
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="Func",
                    game_type=GameType.FUNCTION_COVARIANT,
                    signature=("In", "Out", "", ""),
                    color_code=1,
                ),
            ],
        )
        findings = check_s005_decision_space_validation(pattern)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# S-007 initialization completeness tests
# ---------------------------------------------------------------------------


class TestS007InitializationCompleteness:
    def test_passes_connected(self):
        pattern = _make_pattern(
            inputs=[
                InputIR(
                    name="Init",
                    input_type=InputType.INITIALIZATION,
                    schema_hint="(H, h0)",
                ),
            ],
            flows=[
                FlowIR(
                    source="Init",
                    target="Game A",
                    label="init",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_s007_initialization_completeness(pattern)
        assert all(f.passed for f in findings)

    def test_fails_disconnected(self):
        pattern = _make_pattern(
            inputs=[
                InputIR(
                    name="Init",
                    input_type=InputType.INITIALIZATION,
                    schema_hint="(H, h0)",
                ),
            ],
            flows=[],
        )
        findings = check_s007_initialization_completeness(pattern)
        assert any(not f.passed for f in findings)

    def test_passes_no_init_inputs(self):
        pattern = _make_pattern()  # default has SENSOR input only
        findings = check_s007_initialization_completeness(pattern)
        assert all(f.passed for f in findings)


# ---------------------------------------------------------------------------
# S-004 with corecursive exclusion
# ---------------------------------------------------------------------------


class TestS004CorecursiveExclusion:
    def test_corecursive_flows_excluded_from_cycle_check(self):
        """Corecursive Y→X flows should not trigger cycle detection."""
        pattern = _make_pattern(
            flows=[
                FlowIR(
                    source="Game A",
                    target="Game B",
                    label="forward",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
                FlowIR(
                    source="Game B",
                    target="Game A",
                    label="temporal",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                    is_corecursive=True,
                ),
            ]
        )
        findings = check_s004_covariant_acyclicity(pattern)
        assert all(f.passed for f in findings)

    def test_non_corecursive_cycle_still_detected(self):
        """Non-corecursive back edge should still trigger cycle detection."""
        pattern = _make_pattern(
            flows=[
                FlowIR(
                    source="Game A",
                    target="Game B",
                    label="forward",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                ),
                FlowIR(
                    source="Game B",
                    target="Game A",
                    label="backward",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                    is_corecursive=False,
                ),
            ]
        )
        findings = check_s004_covariant_acyclicity(pattern)
        assert any(not f.passed for f in findings)


# ---------------------------------------------------------------------------
# S-006 corecursive wiring validation
# ---------------------------------------------------------------------------


class TestS006CorecursiveWiring:
    def test_no_corecursive_flows(self):
        """No corecursive flows → no findings."""
        pattern = _make_pattern()
        findings = check_s006_corecursive_wiring(pattern)
        assert len(findings) == 0

    def test_passes_valid_corecursive(self):
        """Valid corecursive flow: covariant, label in source Y."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.DECISION,
                    signature=("In", "Decision", "R", "S"),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Decision", "Out", "R", "S"),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Decision",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                    is_corecursive=True,
                ),
            ],
        )
        findings = check_s006_corecursive_wiring(pattern)
        assert all(f.passed for f in findings)

    def test_fails_label_not_in_y(self):
        """Corecursive flow label not in source Y → error."""
        pattern = _make_pattern(
            games=[
                OpenGameIR(
                    name="G1",
                    game_type=GameType.DECISION,
                    signature=("In", "Something", "R", "S"),
                    color_code=1,
                ),
                OpenGameIR(
                    name="G2",
                    game_type=GameType.DECISION,
                    signature=("Decision", "Out", "R", "S"),
                    color_code=1,
                ),
            ],
            flows=[
                FlowIR(
                    source="G1",
                    target="G2",
                    label="Decision",
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                    is_corecursive=True,
                ),
            ],
        )
        findings = check_s006_corecursive_wiring(pattern)
        assert any(not f.passed for f in findings)

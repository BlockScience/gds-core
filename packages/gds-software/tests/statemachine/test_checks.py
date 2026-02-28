"""Tests for state machine verification checks."""

import pytest

from gds_software.statemachine.checks import (
    check_sm001_initial_state,
    check_sm002_reachability,
    check_sm003_determinism,
    check_sm004_guard_completeness,
    check_sm005_region_partition,
    check_sm006_transition_validity,
)
from gds_software.statemachine.elements import (
    Event,
    Guard,
    Region,
    State,
    Transition,
)
from gds_software.statemachine.model import StateMachineModel
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return StateMachineModel(
        name="Door",
        states=[
            State(name="Closed", is_initial=True),
            State(name="Open"),
        ],
        events=[Event(name="Push")],
        transitions=[
            Transition(name="T1", source="Closed", target="Open", event="Push"),
            Transition(name="T2", source="Open", target="Closed", event="Push"),
        ],
    )


class TestSM001InitialState:
    def test_has_initial(self, good_model):
        findings = check_sm001_initial_state(good_model)
        assert all(f.passed for f in findings)


class TestSM002Reachability:
    def test_all_reachable(self, good_model):
        findings = check_sm002_reachability(good_model)
        assert all(f.passed for f in findings)

    def test_unreachable_state(self):
        model = StateMachineModel(
            name="Unreachable",
            states=[
                State(name="A", is_initial=True),
                State(name="B"),
                State(name="Island"),
            ],
            events=[Event(name="E")],
            transitions=[
                Transition(name="T1", source="A", target="B", event="E"),
            ],
        )
        findings = check_sm002_reachability(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "Island" in failed[0].source_elements


class TestSM003Determinism:
    def test_deterministic(self, good_model):
        findings = check_sm003_determinism(good_model)
        assert all(f.passed for f in findings)

    def test_nondeterministic(self):
        model = StateMachineModel(
            name="NonDet",
            states=[
                State(name="A", is_initial=True),
                State(name="B"),
                State(name="C"),
            ],
            events=[Event(name="E")],
            transitions=[
                Transition(name="T1", source="A", target="B", event="E"),
                Transition(name="T2", source="A", target="C", event="E"),
            ],
        )
        findings = check_sm003_determinism(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1

    def test_guarded_ok(self):
        model = StateMachineModel(
            name="Guarded",
            states=[
                State(name="A", is_initial=True),
                State(name="B"),
                State(name="C"),
            ],
            events=[Event(name="E")],
            transitions=[
                Transition(
                    name="T1",
                    source="A",
                    target="B",
                    event="E",
                    guard=Guard(condition="x > 0"),
                ),
                Transition(name="T2", source="A", target="C", event="E"),
            ],
        )
        findings = check_sm003_determinism(model)
        # One guarded + one unguarded = deterministic (one unguarded only)
        assert all(f.passed for f in findings)


class TestSM004GuardCompleteness:
    def test_no_guards_passes(self, good_model):
        findings = check_sm004_guard_completeness(good_model)
        assert all(f.passed for f in findings)


class TestSM005RegionPartition:
    def test_no_regions_passes(self, good_model):
        findings = check_sm005_region_partition(good_model)
        assert all(f.passed for f in findings)

    def test_overlap_fails(self):
        model = StateMachineModel(
            name="Overlap",
            states=[
                State(name="A", is_initial=True),
                State(name="B"),
            ],
            regions=[
                Region(name="R1", states=["A"]),
                Region(name="R2", states=["A", "B"]),
            ],
        )
        findings = check_sm005_region_partition(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1


class TestSM006TransitionValidity:
    def test_valid_transitions(self, good_model):
        findings = check_sm006_transition_validity(good_model)
        assert all(f.passed for f in findings)


class TestVerifyEngine:
    def test_verify_sm(self, good_model):
        report = verify(good_model)
        assert report.system_name == "Door"
        sm_findings = [f for f in report.findings if f.check_id.startswith("SM-")]
        assert len(sm_findings) > 0

    def test_verify_sm_only(self, good_model):
        report = verify(good_model, include_gds_checks=False)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) == 0

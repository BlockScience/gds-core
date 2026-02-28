"""Tests for VSM verification checks."""

from gds.verification.findings import Severity

from gds_business.vsm.checks import (
    ALL_VSM_CHECKS,
    check_vsm001_linear_process_flow,
    check_vsm002_push_pull_boundary,
    check_vsm003_flow_reference_validity,
    check_vsm004_bottleneck_vs_takt,
)
from gds_business.vsm.elements import (
    Customer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)
from gds_business.vsm.model import ValueStreamModel


def _linear_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="Linear",
        steps=[
            ProcessStep(name="S1", cycle_time=10.0),
            ProcessStep(name="S2", cycle_time=20.0),
        ],
        suppliers=[Supplier(name="Sup")],
        customers=[Customer(name="Cust", takt_time=30.0)],
        material_flows=[
            MaterialFlow(source="Sup", target="S1"),
            MaterialFlow(source="S1", target="S2"),
            MaterialFlow(source="S2", target="Cust"),
        ],
    )


def _branching_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="Branching",
        steps=[
            ProcessStep(name="S1", cycle_time=10.0),
            ProcessStep(name="S2", cycle_time=20.0),
            ProcessStep(name="S3", cycle_time=15.0),
        ],
        material_flows=[
            MaterialFlow(source="S1", target="S2"),
            MaterialFlow(source="S1", target="S3"),
        ],
    )


def _push_pull_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="PushPull",
        steps=[
            ProcessStep(name="S1", cycle_time=10.0),
            ProcessStep(name="S2", cycle_time=20.0),
            ProcessStep(name="S3", cycle_time=15.0),
        ],
        material_flows=[
            MaterialFlow(source="S1", target="S2", flow_type="push"),
            MaterialFlow(source="S2", target="S3", flow_type="pull"),
        ],
    )


def _bottleneck_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="Bottleneck",
        steps=[
            ProcessStep(name="S1", cycle_time=10.0),
            ProcessStep(name="S2", cycle_time=60.0),  # Bottleneck
        ],
        customers=[Customer(name="Cust", takt_time=50.0)],
        material_flows=[
            MaterialFlow(source="S1", target="S2"),
            MaterialFlow(source="S2", target="Cust"),
        ],
    )


def _within_takt_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="WithinTakt",
        steps=[
            ProcessStep(name="S1", cycle_time=10.0),
            ProcessStep(name="S2", cycle_time=20.0),
        ],
        customers=[Customer(name="Cust", takt_time=30.0)],
    )


def _no_flows_model() -> ValueStreamModel:
    return ValueStreamModel(
        name="NoFlows",
        steps=[ProcessStep(name="S1", cycle_time=10.0)],
    )


class TestVSM001LinearProcessFlow:
    def test_linear_passes(self):
        findings = check_vsm001_linear_process_flow(_linear_model())
        # S1 and S2 each have <=1 in, <=1 out
        step_findings = [f for f in findings if f.source_elements[0] in ("S1", "S2")]
        assert all(f.passed for f in step_findings)

    def test_branching_detected(self):
        findings = check_vsm001_linear_process_flow(_branching_model())
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "S1" in failed[0].source_elements

    def test_severity_is_warning(self):
        findings = check_vsm001_linear_process_flow(_linear_model())
        assert all(f.severity == Severity.WARNING for f in findings)


class TestVSM002PushPullBoundary:
    def test_boundary_detected(self):
        findings = check_vsm002_push_pull_boundary(_push_pull_model())
        boundary = [
            f
            for f in findings
            if "boundary" in f.message.lower() and "at" in f.message.lower()
        ]
        assert len(boundary) >= 1

    def test_all_push_no_boundary(self):
        findings = check_vsm002_push_pull_boundary(_linear_model())
        assert all(f.passed for f in findings)
        assert any("push" in f.message.lower() for f in findings)

    def test_no_flows(self):
        findings = check_vsm002_push_pull_boundary(_no_flows_model())
        assert len(findings) >= 1
        assert all(f.passed for f in findings)


class TestVSM003FlowReferenceValidity:
    def test_valid_flows(self):
        findings = check_vsm003_flow_reference_validity(_linear_model())
        assert all(f.passed for f in findings)

    def test_no_flows_empty(self):
        findings = check_vsm003_flow_reference_validity(_no_flows_model())
        assert len(findings) == 0

    def test_severity_is_error(self):
        findings = check_vsm003_flow_reference_validity(_linear_model())
        assert all(f.severity == Severity.ERROR for f in findings)


class TestVSM004BottleneckVsTakt:
    def test_bottleneck_exceeds_takt(self):
        findings = check_vsm004_bottleneck_vs_takt(_bottleneck_model())
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "S2" in failed[0].source_elements

    def test_within_takt(self):
        findings = check_vsm004_bottleneck_vs_takt(_within_takt_model())
        assert all(f.passed for f in findings)

    def test_no_customers(self):
        findings = check_vsm004_bottleneck_vs_takt(_no_flows_model())
        assert len(findings) == 1
        assert findings[0].passed


class TestALLVSMChecks:
    def test_all_checks_registered(self):
        assert len(ALL_VSM_CHECKS) == 4

    def test_all_checks_callable(self):
        model = _linear_model()
        for check in ALL_VSM_CHECKS:
            findings = check(model)
            assert isinstance(findings, list)

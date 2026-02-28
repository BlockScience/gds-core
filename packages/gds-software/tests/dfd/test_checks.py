"""Tests for DFD verification checks."""

import pytest

from gds_software.dfd.checks import (
    check_dfd001_process_connectivity,
    check_dfd002_flow_validity,
    check_dfd003_no_ext_to_ext,
    check_dfd004_store_connectivity,
    check_dfd005_process_output,
)
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process
from gds_software.dfd.model import DFDModel
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return DFDModel(
        name="Auth",
        external_entities=[ExternalEntity(name="User")],
        processes=[Process(name="Auth"), Process(name="Log")],
        data_stores=[DataStore(name="DB")],
        data_flows=[
            DataFlow(name="Login", source="User", target="Auth"),
            DataFlow(name="Save", source="Auth", target="DB"),
            DataFlow(name="Read", source="DB", target="Log"),
            DataFlow(name="Result", source="Auth", target="User"),
            DataFlow(name="LogOut", source="Log", target="User"),
        ],
    )


@pytest.fixture
def disconnected_process_model():
    return DFDModel(
        name="Disconnected",
        processes=[Process(name="Connected"), Process(name="Island")],
        data_flows=[
            DataFlow(name="F", source="Connected", target="Connected"),
        ],
    )


class TestDFD001ProcessConnectivity:
    def test_connected_processes_pass(self, good_model):
        findings = check_dfd001_process_connectivity(good_model)
        assert all(f.passed for f in findings)

    def test_disconnected_process_warns(self, disconnected_process_model):
        findings = check_dfd001_process_connectivity(disconnected_process_model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "Island" in failed[0].source_elements
        assert failed[0].severity.value == "warning"


class TestDFD002FlowValidity:
    def test_valid_references_pass(self, good_model):
        findings = check_dfd002_flow_validity(good_model)
        assert all(f.passed for f in findings)


class TestDFD003NoExtToExt:
    def test_no_ext_to_ext_passes(self, good_model):
        findings = check_dfd003_no_ext_to_ext(good_model)
        assert all(f.passed for f in findings)


class TestDFD004StoreConnectivity:
    def test_connected_stores_pass(self, good_model):
        findings = check_dfd004_store_connectivity(good_model)
        assert all(f.passed for f in findings)

    def test_disconnected_store_warns(self):
        model = DFDModel(
            name="Disconnected",
            processes=[Process(name="P")],
            data_stores=[DataStore(name="Unused")],
        )
        findings = check_dfd004_store_connectivity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].severity.value == "warning"


class TestDFD005ProcessOutput:
    def test_processes_with_output_pass(self, good_model):
        findings = check_dfd005_process_output(good_model)
        assert all(f.passed for f in findings)

    def test_process_without_output_warns(self):
        model = DFDModel(
            name="NoOutput",
            processes=[Process(name="Sink")],
            external_entities=[ExternalEntity(name="E")],
            data_flows=[DataFlow(name="F", source="E", target="Sink")],
        )
        findings = check_dfd005_process_output(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestVerifyEngine:
    def test_verify_good_model(self, good_model):
        report = verify(good_model)
        assert report.system_name == "Auth"
        assert report.checks_total > 0
        dfd_findings = [f for f in report.findings if f.check_id.startswith("DFD-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(dfd_findings) > 0
        assert len(gds_findings) > 0

    def test_verify_domain_only(self, good_model):
        report = verify(good_model, include_gds_checks=False)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) == 0

    def test_verify_specific_checks(self, good_model):
        report = verify(
            good_model,
            domain_checks=[check_dfd001_process_connectivity],
            include_gds_checks=False,
        )
        assert all(f.check_id == "DFD-001" for f in report.findings)

    def test_verify_errors_count(self, good_model):
        report = verify(good_model, include_gds_checks=False)
        assert report.errors == 0

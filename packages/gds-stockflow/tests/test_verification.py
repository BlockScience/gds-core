"""Tests for stock-flow verification checks."""

import pytest

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel
from stockflow.verification.checks import (
    check_sf001_orphan_stocks,
    check_sf002_flow_stock_validity,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
    check_sf005_flow_completeness,
)
from stockflow.verification.engine import verify


@pytest.fixture
def good_model():
    return StockFlowModel(
        name="Population",
        stocks=[Stock(name="Population", initial=1000.0)],
        flows=[
            Flow(name="Births", target="Population"),
            Flow(name="Deaths", source="Population"),
        ],
        auxiliaries=[
            Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
        ],
        converters=[Converter(name="Fertility")],
    )


@pytest.fixture
def orphan_stock_model():
    """Model where one stock has no flows."""
    return StockFlowModel(
        name="Orphan",
        stocks=[Stock(name="Connected"), Stock(name="Orphaned")],
        flows=[Flow(name="F", target="Connected")],
    )


class TestSF001OrphanStocks:
    def test_connected_stocks_pass(self, good_model):
        findings = check_sf001_orphan_stocks(good_model)
        assert all(f.passed for f in findings)

    def test_orphan_stock_warns(self, orphan_stock_model):
        findings = check_sf001_orphan_stocks(orphan_stock_model)
        orphan_findings = [f for f in findings if not f.passed]
        assert len(orphan_findings) == 1
        assert "Orphaned" in orphan_findings[0].source_elements
        assert orphan_findings[0].severity.value == "warning"


class TestSF002FlowStockValidity:
    def test_valid_references_pass(self, good_model):
        findings = check_sf002_flow_stock_validity(good_model)
        assert all(f.passed for f in findings)


class TestSF003AuxiliaryAcyclicity:
    def test_acyclic_passes(self, good_model):
        findings = check_sf003_auxiliary_acyclicity(good_model)
        assert all(f.passed for f in findings)

    def test_cycle_detected(self):
        model = StockFlowModel(
            name="Cyclic",
            stocks=[Stock(name="S")],
            auxiliaries=[
                Auxiliary(name="A", inputs=["B"]),
                Auxiliary(name="B", inputs=["A"]),
            ],
        )
        findings = check_sf003_auxiliary_acyclicity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].severity.value == "error"

    def test_self_loop_detected(self):
        model = StockFlowModel(
            name="SelfLoop",
            stocks=[Stock(name="S")],
            auxiliaries=[
                Auxiliary(name="A", inputs=["A"]),
            ],
        )
        findings = check_sf003_auxiliary_acyclicity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestSF004ConverterConnectivity:
    def test_connected_converter_passes(self, good_model):
        findings = check_sf004_converter_connectivity(good_model)
        assert all(f.passed for f in findings)

    def test_disconnected_converter_warns(self):
        model = StockFlowModel(
            name="Disconnected",
            stocks=[Stock(name="S")],
            converters=[Converter(name="Unused")],
        )
        findings = check_sf004_converter_connectivity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].severity.value == "warning"


class TestSF005FlowCompleteness:
    def test_valid_flows_pass(self, good_model):
        findings = check_sf005_flow_completeness(good_model)
        assert all(f.passed for f in findings)


class TestVerifyEngine:
    def test_verify_good_model(self, good_model):
        report = verify(good_model)
        assert report.system_name == "Population"
        assert report.checks_total > 0
        # SF checks + GDS checks
        sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(sf_findings) > 0
        assert len(gds_findings) > 0

    def test_verify_sf_only(self, good_model):
        report = verify(good_model, include_gds_checks=False)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) == 0

    def test_verify_specific_checks(self, good_model):
        report = verify(
            good_model,
            sf_checks=[check_sf001_orphan_stocks],
            include_gds_checks=False,
        )
        assert all(f.check_id == "SF-001" for f in report.findings)

    def test_verify_errors_count(self, good_model):
        report = verify(good_model, include_gds_checks=False)
        assert report.errors == 0

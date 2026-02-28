"""Tests for supply chain verification checks."""

from gds.verification.findings import Severity

from gds_business.supplychain.checks import (
    ALL_SCN_CHECKS,
    check_scn001_network_connectivity,
    check_scn002_shipment_node_validity,
    check_scn003_demand_target_validity,
    check_scn004_no_orphan_nodes,
)
from gds_business.supplychain.elements import (
    DemandSource,
    Shipment,
    SupplyNode,
)
from gds_business.supplychain.model import SupplyChainModel


def _connected_model() -> SupplyChainModel:
    return SupplyChainModel(
        name="Connected",
        nodes=[SupplyNode(name="A"), SupplyNode(name="B")],
        shipments=[Shipment(name="S1", source_node="A", target_node="B")],
        demand_sources=[DemandSource(name="D1", target_node="B")],
    )


def _disconnected_model() -> SupplyChainModel:
    return SupplyChainModel(
        name="Disconnected",
        nodes=[
            SupplyNode(name="A"),
            SupplyNode(name="B"),
            SupplyNode(name="C"),
        ],
        shipments=[Shipment(name="S1", source_node="A", target_node="B")],
        demand_sources=[DemandSource(name="D1", target_node="B")],
    )


def _orphan_model() -> SupplyChainModel:
    return SupplyChainModel(
        name="Orphan",
        nodes=[
            SupplyNode(name="A"),
            SupplyNode(name="B"),
            SupplyNode(name="C"),
        ],
        shipments=[Shipment(name="S1", source_node="A", target_node="B")],
    )


def _no_shipments_model() -> SupplyChainModel:
    return SupplyChainModel(
        name="NoShipments",
        nodes=[SupplyNode(name="A")],
        demand_sources=[DemandSource(name="D1", target_node="A")],
    )


class TestSCN001NetworkConnectivity:
    def test_all_connected(self):
        findings = check_scn001_network_connectivity(_connected_model())
        assert all(f.passed for f in findings)

    def test_disconnected_node(self):
        findings = check_scn001_network_connectivity(_disconnected_model())
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "C" in failed[0].source_elements

    def test_severity_is_warning(self):
        findings = check_scn001_network_connectivity(_connected_model())
        assert all(f.severity == Severity.WARNING for f in findings)


class TestSCN002ShipmentNodeValidity:
    def test_valid_shipments(self):
        findings = check_scn002_shipment_node_validity(_connected_model())
        assert all(f.passed for f in findings)

    def test_no_shipments_empty(self):
        findings = check_scn002_shipment_node_validity(_no_shipments_model())
        assert len(findings) == 0


class TestSCN003DemandTargetValidity:
    def test_valid_demand(self):
        findings = check_scn003_demand_target_validity(_connected_model())
        assert all(f.passed for f in findings)

    def test_severity_is_error(self):
        findings = check_scn003_demand_target_validity(_connected_model())
        assert all(f.severity == Severity.ERROR for f in findings)


class TestSCN004NoOrphanNodes:
    def test_no_orphans(self):
        findings = check_scn004_no_orphan_nodes(_connected_model())
        assert all(f.passed for f in findings)

    def test_orphan_detected(self):
        findings = check_scn004_no_orphan_nodes(_orphan_model())
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "C" in failed[0].source_elements


class TestALLSCNChecks:
    def test_all_checks_registered(self):
        assert len(ALL_SCN_CHECKS) == 4

    def test_all_checks_callable(self):
        model = _connected_model()
        for check in ALL_SCN_CHECKS:
            findings = check(model)
            assert isinstance(findings, list)

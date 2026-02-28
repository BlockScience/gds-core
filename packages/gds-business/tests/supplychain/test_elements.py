"""Tests for supply chain element declarations."""

import pytest
from pydantic import ValidationError

from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)


class TestSupplyNode:
    def test_create_minimal(self):
        n = SupplyNode(name="Warehouse")
        assert n.name == "Warehouse"
        assert n.initial_inventory == 0.0
        assert n.capacity == float("inf")

    def test_create_with_params(self):
        n = SupplyNode(name="W1", initial_inventory=100, capacity=500)
        assert n.initial_inventory == 100
        assert n.capacity == 500

    def test_frozen(self):
        n = SupplyNode(name="W1")
        with pytest.raises(ValidationError):
            n.name = "W2"

    def test_equality(self):
        n1 = SupplyNode(name="W1")
        n2 = SupplyNode(name="W1")
        assert n1 == n2


class TestShipment:
    def test_create(self):
        s = Shipment(name="S1", source_node="A", target_node="B")
        assert s.source_node == "A"
        assert s.target_node == "B"
        assert s.lead_time == 1.0

    def test_with_lead_time(self):
        s = Shipment(name="S1", source_node="A", target_node="B", lead_time=3.0)
        assert s.lead_time == 3.0

    def test_frozen(self):
        s = Shipment(name="S1", source_node="A", target_node="B")
        with pytest.raises(ValidationError):
            s.source_node = "C"


class TestDemandSource:
    def test_create(self):
        d = DemandSource(name="D1", target_node="Retail")
        assert d.name == "D1"
        assert d.target_node == "Retail"

    def test_frozen(self):
        d = DemandSource(name="D1", target_node="Retail")
        with pytest.raises(ValidationError):
            d.target_node = "Other"


class TestOrderPolicy:
    def test_create_minimal(self):
        op = OrderPolicy(name="OP1", node="W1")
        assert op.node == "W1"
        assert op.inputs == []

    def test_create_with_inputs(self):
        op = OrderPolicy(name="OP1", node="W1", inputs=["W2", "W3"])
        assert op.inputs == ["W2", "W3"]

    def test_frozen(self):
        op = OrderPolicy(name="OP1", node="W1")
        with pytest.raises(ValidationError):
            op.node = "W2"

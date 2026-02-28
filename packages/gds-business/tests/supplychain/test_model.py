"""Tests for SupplyChainModel."""

import pytest

from gds_business.common.errors import BizValidationError
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)
from gds_business.supplychain.model import SupplyChainModel


class TestSupplyChainModelConstruction:
    def test_minimal(self):
        m = SupplyChainModel(name="test", nodes=[SupplyNode(name="W1")])
        assert m.name == "test"
        assert len(m.nodes) == 1

    def test_full_model(self):
        m = SupplyChainModel(
            name="test",
            nodes=[SupplyNode(name="W1"), SupplyNode(name="W2")],
            shipments=[Shipment(name="S1", source_node="W1", target_node="W2")],
            demand_sources=[DemandSource(name="D1", target_node="W2")],
            order_policies=[OrderPolicy(name="OP1", node="W2", inputs=["W1"])],
        )
        assert len(m.shipments) == 1
        assert len(m.demand_sources) == 1
        assert len(m.order_policies) == 1

    def test_no_nodes_fails(self):
        with pytest.raises(BizValidationError, match="at least one node"):
            SupplyChainModel(name="test", nodes=[])

    def test_duplicate_node_names_fails(self):
        with pytest.raises(BizValidationError, match="Duplicate node name"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1"), SupplyNode(name="W1")],
            )

    def test_shipment_source_invalid_fails(self):
        with pytest.raises(BizValidationError, match="source_node.*not a declared"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1")],
                shipments=[Shipment(name="S1", source_node="Z", target_node="W1")],
            )

    def test_shipment_target_invalid_fails(self):
        with pytest.raises(BizValidationError, match="target_node.*not a declared"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1")],
                shipments=[Shipment(name="S1", source_node="W1", target_node="Z")],
            )

    def test_demand_target_invalid_fails(self):
        with pytest.raises(BizValidationError, match="target_node.*not a declared"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1")],
                demand_sources=[DemandSource(name="D1", target_node="Z")],
            )

    def test_order_policy_node_invalid_fails(self):
        with pytest.raises(BizValidationError, match="node.*not a declared"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1")],
                order_policies=[OrderPolicy(name="OP1", node="Z")],
            )

    def test_order_policy_input_invalid_fails(self):
        with pytest.raises(BizValidationError, match="input.*not a declared"):
            SupplyChainModel(
                name="test",
                nodes=[SupplyNode(name="W1")],
                order_policies=[OrderPolicy(name="OP1", node="W1", inputs=["Z"])],
            )


class TestSupplyChainModelProperties:
    def test_node_names(self):
        m = SupplyChainModel(
            name="test",
            nodes=[SupplyNode(name="W1"), SupplyNode(name="W2")],
        )
        assert m.node_names == {"W1", "W2"}

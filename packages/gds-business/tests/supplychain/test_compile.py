"""Tests for supply chain compilation."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec

from gds_business.supplychain.compile import (
    compile_scn,
    compile_scn_to_system,
)
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)
from gds_business.supplychain.model import SupplyChainModel


def _beer_game() -> SupplyChainModel:
    """Classic beer distribution game — 4 echelons."""
    return SupplyChainModel(
        name="Beer Game",
        nodes=[
            SupplyNode(name="Factory", initial_inventory=100),
            SupplyNode(name="Distributor", initial_inventory=100),
            SupplyNode(name="Wholesaler", initial_inventory=100),
            SupplyNode(name="Retailer", initial_inventory=100),
        ],
        shipments=[
            Shipment(name="F->D", source_node="Factory", target_node="Distributor"),
            Shipment(name="D->W", source_node="Distributor", target_node="Wholesaler"),
            Shipment(name="W->R", source_node="Wholesaler", target_node="Retailer"),
        ],
        demand_sources=[
            DemandSource(name="Customer Demand", target_node="Retailer"),
        ],
        order_policies=[
            OrderPolicy(name="Retailer Policy", node="Retailer", inputs=["Retailer"]),
            OrderPolicy(
                name="Wholesaler Policy",
                node="Wholesaler",
                inputs=["Wholesaler"],
            ),
            OrderPolicy(
                name="Distributor Policy",
                node="Distributor",
                inputs=["Distributor"],
            ),
            OrderPolicy(name="Factory Policy", node="Factory", inputs=["Factory"]),
        ],
    )


def _simple_model() -> SupplyChainModel:
    return SupplyChainModel(
        name="Simple SCN",
        nodes=[SupplyNode(name="W1"), SupplyNode(name="W2")],
        shipments=[Shipment(name="S1", source_node="W1", target_node="W2")],
        demand_sources=[DemandSource(name="D1", target_node="W2")],
        order_policies=[OrderPolicy(name="OP1", node="W2", inputs=["W1"])],
    )


def _nodes_only() -> SupplyChainModel:
    return SupplyChainModel(
        name="Nodes Only",
        nodes=[SupplyNode(name="W1")],
    )


class TestCompileSCN:
    def test_returns_gds_spec(self):
        spec = compile_scn(_beer_game())
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Beer Game"

    def test_registers_types(self):
        spec = compile_scn(_beer_game())
        assert "SCN Inventory" in spec.types
        assert "SCN ShipmentRate" in spec.types
        assert "SCN Demand" in spec.types

    def test_registers_spaces(self):
        spec = compile_scn(_beer_game())
        assert "SCN InventorySpace" in spec.spaces
        assert "SCN ShipmentRateSpace" in spec.spaces
        assert "SCN DemandSpace" in spec.spaces

    def test_registers_entities(self):
        spec = compile_scn(_beer_game())
        # One entity per supply node
        assert len(spec.entities) == 4

    def test_block_roles(self):
        spec = compile_scn(_beer_game())
        boundary = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundary) == 1  # Customer Demand
        assert len(policies) == 4  # 4 order policies
        assert len(mechanisms) == 4  # 4 node mechanisms

    def test_registers_wirings(self):
        spec = compile_scn(_beer_game())
        assert len(spec.wirings) == 1

    def test_simple_spec(self):
        spec = compile_scn(_simple_model())
        assert len(spec.blocks) == 4  # 1 demand + 1 policy + 2 mechanisms

    def test_nodes_only_no_wiring(self):
        spec = compile_scn(_nodes_only())
        assert len(spec.wirings) == 0


class TestCompileSCNToSystem:
    def test_returns_system_ir(self):
        ir = compile_scn_to_system(_beer_game())
        assert isinstance(ir, SystemIR)
        assert ir.name == "Beer Game"

    def test_block_count(self):
        ir = compile_scn_to_system(_beer_game())
        # 1 demand + 4 policies + 4 mechanisms = 9
        assert len(ir.blocks) == 9

    def test_simple_model(self):
        ir = compile_scn_to_system(_simple_model())
        assert len(ir.blocks) == 4

    def test_nodes_only(self):
        ir = compile_scn_to_system(_nodes_only())
        assert len(ir.blocks) == 1


class TestSCNCanonical:
    """SCN should be stateful: h = f o g, with inventory state."""

    def test_canonical_stateful(self):
        spec = compile_scn(_beer_game())
        canon = project_canonical(spec)
        # 4 mechanisms (f), 4 policies + 1 boundary (g)
        assert len(canon.mechanism_blocks) == 4
        assert len(canon.policy_blocks) == 4
        assert len(canon.boundary_blocks) == 1
        assert len(canon.state_variables) == 4

    def test_canonical_no_control(self):
        spec = compile_scn(_beer_game())
        canon = project_canonical(spec)
        assert len(canon.control_blocks) == 0


class TestSCNModelCompileMethods:
    def test_model_compile(self):
        m = _beer_game()
        spec = m.compile()
        assert isinstance(spec, GDSSpec)

    def test_model_compile_system(self):
        m = _beer_game()
        ir = m.compile_system()
        assert isinstance(ir, SystemIR)

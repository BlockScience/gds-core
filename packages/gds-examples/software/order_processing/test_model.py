"""Tests for the E-Commerce Order Processing DFD model."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.ir.models import FlowDirection
from gds.query import SpecQuery
from gds.verification.engine import verify
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import (
    check_completeness,
    check_determinism,
    check_type_safety,
)
from gds_software.verification.engine import verify as sw_verify
from software.order_processing.model import (
    build_canonical,
    build_model,
    build_spec,
    build_system,
)

# ── Model Declaration ──────────────────────────────────────────


class TestModel:
    def test_two_external_entities(self):
        model = build_model()
        assert len(model.external_entities) == 2
        assert model.external_names == {"Customer", "Payment Provider"}

    def test_three_processes(self):
        model = build_model()
        assert len(model.processes) == 3
        assert model.process_names == {
            "Validate Order",
            "Process Payment",
            "Fulfill Order",
        }

    def test_two_data_stores(self):
        model = build_model()
        assert len(model.data_stores) == 2
        assert model.store_names == {"Orders DB", "Inventory DB"}

    def test_eleven_data_flows(self):
        model = build_model()
        assert len(model.data_flows) == 11

    def test_flow_names(self):
        model = build_model()
        flow_names = {f.name for f in model.data_flows}
        expected = {
            "Order Request",
            "Payment Request",
            "Payment Authorization",
            "Payment Confirmation",
            "Fulfillment Request",
            "Order Status",
            "Order Record",
            "Order Lookup",
            "Order Details",
            "Stock Update",
            "Stock Check",
        }
        assert flow_names == expected

    def test_customer_flows(self):
        """Customer is source of Order Request and target of Order Status."""
        model = build_model()
        from_customer = [f for f in model.data_flows if f.source == "Customer"]
        to_customer = [f for f in model.data_flows if f.target == "Customer"]
        assert len(from_customer) == 1
        assert from_customer[0].name == "Order Request"
        assert len(to_customer) == 1
        assert to_customer[0].name == "Order Status"

    def test_payment_provider_flows(self):
        """Payment Provider sends confirmation and receives authorization."""
        model = build_model()
        from_pp = [f for f in model.data_flows if f.source == "Payment Provider"]
        to_pp = [f for f in model.data_flows if f.target == "Payment Provider"]
        assert len(from_pp) == 1
        assert from_pp[0].name == "Payment Confirmation"
        assert len(to_pp) == 1
        assert to_pp[0].name == "Payment Authorization"

    def test_all_element_names(self):
        model = build_model()
        assert len(model.element_names) == 7  # 2 + 3 + 2


# ── DFD Domain Verification ──────────────────────────────────────


class TestDFDVerification:
    def test_dfd_checks_pass(self):
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        errors = [
            f for f in report.findings if not f.passed and f.severity.value == "error"
        ]
        assert errors == [], [f.message for f in errors]

    def test_process_connectivity(self):
        """DFD-001: Every process has at least one connected flow."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        failures = [
            f for f in report.findings if f.check_id == "DFD-001" and not f.passed
        ]
        assert failures == []

    def test_flow_validity(self):
        """DFD-002: All flow sources/targets are declared elements."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        failures = [
            f for f in report.findings if f.check_id == "DFD-002" and not f.passed
        ]
        assert failures == []

    def test_no_ext_to_ext(self):
        """DFD-003: No direct flows between external entities."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        failures = [
            f for f in report.findings if f.check_id == "DFD-003" and not f.passed
        ]
        assert failures == []

    def test_store_connectivity(self):
        """DFD-004: Every data store has at least one connected flow."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        failures = [
            f for f in report.findings if f.check_id == "DFD-004" and not f.passed
        ]
        assert failures == []

    def test_process_output(self):
        """DFD-005: Every process has at least one outgoing flow."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=False)
        failures = [
            f for f in report.findings if f.check_id == "DFD-005" and not f.passed
        ]
        assert failures == []


# ── GDSSpec (compiled from DFD) ────────────────────────────────


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert {"Orders DB", "Inventory DB"} == set(spec.entities.keys())

    def test_entities_have_content_variable(self):
        spec = build_spec()
        for entity in spec.entities.values():
            assert "content" in entity.variables

    def test_seven_blocks(self):
        """2 externals + 3 processes + 2 store mechanisms = 7 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 7

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 2  # Customer, Payment Provider
        assert len(policies) == 3  # Validate Order, Process Payment, Fulfill Order
        assert len(mechanisms) == 2  # Orders DB Store, Inventory DB Store

    def test_externals_are_boundary_actions(self):
        spec = build_spec()
        for name in ["Customer", "Payment Provider"]:
            block = spec.blocks[name]
            assert isinstance(block, BoundaryAction)
            assert block.interface.forward_in == ()

    def test_processes_are_policies(self):
        spec = build_spec()
        for name in ["Validate Order", "Process Payment", "Fulfill Order"]:
            assert isinstance(spec.blocks[name], Policy)

    def test_store_mechanisms(self):
        spec = build_spec()
        for store_name in ["Orders DB", "Inventory DB"]:
            block = spec.blocks[f"{store_name} Store"]
            assert isinstance(block, Mechanism)
            assert (store_name, "content") in block.updates

    def test_three_types_registered(self):
        spec = build_spec()
        type_names = set(spec.types.keys())
        assert "DFD Signal" in type_names
        assert "DFD Data" in type_names
        assert "DFD Content" in type_names

    def test_three_spaces_registered(self):
        spec = build_spec()
        space_names = set(spec.spaces.keys())
        assert "DFD SignalSpace" in space_names
        assert "DFD DataSpace" in space_names
        assert "DFD ContentSpace" in space_names


# ── Canonical Projection ───────────────────────────────────────


class TestCanonical:
    def test_state_dim_equals_two(self):
        """dim(X) = 2: Orders DB content, Inventory DB content."""
        c = build_canonical()
        assert len(c.state_variables) == 2

    def test_input_dim_equals_two(self):
        """dim(U) = 2: Customer, Payment Provider."""
        c = build_canonical()
        assert len(c.boundary_blocks) == 2
        assert "Customer" in c.boundary_blocks
        assert "Payment Provider" in c.boundary_blocks

    def test_two_mechanisms(self):
        """|f| = 2: Orders DB Store, Inventory DB Store."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 2
        assert "Orders DB Store" in c.mechanism_blocks
        assert "Inventory DB Store" in c.mechanism_blocks

    def test_three_policies(self):
        """|g| = 3: Validate Order, Process Payment, Fulfill Order."""
        c = build_canonical()
        assert len(c.policy_blocks) == 3

    def test_no_control_blocks(self):
        """ControlAction unused in DFD DSL."""
        c = build_canonical()
        assert len(c.control_blocks) == 0

    def test_role_partition_complete(self):
        """Every block appears in exactly one canonical role."""
        spec = build_spec()
        c = build_canonical()
        all_canonical = (
            set(c.boundary_blocks)
            | set(c.policy_blocks)
            | set(c.mechanism_blocks)
            | set(c.control_blocks)
        )
        assert all_canonical == set(spec.blocks.keys())

    def test_role_partition_disjoint(self):
        c = build_canonical()
        sets = [
            set(c.boundary_blocks),
            set(c.policy_blocks),
            set(c.mechanism_blocks),
            set(c.control_blocks),
        ]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i] & sets[j] == set()


# ── SystemIR and Composition ──────────────────────────────────


class TestSystem:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Order Processing"

    def test_seven_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 7

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "Customer",
            "Payment Provider",
            "Validate Order",
            "Process Payment",
            "Fulfill Order",
            "Orders DB Store",
            "Inventory DB Store",
        }
        assert names == expected

    def test_temporal_wirings(self):
        """Three temporal loops: store content feeds processes across timesteps.

        Orders DB Store -> Process Payment,
        Orders DB Store -> Fulfill Order,
        Inventory DB Store -> Fulfill Order.
        """
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 3

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_feedback_wirings(self):
        """No within-timestep backward flow in DFD."""
        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 0


# ── GDS Verification ──────────────────────────────────────────


class TestVerification:
    def test_generic_checks_pass(self):
        checks = [
            check_g001_domain_codomain_matching,
            check_g003_direction_consistency,
            check_g004_dangling_wirings,
            check_g005_sequential_type_compatibility,
            check_g006_covariant_acyclicity,
        ]
        system = build_system()
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]

    def test_completeness(self):
        spec = build_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_determinism(self):
        spec = build_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)

    def test_dfd_and_gds_combined(self):
        """Full verification: DFD + GDS checks together."""
        model = build_model()
        report = sw_verify(model, include_gds_checks=True)
        assert report.checks_total > 0
        dfd_findings = [f for f in report.findings if f.check_id.startswith("DFD-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(dfd_findings) > 0
        assert len(gds_findings) > 0


# ── Query API ─────────────────────────────────────────────────


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Orders DB Store" in updates["Orders DB"]["content"]
        assert "Inventory DB Store" in updates["Inventory DB"]["content"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 2
        assert len(by_kind["policy"]) == 3
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_orders_db(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Orders DB", "content")
        assert "Orders DB Store" in affecting

    def test_blocks_affecting_inventory_db(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Inventory DB", "content")
        assert "Inventory DB Store" in affecting

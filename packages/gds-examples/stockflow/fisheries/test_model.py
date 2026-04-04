"""Tests for the Gordon-Schaefer Bioeconomic Fishery model."""

import pytest

from fisheries.model import (
    BiomassRate,
    Currency,
    EffortLevel,
    GrowthParameter,
    Population,
    UnitFraction,
    build_spec,
    build_system,
    compute_growth,
    compute_harvest_pressure,
    compute_profit,
    enforce_quota,
    environmental_conditions,
    fish_stock,
    fleet,
    market_price,
    observe_effort,
    observe_stock,
    update_fish_stock,
    update_fleet,
)
from gds.blocks.composition import FeedbackLoop
from gds.blocks.errors import GDSCompositionError
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.canonical import project_canonical
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

# -- Types -------------------------------------------------------------------


class TestTypes:
    def test_population_non_negative(self):
        assert Population.check_value(0.0)
        assert Population.check_value(1000.5)
        assert not Population.check_value(-1.0)

    def test_population_rejects_int(self):
        assert not Population.check_value(100)

    def test_biomass_rate_allows_negative(self):
        assert BiomassRate.check_value(-50.0)
        assert BiomassRate.check_value(0.0)
        assert BiomassRate.check_value(100.0)

    def test_effort_level_non_negative(self):
        assert EffortLevel.check_value(0.0)
        assert EffortLevel.check_value(50.0)
        assert not EffortLevel.check_value(-0.1)

    def test_currency_allows_negative(self):
        assert Currency.check_value(-1000.0)
        assert Currency.check_value(0.0)
        assert Currency.check_value(500.0)

    def test_unit_fraction_range(self):
        assert UnitFraction.check_value(0.5)
        assert UnitFraction.check_value(1.0)
        assert UnitFraction.check_value(2.0)
        assert not UnitFraction.check_value(0.0)
        assert not UnitFraction.check_value(2.1)

    def test_growth_parameter_positive(self):
        assert GrowthParameter.check_value(0.01)
        assert GrowthParameter.check_value(5.0)
        assert not GrowthParameter.check_value(0.0)
        assert not GrowthParameter.check_value(-1.0)


# -- Entities ----------------------------------------------------------------


class TestEntities:
    def test_fish_stock_has_biomass(self):
        assert "biomass" in fish_stock.variables
        assert fish_stock.variables["biomass"].symbol == "N"

    def test_fleet_has_effort(self):
        assert "effort" in fleet.variables
        assert fleet.variables["effort"].symbol == "E"

    def test_fish_stock_validates_state(self):
        assert fish_stock.validate_state({"biomass": 1000.0}) == []

    def test_fleet_validates_state(self):
        assert fleet.validate_state({"effort": 50.0}) == []

    def test_fish_stock_rejects_negative(self):
        errors = fish_stock.validate_state({"biomass": -10.0})
        assert len(errors) > 0


# -- Blocks ------------------------------------------------------------------


class TestBlocks:
    def test_observe_stock_is_boundary(self):
        assert isinstance(observe_stock, BoundaryAction)
        assert observe_stock.interface.forward_in == ()
        assert len(observe_stock.interface.forward_out) == 1

    def test_observe_effort_is_boundary(self):
        assert isinstance(observe_effort, BoundaryAction)
        assert observe_effort.interface.forward_in == ()

    def test_environmental_conditions_is_boundary(self):
        assert isinstance(environmental_conditions, BoundaryAction)
        assert environmental_conditions.interface.forward_in == ()

    def test_market_price_is_boundary(self):
        assert isinstance(market_price, BoundaryAction)
        assert market_price.interface.forward_in == ()

    def test_compute_growth_is_policy(self):
        assert isinstance(compute_growth, Policy)
        assert len(compute_growth.interface.forward_in) == 2
        assert len(compute_growth.interface.forward_out) == 1

    def test_compute_harvest_pressure_has_backward_in(self):
        assert isinstance(compute_harvest_pressure, Policy)
        assert len(compute_harvest_pressure.interface.backward_in) == 1
        bw_in = compute_harvest_pressure.interface.backward_in
        assert bw_in[0].name == "Quota Feedback"

    def test_compute_profit_is_policy(self):
        assert isinstance(compute_profit, Policy)
        assert len(compute_profit.interface.forward_in) == 2

    def test_enforce_quota_is_control_action(self):
        assert isinstance(enforce_quota, ControlAction)
        assert len(enforce_quota.interface.forward_in) == 1
        assert len(enforce_quota.interface.forward_out) == 1
        assert len(enforce_quota.interface.backward_out) == 1
        assert enforce_quota.interface.backward_out[0].name == "Quota Feedback"

    def test_update_fish_stock_is_mechanism_with_loop_output(self):
        assert isinstance(update_fish_stock, Mechanism)
        assert update_fish_stock.updates == [("Fish Stock", "biomass")]
        assert len(update_fish_stock.interface.forward_out) == 1
        assert update_fish_stock.interface.forward_out[0].name == "Stock Observation"

    def test_update_fleet_is_mechanism_with_loop_output(self):
        assert isinstance(update_fleet, Mechanism)
        assert update_fleet.updates == [("Fleet", "effort")]
        assert len(update_fleet.interface.forward_out) == 1
        assert update_fleet.interface.forward_out[0].name == "Effort Observation"

    def test_mechanism_cannot_have_backward_ports(self):
        from gds.types.interface import Interface, port

        with pytest.raises(GDSCompositionError, match="backward ports must be empty"):
            Mechanism(
                name="Bad",
                interface=Interface(backward_out=(port("Signal"),)),
            )

    def test_four_boundary_actions(self):
        blocks = [observe_stock, observe_effort, environmental_conditions, market_price]
        for b in blocks:
            assert isinstance(b, BoundaryAction)

    def test_three_policies(self):
        blocks = [compute_growth, compute_harvest_pressure, compute_profit]
        for b in blocks:
            assert isinstance(b, Policy)

    def test_one_control_action(self):
        assert isinstance(enforce_quota, ControlAction)

    def test_two_mechanisms(self):
        blocks = [update_fish_stock, update_fleet]
        for b in blocks:
            assert isinstance(b, Mechanism)


# -- Composition -------------------------------------------------------------


class TestComposition:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Gordon-Schaefer Fishery"

    def test_flatten_yields_ten_blocks(self):
        tier_0 = (
            observe_stock | observe_effort | environmental_conditions | market_price
        )
        tier_1 = compute_growth | compute_harvest_pressure
        tier_4 = update_fish_stock | update_fleet
        pipeline = tier_0 >> tier_1 >> enforce_quota >> compute_profit >> tier_4
        flat = pipeline.flatten()
        assert len(flat) == 10

    def test_feedback_loop_wraps_pipeline(self):
        tier_0 = (
            observe_stock | observe_effort | environmental_conditions | market_price
        )
        tier_1 = compute_growth | compute_harvest_pressure
        tier_4 = update_fish_stock | update_fleet
        pipeline = tier_0 >> tier_1 >> enforce_quota >> compute_profit >> tier_4
        from gds.blocks.composition import Wiring

        with_feedback = pipeline.feedback(
            [
                Wiring(
                    source_block="Enforce Quota",
                    source_port="Quota Feedback",
                    target_block="Compute Harvest Pressure",
                    target_port="Quota Feedback",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ]
        )
        assert isinstance(with_feedback, FeedbackLoop)

    def test_combined_feedback_and_loop(self):
        """First GDS example to chain .feedback() and .loop()."""
        system = build_system()
        assert len(system.blocks) == 10

    def test_feedback_wirings(self):
        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 1
        assert feedback[0].direction == FlowDirection.CONTRAVARIANT

    def test_temporal_wirings(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 3

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_contravariant_temporal(self):
        """CONTRAVARIANT .loop() is invalid — only COVARIANT allowed."""
        from gds.blocks.composition import Wiring
        from gds.blocks.errors import GDSTypeError

        tier_0 = (
            observe_stock | observe_effort | environmental_conditions | market_price
        )
        tier_1 = compute_growth | compute_harvest_pressure
        tier_4 = update_fish_stock | update_fleet
        pipeline = tier_0 >> tier_1 >> enforce_quota >> compute_profit >> tier_4

        with pytest.raises(GDSTypeError):
            pipeline.loop(
                [
                    Wiring(
                        source_block="Update Fish Stock",
                        source_port="Stock Observation",
                        target_block="Compute Growth",
                        target_port="Stock Observation",
                        direction=FlowDirection.CONTRAVARIANT,
                    )
                ]
            )


# -- Spec --------------------------------------------------------------------


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert {"Fish Stock", "Fleet"} == set(spec.entities.keys())

    def test_ten_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 10

    def test_block_names(self):
        spec = build_spec()
        expected = {
            "Observe Stock",
            "Observe Effort",
            "Environmental Conditions",
            "Market Price",
            "Compute Growth",
            "Compute Harvest Pressure",
            "Enforce Quota",
            "Compute Profit",
            "Update Fish Stock",
            "Update Fleet",
        }
        assert set(spec.blocks.keys()) == expected

    def test_six_parameters(self):
        spec = build_spec()
        expected = {
            "intrinsic_growth_rate",
            "base_carrying_capacity",
            "catchability_coefficient",
            "cost_per_unit_effort",
            "quota_limit",
            "effort_adjustment_speed",
        }
        assert set(spec.parameters.keys()) == expected

    def test_nine_spaces(self):
        spec = build_spec()
        assert len(spec.spaces) == 9


# -- Canonical Projection ----------------------------------------------------


class TestCanonical:
    def test_state_dim_two(self):
        c = project_canonical(build_spec())
        assert len(c.state_variables) == 2

    def test_four_boundary_blocks(self):
        c = project_canonical(build_spec())
        assert len(c.boundary_blocks) == 4

    def test_three_policy_blocks(self):
        c = project_canonical(build_spec())
        assert len(c.policy_blocks) == 3

    def test_one_control_block(self):
        c = project_canonical(build_spec())
        assert len(c.control_blocks) == 1
        assert "Enforce Quota" in c.control_blocks

    def test_two_mechanism_blocks(self):
        c = project_canonical(build_spec())
        assert len(c.mechanism_blocks) == 2

    def test_role_partition_complete(self):
        spec = build_spec()
        c = project_canonical(spec)
        all_canonical = (
            set(c.boundary_blocks)
            | set(c.policy_blocks)
            | set(c.mechanism_blocks)
            | set(c.control_blocks)
        )
        assert all_canonical == set(spec.blocks.keys())

    def test_role_partition_disjoint(self):
        c = project_canonical(build_spec())
        sets = [
            set(c.boundary_blocks),
            set(c.policy_blocks),
            set(c.mechanism_blocks),
            set(c.control_blocks),
        ]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i] & sets[j] == set()


# -- Verification ------------------------------------------------------------


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


# -- Query API ---------------------------------------------------------------


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Update Fish Stock" in updates["Fish Stock"]["biomass"]
        assert "Update Fleet" in updates["Fleet"]["effort"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 4
        assert len(by_kind["policy"]) == 3
        assert len(by_kind["control"]) == 1
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_fish_stock(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Fish Stock", "biomass")
        assert "Update Fish Stock" in affecting

    def test_blocks_affecting_fleet(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Fleet", "effort")
        assert "Update Fleet" in affecting

    def test_param_to_blocks_growth(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Compute Growth" in mapping["intrinsic_growth_rate"]
        assert "Compute Growth" in mapping["base_carrying_capacity"]

    def test_param_to_blocks_harvest(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Compute Harvest Pressure" in mapping["catchability_coefficient"]

    def test_param_to_blocks_quota(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Enforce Quota" in mapping["quota_limit"]

    def test_param_to_blocks_effort(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Update Fleet" in mapping["effort_adjustment_speed"]

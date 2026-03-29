"""Tests for the Gordon-Schaefer fishery model (raw GDS, V1 unregulated).

Covers: types, entities, blocks, composition, spec, verification,
canonical projection, and analytical benchmark validation.
"""

import pytest
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.query import SpecQuery
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
    check_parameter_references,
    check_type_safety,
)
from gds.verification.engine import verify

from fishery.model import (
    DEFAULTS,
    Biomass,
    Capacity,
    Catch,
    CostParam,
    Effort,
    N_FISHERS,
    Price,
    Profit,
    RateParam,
    analytical_benchmarks,
    build_canonical,
    build_spec,
    build_system,
    fish_population,
    growth_rate,
    market_price,
    population_dynamics,
    stock_observer,
)


# ══════════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════════


class TestTypes:
    def test_biomass_non_negative(self):
        assert Biomass.check_value(0.0)
        assert Biomass.check_value(100_000.0)
        assert not Biomass.check_value(-1.0)

    def test_effort_non_negative(self):
        assert Effort.check_value(0.0)
        assert Effort.check_value(500.0)
        assert not Effort.check_value(-0.1)

    def test_catch_non_negative(self):
        assert Catch.check_value(0.0)
        assert not Catch.check_value(-1.0)

    def test_profit_allows_negative(self):
        assert Profit.check_value(-1000.0)
        assert Profit.check_value(0.0)
        assert Profit.check_value(5000.0)

    def test_price_positive(self):
        assert Price.check_value(100.0)
        assert not Price.check_value(0.0)
        assert not Price.check_value(-1.0)

    def test_rate_param_positive(self):
        assert RateParam.check_value(0.5)
        assert not RateParam.check_value(0.0)

    def test_capacity_positive(self):
        assert Capacity.check_value(100_000.0)
        assert not Capacity.check_value(0.0)

    def test_cost_param_positive(self):
        assert CostParam.check_value(5000.0)
        assert not CostParam.check_value(0.0)


# ══════════════════════════════════════════════════════════════════
# Entities
# ══════════════════════════════════════════════════════════════════


class TestEntities:
    def test_fish_population_has_level(self):
        assert "level" in fish_population.variables
        assert fish_population.variables["level"].typedef is Biomass

    def test_fish_population_symbol(self):
        assert fish_population.variables["level"].symbol == "N"


# ══════════════════════════════════════════════════════════════════
# Blocks
# ══════════════════════════════════════════════════════════════════


class TestBlocks:
    def test_market_price_is_boundary(self):
        assert isinstance(market_price, BoundaryAction)
        assert market_price.interface.forward_in == ()
        assert len(market_price.interface.forward_out) == 1

    def test_stock_observer_is_policy(self):
        assert isinstance(stock_observer, Policy)
        assert len(stock_observer.interface.forward_in) == 1
        assert len(stock_observer.interface.forward_out) == 1

    def test_growth_rate_is_policy(self):
        assert isinstance(growth_rate, Policy)
        assert "r" in growth_rate.params_used
        assert "K" in growth_rate.params_used

    def test_population_dynamics_is_mechanism(self):
        assert isinstance(population_dynamics, Mechanism)
        assert population_dynamics.updates == [("Fish Population", "level")]
        assert len(population_dynamics.interface.forward_in) == 2
        assert len(population_dynamics.interface.forward_out) == 1  # for .loop()


# ══════════════════════════════════════════════════════════════════
# Spec
# ══════════════════════════════════════════════════════════════════


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == []

    def test_entity_count(self):
        spec = build_spec()
        assert len(spec.entities) == 1 + N_FISHERS  # population + n fishers

    def test_parameter_names(self):
        spec = build_spec()
        expected = {"r", "K", "q", "p", "c", "m"}
        assert spec.parameter_schema.names() == expected

    def test_parameter_bounds(self):
        spec = build_spec()
        r_param = spec.parameter_schema.parameters["r"]
        assert r_param.bounds == (0.05, 2.0)

    def test_block_count(self):
        spec = build_spec()
        n = N_FISHERS
        # 1 boundary + 1 observer + n fishers + 1 harvest + 1 growth
        # + 1 pop dynamics + n profit mechanisms
        expected = 1 + 1 + n + 1 + 1 + 1 + n
        assert len(spec.blocks) == expected

    def test_has_admissibility_constraint(self):
        spec = build_spec()
        assert len(spec.admissibility_constraints) >= 1
        assert "market_viability" in spec.admissibility_constraints

    def test_has_transition_signatures(self):
        spec = build_spec()
        assert len(spec.transition_signatures) >= 1 + N_FISHERS
        mech_names = [ts.mechanism for ts in spec.transition_signatures.values()]
        assert "Population Dynamics" in mech_names


# ══════════════════════════════════════════════════════════════════
# Verification
# ══════════════════════════════════════════════════════════════════


class TestVerification:
    def test_generic_checks_pass(self):
        """G-001, G-003..G-006 pass. G-002 skipped (flags BoundaryAction)."""
        checks = [
            check_g001_domain_codomain_matching,
            check_g003_direction_consistency,
            check_g004_dangling_wirings,
            check_g005_sequential_type_compatibility,
            check_g006_covariant_acyclicity,
        ]
        system = build_system()
        report = verify(system, checks=checks)
        assert report.errors == 0, f"Generic check failures: {report.findings}"

    def test_completeness(self):
        findings = check_completeness(build_spec())
        assert all(f.passed for f in findings)

    def test_determinism(self):
        findings = check_determinism(build_spec())
        assert all(f.passed for f in findings)

    def test_type_safety(self):
        findings = check_type_safety(build_spec())
        assert all(f.passed for f in findings)

    def test_parameter_references(self):
        findings = check_parameter_references(build_spec())
        assert all(f.passed for f in findings)


# ══════════════════════════════════════════════════════════════════
# Canonical projection
# ══════════════════════════════════════════════════════════════════


class TestCanonical:
    def test_canonical_projects(self):
        canonical = build_canonical()
        assert canonical is not None

    def test_state_variables(self):
        canonical = build_canonical()
        # N + n profit variables
        assert len(canonical.state_variables) == 1 + N_FISHERS

    def test_has_boundary_blocks(self):
        canonical = build_canonical()
        assert "Market Price" in canonical.boundary_blocks

    def test_has_mechanism_blocks(self):
        canonical = build_canonical()
        assert "Population Dynamics" in canonical.mechanism_blocks

    def test_has_policy_blocks(self):
        canonical = build_canonical()
        assert "Stock Observer" in canonical.policy_blocks
        assert "Growth Rate" in canonical.policy_blocks

    def test_update_map_covers_population(self):
        canonical = build_canonical()
        mech_names = [name for name, _ in canonical.update_map]
        assert "Population Dynamics" in mech_names

    def test_formula_renders(self):
        canonical = build_canonical()
        formula = canonical.formula()
        assert "h" in formula
        assert "f" in formula
        assert "g" in formula


# ══════════════════════════════════════════════════════════════════
# Query
# ══════════════════════════════════════════════════════════════════


class TestQuery:
    def test_param_to_blocks(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "r" in mapping
        assert "Growth Rate" in mapping["r"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert "boundary" in by_kind
        assert "policy" in by_kind
        assert "mechanism" in by_kind

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        update_map = q.entity_update_map()
        assert "Fish Population" in update_map
        assert "level" in update_map["Fish Population"]


# ══════════════════════════════════════════════════════════════════
# Analytical benchmarks
# ══════════════════════════════════════════════════════════════════


class TestBenchmarks:
    """Validate Gordon-Schaefer closed-form results."""

    def setup_method(self):
        self.b = analytical_benchmarks()

    def test_msy_stock(self):
        assert self.b["N_MSY"] == pytest.approx(50_000.0)

    def test_msy_harvest(self):
        assert self.b["H_MSY"] == pytest.approx(12_500.0)

    def test_bionomic_stock(self):
        assert self.b["N_inf"] == pytest.approx(25_000.0)

    def test_overfishing_holds(self):
        assert self.b["overfishing"], "N_inf should be < N_MSY"

    def test_ordering(self):
        assert self.b["N_inf"] < self.b["N_MSY"] < self.b["N_MEY"] < DEFAULTS["K"]

    def test_nash_between_inf_and_K(self):
        assert self.b["N_inf"] < self.b["N_nash"] < DEFAULTS["K"]

    def test_sole_owner_equals_mey(self):
        sole = analytical_benchmarks(n=1)
        assert sole["N_nash"] == pytest.approx(sole["N_MEY"])

    def test_effort_ratio(self):
        n = DEFAULTS["n"]
        expected = 2 * n / (n + 1)
        assert self.b["effort_ratio"] == pytest.approx(expected)

    def test_tragedy_limit(self):
        """As n -> infinity, N_nash -> N_inf."""
        large_n = analytical_benchmarks(n=1000)
        assert large_n["N_nash"] == pytest.approx(large_n["N_inf"], rel=1e-2)

    def test_optimal_quota_msy(self):
        assert self.b["Q_MSY"] == pytest.approx(self.b["H_MSY"])


# ══════════════════════════════════════════════════════════════════
# Parameterized: scale with number of fishers
# ══════════════════════════════════════════════════════════════════


class TestScaling:
    @pytest.mark.parametrize("n", [1, 2, 5, 10])
    def test_spec_validates_for_n_fishers(self, n):
        spec = build_spec(n)
        errors = spec.validate_spec()
        assert errors == []

    @pytest.mark.parametrize("n", [1, 2, 5, 10])
    def test_canonical_projects_for_n_fishers(self, n):
        canonical = build_canonical(n)
        assert len(canonical.state_variables) == 1 + n
        assert len(canonical.mechanism_blocks) == 1 + n

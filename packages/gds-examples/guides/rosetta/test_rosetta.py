"""Tests for the Cross-Domain Rosetta Stone example.

Tests all three domain views (stock-flow, control, game theory) of the
resource pool scenario, verifying that each compiles successfully, passes
verification, and produces the expected canonical decomposition.
"""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.ir.models import FlowDirection
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
from guides.rosetta.comparison import build_all_canonicals, canonical_spectrum_table
from guides.rosetta.control_view import (
    build_canonical as build_control_canonical,
)
from guides.rosetta.control_view import (
    build_model as build_control_model,
)
from guides.rosetta.control_view import (
    build_spec as build_control_spec,
)
from guides.rosetta.control_view import (
    build_system as build_control_system,
)
from guides.rosetta.game_view import (
    build_canonical as build_game_canonical,
)
from guides.rosetta.game_view import (
    build_pattern,
)
from guides.rosetta.game_view import (
    build_spec as build_game_spec,
)
from guides.rosetta.stockflow_view import (
    build_canonical as build_sf_canonical,
)
from guides.rosetta.stockflow_view import (
    build_model as build_sf_model,
)
from guides.rosetta.stockflow_view import (
    build_spec as build_sf_spec,
)
from guides.rosetta.stockflow_view import (
    build_system as build_sf_system,
)

# ── Stock-Flow View ──────────────────────────────────────────────


class TestStockFlowModel:
    def test_model_constructs(self):
        model = build_sf_model()
        assert model.name == "Resource Pool (Stock-Flow)"

    def test_one_stock(self):
        model = build_sf_model()
        assert len(model.stocks) == 1
        assert model.stocks[0].name == "ResourceLevel"

    def test_two_flows(self):
        model = build_sf_model()
        assert len(model.flows) == 2
        flow_names = {f.name for f in model.flows}
        assert flow_names == {"supply", "consumption"}

    def test_one_auxiliary(self):
        model = build_sf_model()
        assert len(model.auxiliaries) == 1
        assert model.auxiliaries[0].name == "net_rate"

    def test_two_converters(self):
        model = build_sf_model()
        assert len(model.converters) == 2
        converter_names = {c.name for c in model.converters}
        assert converter_names == {"supply_rate", "consumption_rate"}


class TestStockFlowSpec:
    def test_spec_validates(self):
        spec = build_sf_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_one_entity(self):
        spec = build_sf_spec()
        assert len(spec.entities) == 1
        assert "ResourceLevel" in spec.entities

    def test_block_count(self):
        """2 converters + 1 auxiliary + 2 flows + 1 mechanism = 6 blocks."""
        spec = build_sf_spec()
        assert len(spec.blocks) == 6

    def test_block_roles(self):
        spec = build_sf_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 2  # supply_rate, consumption_rate
        assert len(policies) == 3  # net_rate, supply, consumption
        assert len(mechanisms) == 1  # ResourceLevel Accumulation

    def test_two_parameters(self):
        spec = build_sf_spec()
        assert len(spec.parameters) == 2
        assert set(spec.parameters.keys()) == {"supply_rate", "consumption_rate"}


class TestStockFlowSystem:
    def test_system_compiles(self):
        system = build_sf_system()
        assert system.name == "Resource Pool (Stock-Flow)"
        assert len(system.blocks) == 6

    def test_generic_checks_pass(self):
        checks = [
            check_g001_domain_codomain_matching,
            check_g003_direction_consistency,
            check_g004_dangling_wirings,
            check_g005_sequential_type_compatibility,
            check_g006_covariant_acyclicity,
        ]
        system = build_sf_system()
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]


class TestStockFlowCanonical:
    def test_state_dim(self):
        c = build_sf_canonical()
        assert len(c.state_variables) == 1  # ResourceLevel.level

    def test_input_dim(self):
        c = build_sf_canonical()
        assert len(c.input_ports) == 2  # supply_rate, consumption_rate

    def test_mechanism_count(self):
        c = build_sf_canonical()
        assert len(c.mechanism_blocks) == 1

    def test_policy_count(self):
        c = build_sf_canonical()
        assert len(c.policy_blocks) == 3  # net_rate, supply, consumption

    def test_has_parameters(self):
        c = build_sf_canonical()
        assert c.has_parameters

    def test_formula(self):
        c = build_sf_canonical()
        assert "theta" in c.formula().lower() or "Θ" in c.formula()

    def test_completeness(self):
        spec = build_sf_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_determinism(self):
        spec = build_sf_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_sf_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


# ── Control View ─────────────────────────────────────────────────


class TestControlModel:
    def test_model_constructs(self):
        model = build_control_model()
        assert model.name == "Resource Pool (Control)"

    def test_one_state(self):
        model = build_control_model()
        assert len(model.states) == 1
        assert model.states[0].name == "resource_level"

    def test_one_input(self):
        model = build_control_model()
        assert len(model.inputs) == 1
        assert model.inputs[0].name == "target_level"

    def test_one_sensor(self):
        model = build_control_model()
        assert len(model.sensors) == 1
        assert model.sensors[0].name == "level_sensor"

    def test_one_controller(self):
        model = build_control_model()
        assert len(model.controllers) == 1
        assert model.controllers[0].name == "supply_controller"

    def test_controller_reads(self):
        model = build_control_model()
        ctrl = model.controllers[0]
        assert set(ctrl.reads) == {"level_sensor", "target_level"}

    def test_controller_drives(self):
        model = build_control_model()
        ctrl = model.controllers[0]
        assert set(ctrl.drives) == {"resource_level"}


class TestControlSpec:
    def test_spec_validates(self):
        spec = build_control_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_one_entity(self):
        spec = build_control_spec()
        assert len(spec.entities) == 1
        assert "resource_level" in spec.entities

    def test_four_blocks(self):
        """1 input + 1 sensor + 1 controller + 1 dynamics = 4 blocks."""
        spec = build_control_spec()
        assert len(spec.blocks) == 4

    def test_block_roles(self):
        spec = build_control_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 1  # target_level
        assert len(policies) == 2  # level_sensor, supply_controller
        assert len(mechanisms) == 1  # resource_level Dynamics

    def test_one_parameter(self):
        spec = build_control_spec()
        assert len(spec.parameters) == 1
        assert "target_level" in spec.parameters


class TestControlSystem:
    def test_system_compiles(self):
        system = build_control_system()
        assert system.name == "Resource Pool (Control)"
        assert len(system.blocks) == 4

    def test_temporal_wirings(self):
        system = build_control_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 1  # dynamics -> sensor

    def test_temporal_wirings_covariant(self):
        system = build_control_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_generic_checks_pass(self):
        checks = [
            check_g001_domain_codomain_matching,
            check_g003_direction_consistency,
            check_g004_dangling_wirings,
            check_g005_sequential_type_compatibility,
            check_g006_covariant_acyclicity,
        ]
        system = build_control_system()
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]


class TestControlCanonical:
    def test_state_dim(self):
        c = build_control_canonical()
        assert len(c.state_variables) == 1  # resource_level.value

    def test_input_dim(self):
        c = build_control_canonical()
        assert len(c.input_ports) == 1  # target_level

    def test_mechanism_count(self):
        c = build_control_canonical()
        assert len(c.mechanism_blocks) == 1

    def test_policy_count(self):
        c = build_control_canonical()
        assert len(c.policy_blocks) == 2  # sensor + controller

    def test_has_parameters(self):
        c = build_control_canonical()
        assert c.has_parameters

    def test_completeness(self):
        spec = build_control_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_determinism(self):
        spec = build_control_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_control_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


# ── Game Theory View ─────────────────────────────────────────────


class TestGamePattern:
    def test_pattern_constructs(self):
        pattern = build_pattern()
        assert pattern.name == "Resource Pool (Game)"

    def test_three_atomic_games(self):
        pattern = build_pattern()
        flat = pattern.game.flatten()
        assert len(flat) == 3
        names = {g.name for g in flat}
        assert names == {
            "Agent 1 Extraction",
            "Agent 2 Extraction",
            "Payoff Computation",
        }

    def test_one_input(self):
        pattern = build_pattern()
        assert len(pattern.inputs) == 1
        assert pattern.inputs[0].name == "Resource Availability"


class TestGameSpec:
    def test_spec_constructs(self):
        spec = build_game_spec()
        assert spec.name == "Resource Pool (Game)"

    def test_no_entities(self):
        """Games have no persistent state."""
        spec = build_game_spec()
        assert len(spec.entities) == 0

    def test_four_blocks(self):
        """3 games + 1 boundary input = 4 blocks."""
        spec = build_game_spec()
        assert len(spec.blocks) == 4

    def test_block_roles(self):
        spec = build_game_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 1  # Resource Availability
        assert len(policies) == 3  # 2 agents + payoff
        assert len(mechanisms) == 0  # no state updates

    def test_no_parameters(self):
        spec = build_game_spec()
        assert len(spec.parameters) == 0


class TestGameCanonical:
    def test_no_state(self):
        """Games are stateless: |X| = 0."""
        c = build_game_canonical()
        assert len(c.state_variables) == 0

    def test_one_input(self):
        c = build_game_canonical()
        assert len(c.input_ports) == 1

    def test_no_mechanisms(self):
        """Pure policy: |f| = 0."""
        c = build_game_canonical()
        assert len(c.mechanism_blocks) == 0

    def test_three_policies(self):
        """All games map to Policy: |g| = 3."""
        c = build_game_canonical()
        assert len(c.policy_blocks) == 3

    def test_no_parameters(self):
        c = build_game_canonical()
        assert not c.has_parameters

    def test_formula_is_pure_policy(self):
        """h = g (not h = f . g) because there are no mechanisms."""
        c = build_game_canonical()
        assert len(c.mechanism_blocks) == 0, "Game view should have no mechanisms"
        assert len(c.policy_blocks) > 0, "Game view should have policies"
        assert not c.has_parameters, "Game view should have no parameters"


# ── Cross-Domain Comparison ──────────────────────────────────────


class TestComparison:
    def test_all_canonicals_build(self):
        canonicals = build_all_canonicals()
        assert len(canonicals) == 3
        assert set(canonicals.keys()) == {"Stock-Flow", "Control", "Game Theory"}

    def test_spectrum_table_renders(self):
        table = canonical_spectrum_table()
        assert "Stock-Flow" in table
        assert "Control" in table
        assert "Game Theory" in table
        assert "|X|" in table

    def test_stockflow_is_dynamical(self):
        """Stock-flow has both g and f: dynamical character."""
        canonicals = build_all_canonicals()
        c = canonicals["Stock-Flow"]
        assert len(c.mechanism_blocks) > 0
        assert len(c.policy_blocks) > 0

    def test_control_is_dynamical(self):
        """Control has both g and f: dynamical character."""
        canonicals = build_all_canonicals()
        c = canonicals["Control"]
        assert len(c.mechanism_blocks) > 0
        assert len(c.policy_blocks) > 0

    def test_game_is_strategic(self):
        """Game theory has g but no f: strategic character."""
        canonicals = build_all_canonicals()
        c = canonicals["Game Theory"]
        assert len(c.mechanism_blocks) == 0
        assert len(c.policy_blocks) > 0

    def test_all_have_boundary_actions(self):
        """All three views have exogenous inputs."""
        canonicals = build_all_canonicals()
        for view_name, c in canonicals.items():
            assert len(c.boundary_blocks) > 0, f"{view_name} has no boundary actions"

    def test_state_dimensions_differ(self):
        """Stock-flow and control have state; games do not."""
        canonicals = build_all_canonicals()
        assert len(canonicals["Stock-Flow"].state_variables) > 0
        assert len(canonicals["Control"].state_variables) > 0
        assert len(canonicals["Game Theory"].state_variables) == 0

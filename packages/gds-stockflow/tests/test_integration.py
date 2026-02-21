"""End-to-end integration tests: declare → compile → verify → canonical."""

import pytest

from gds.canonical import project_canonical

from stockflow.dsl.compile import compile_model, compile_to_system
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel
from stockflow.verification.engine import verify


class TestPopulationEndToEnd:
    """Population dynamics: Births/Deaths with Birth Rate auxiliary."""

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Population Dynamics",
            stocks=[Stock(name="Population", initial=1000.0)],
            flows=[
                Flow(name="Births", target="Population"),
                Flow(name="Deaths", source="Population"),
            ],
            auxiliaries=[
                Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
                Auxiliary(name="Death Rate", inputs=["Population"]),
            ],
            converters=[Converter(name="Fertility")],
            description="Simple population dynamics model",
        )

    def test_compile_to_spec(self, model):
        spec = compile_model(model)
        assert spec.name == "Population Dynamics"
        assert len(spec.types) == 4  # Level, UnconstrainedLevel, Rate, Signal
        assert len(spec.spaces) == 4
        assert len(spec.entities) == 1  # Population
        assert len(spec.blocks) == 6  # 1 conv + 2 aux + 2 flow + 1 mech

    def test_compile_to_system_ir(self, model):
        ir = compile_to_system(model)
        assert ir.name == "Population Dynamics"
        assert len(ir.blocks) == 6
        temporal = [w for w in ir.wirings if w.is_temporal]
        # Population → Birth Rate, Population → Death Rate (aux only, not flows)
        assert len(temporal) == 2

    def test_verify_sf_no_errors(self, model):
        """All SF checks pass (no domain errors)."""
        report = verify(model, include_gds_checks=False)
        errors = [f for f in report.findings if not f.passed and f.severity == "error"]
        assert len(errors) == 0

    def test_verify_with_gds_runs(self, model):
        """GDS checks run without exceptions. Some G-002 findings are expected
        for BoundaryActions/Flows which have no forward_in by design."""
        report = verify(model, include_gds_checks=True)
        assert report.checks_total > 0
        sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(sf_findings) > 0
        assert len(gds_findings) > 0

    def test_canonical_projection(self, model):
        spec = compile_model(model)
        canonical = project_canonical(spec)
        # State space: Population entity with level variable
        assert len(canonical.state_variables) == 1
        assert canonical.state_variables[0] == ("Population", "level")
        # Input U: Fertility boundary action
        assert len(canonical.boundary_blocks) == 1
        assert "Fertility" in canonical.boundary_blocks
        # Policies: 2 aux + 2 flows
        assert len(canonical.policy_blocks) == 4
        # Mechanisms: 1 stock accumulator
        assert len(canonical.mechanism_blocks) == 1

    def test_spec_validates(self, model):
        spec = compile_model(model)
        errors = spec.validate_spec()
        assert len(errors) == 0, f"Spec validation errors: {errors}"


class TestPredatorPreyEndToEnd:
    """Two-stock predator-prey model."""

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Predator Prey",
            stocks=[
                Stock(name="Prey", initial=100.0),
                Stock(name="Predator", initial=20.0),
            ],
            flows=[
                Flow(name="Prey Births", target="Prey"),
                Flow(name="Prey Deaths", source="Prey"),
                Flow(name="Predator Births", target="Predator"),
                Flow(name="Predator Deaths", source="Predator"),
            ],
            auxiliaries=[
                Auxiliary(name="Prey Growth", inputs=["Prey"]),
                Auxiliary(name="Predation", inputs=["Prey", "Predator"]),
                Auxiliary(name="Predator Growth", inputs=["Predator", "Prey"]),
                Auxiliary(name="Predator Decline", inputs=["Predator"]),
            ],
        )

    def test_compile_two_stocks(self, model):
        spec = compile_model(model)
        assert "Prey" in spec.entities
        assert "Predator" in spec.entities
        assert len(spec.blocks) == 10  # 4 aux + 4 flow + 2 mech

    def test_system_ir_two_stocks(self, model):
        ir = compile_to_system(model)
        assert len(ir.blocks) == 10

    def test_verify_sf_no_errors(self, model):
        report = verify(model, include_gds_checks=False)
        errors = [f for f in report.findings if not f.passed and f.severity == "error"]
        assert len(errors) == 0


class TestMinimalModel:
    """Edge case: stock with no flows."""

    def test_single_stock(self):
        model = StockFlowModel(name="Minimal", stocks=[Stock(name="S")])
        ir = compile_to_system(model)
        assert len(ir.blocks) == 1

        report = verify(model, include_gds_checks=False)
        orphan = [f for f in report.findings if f.check_id == "SF-001" and not f.passed]
        assert len(orphan) == 1  # Warning: orphan stock


class TestSIRModel:
    """Classic SIR epidemiology model — 3 stocks, 2 flows, 2 auxiliaries."""

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="SIR",
            stocks=[
                Stock(name="Susceptible", initial=999.0),
                Stock(name="Infected", initial=1.0),
                Stock(name="Recovered", initial=0.0),
            ],
            flows=[
                Flow(name="Infection", source="Susceptible", target="Infected"),
                Flow(name="Recovery", source="Infected", target="Recovered"),
            ],
            auxiliaries=[
                Auxiliary(
                    name="Infection Rate",
                    inputs=["Susceptible", "Infected", "Contact Rate"],
                ),
                Auxiliary(name="Recovery Rate", inputs=["Infected", "Recovery Time"]),
            ],
            converters=[
                Converter(name="Contact Rate"),
                Converter(name="Recovery Time"),
            ],
        )

    def test_three_stocks(self, model):
        spec = compile_model(model)
        assert len(spec.entities) == 3
        assert len(spec.blocks) == 9  # 2 conv + 2 aux + 2 flow + 3 mech

    def test_verify_sf_no_errors(self, model):
        report = verify(model, include_gds_checks=False)
        errors = [f for f in report.findings if not f.passed and f.severity == "error"]
        assert len(errors) == 0

    def test_canonical(self, model):
        spec = compile_model(model)
        canonical = project_canonical(spec)
        assert len(canonical.state_variables) == 3  # S, I, R levels
        assert len(canonical.mechanism_blocks) == 3
        assert len(canonical.boundary_blocks) == 2  # Contact Rate, Recovery Time

    def test_conservation_structure(self, model):
        """Infection and Recovery are inter-stock flows (source AND target)."""
        ir = compile_to_system(model)
        block_names = {b.name for b in ir.blocks}
        assert "Susceptible Accumulation" in block_names
        assert "Infected Accumulation" in block_names
        assert "Recovered Accumulation" in block_names

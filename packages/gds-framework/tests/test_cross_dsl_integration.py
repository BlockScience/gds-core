"""Cross-DSL integration tests — round-trip compilation, canonical projection,
and error condition verification across all five GDS domain DSLs.

Tests the GDS universal substrate claim: every DSL compiles to GDSSpec,
produces valid SystemIR, passes verification, and yields correct canonical
h = f . g decomposition.

These tests require all DSL packages to be installed. When run in isolation
(e.g. ``--package gds-framework``), the entire module is skipped.

Run with:
    uv run pytest packages/gds-framework/tests/test_cross_dsl_integration.py -v
"""

import importlib

import pytest

from gds.canonical import project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec

# Skip entire module if any DSL package is missing (CI runs per-package)
_REQUIRED = ["stockflow", "gds_control", "ogs", "gds_software", "gds_business"]
_missing = [m for m in _REQUIRED if importlib.util.find_spec(m) is None]
pytestmark = pytest.mark.skipif(
    len(_missing) > 0,
    reason=f"Cross-DSL tests require all DSL packages; missing: {_missing}",
)

# ════════════════════════════════════════════════════════════════
# StockFlow DSL
# ════════════════════════════════════════════════════════════════


class TestStockFlowRoundTrip:
    """StockFlow: declare → compile → verify → canonical."""

    @pytest.fixture
    def minimal_model(self):
        from stockflow.dsl.elements import Flow, Stock
        from stockflow.dsl.model import StockFlowModel

        return StockFlowModel(
            name="Minimal SF",
            stocks=[Stock(name="Population", initial=100.0)],
            flows=[Flow(name="Growth", target="Population")],
        )

    @pytest.fixture
    def two_stock_model(self):
        from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
        from stockflow.dsl.model import StockFlowModel

        return StockFlowModel(
            name="Two Stock SF",
            stocks=[
                Stock(name="Prey", initial=100.0),
                Stock(name="Predator", initial=20.0),
            ],
            flows=[
                Flow(name="Prey Growth", target="Prey"),
                Flow(name="Predation", source="Prey", target="Predator"),
                Flow(name="Predator Death", source="Predator"),
            ],
            auxiliaries=[
                Auxiliary(name="Growth Rate", inputs=["Prey"]),
                Auxiliary(name="Predation Rate", inputs=["Prey", "Predator"]),
            ],
            converters=[Converter(name="Base Rate")],
        )

    def test_minimal_compile_to_spec(self, minimal_model):
        from stockflow.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Minimal SF"
        assert len(spec.blocks) > 0
        assert len(spec.entities) == 1

    def test_minimal_compile_to_system(self, minimal_model):
        from stockflow.dsl.compile import compile_to_system

        ir = compile_to_system(minimal_model)
        assert isinstance(ir, SystemIR)
        assert ir.name == "Minimal SF"

    def test_minimal_canonical(self, minimal_model):
        """1 stock → |X|=1, |f|=1, at least 1 policy."""
        from stockflow.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 1
        assert len(canon.mechanism_blocks) == 1
        assert len(canon.policy_blocks) >= 1

    def test_minimal_verify_no_domain_errors(self, minimal_model):
        from stockflow.verification.engine import verify

        report = verify(minimal_model, include_gds_checks=False)
        errors = [
            f for f in report.findings if not f.passed and f.severity.value == "error"
        ]
        assert errors == []

    def test_two_stock_canonical(self, two_stock_model):
        """2 stocks → |X|=2, |f|=2, policies include auxiliaries + flows."""
        from stockflow.dsl.compile import compile_model

        spec = compile_model(two_stock_model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 2
        assert len(canon.mechanism_blocks) == 2
        # 2 auxiliaries + 3 flows = 5 policies
        assert len(canon.policy_blocks) == 5
        # 1 converter = 1 boundary action
        assert len(canon.boundary_blocks) == 1

    def test_spec_validates(self, minimal_model):
        from stockflow.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        errors = spec.validate_spec()
        assert errors == []


# ════════════════════════════════════════════════════════════════
# Control DSL
# ════════════════════════════════════════════════════════════════


class TestControlRoundTrip:
    """Control: declare → compile → verify → canonical."""

    @pytest.fixture
    def minimal_model(self):
        from gds_control.dsl.elements import Controller, Input, Sensor, State
        from gds_control.dsl.model import ControlModel

        return ControlModel(
            name="Minimal Control",
            states=[State(name="x", initial=0.0)],
            inputs=[Input(name="r")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )

    @pytest.fixture
    def mimo_model(self):
        from gds_control.dsl.elements import Controller, Input, Sensor, State
        from gds_control.dsl.model import ControlModel

        return ControlModel(
            name="MIMO Control",
            states=[State(name="x1"), State(name="x2")],
            inputs=[Input(name="r1"), Input(name="r2")],
            sensors=[
                Sensor(name="y1", observes=["x1"]),
                Sensor(name="y2", observes=["x2"]),
            ],
            controllers=[
                Controller(name="K1", reads=["y1", "r1"], drives=["x1"]),
                Controller(name="K2", reads=["y2", "r2"], drives=["x2"]),
            ],
        )

    def test_minimal_compile_to_spec(self, minimal_model):
        from gds_control.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        assert isinstance(spec, GDSSpec)
        assert len(spec.entities) == 1
        assert len(spec.blocks) == 4  # input + sensor + controller + state

    def test_minimal_compile_to_system(self, minimal_model):
        from gds_control.dsl.compile import compile_to_system

        ir = compile_to_system(minimal_model)
        assert isinstance(ir, SystemIR)
        temporal = [w for w in ir.wirings if w.is_temporal]
        assert len(temporal) == 1  # state → sensor loop

    def test_minimal_canonical(self, minimal_model):
        """SISO: |X|=1, |f|=1, g = sensor + controller."""
        from gds_control.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 1
        assert len(canon.mechanism_blocks) == 1
        assert len(canon.policy_blocks) == 2  # sensor + controller
        assert len(canon.boundary_blocks) == 1  # input
        assert len(canon.control_blocks) == 0  # ControlAction unused

    def test_mimo_canonical(self, mimo_model):
        """MIMO: |X|=2, |f|=2, g = 2 sensors + 2 controllers."""
        from gds_control.dsl.compile import compile_model

        spec = compile_model(mimo_model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 2
        assert len(canon.mechanism_blocks) == 2
        assert len(canon.policy_blocks) == 4
        assert len(canon.boundary_blocks) == 2

    def test_verify_no_domain_errors(self, minimal_model):
        from gds_control.verification.engine import verify

        report = verify(minimal_model, include_gds_checks=False)
        errors = [
            f for f in report.findings if not f.passed and f.severity.value == "error"
        ]
        assert errors == []

    def test_spec_validates(self, minimal_model):
        from gds_control.dsl.compile import compile_model

        spec = compile_model(minimal_model)
        errors = spec.validate_spec()
        assert errors == []


# ════════════════════════════════════════════════════════════════
# OGS (Games) DSL
# ════════════════════════════════════════════════════════════════


class TestOGSRoundTrip:
    """OGS: Pattern → compile_pattern_to_spec → canonical."""

    @pytest.fixture
    def single_decision(self):
        from gds.types.interface import port
        from ogs.dsl.games import DecisionGame
        from ogs.dsl.pattern import Pattern
        from ogs.dsl.types import Signature

        game = DecisionGame(
            name="Player",
            signature=Signature(
                x=(port("Observation"),),
                y=(port("Choice"),),
                r=(port("Payoff"),),
            ),
        )
        return Pattern(name="Single Decision", game=game)

    @pytest.fixture
    def sequential_pattern(self):
        from gds.types.interface import port
        from ogs.dsl.games import CovariantFunction
        from ogs.dsl.pattern import Pattern, PatternInput
        from ogs.dsl.types import InputType, Signature

        a = CovariantFunction(
            name="Observe",
            signature=Signature(
                x=(port("Raw"),),
                y=(port("Processed"),),
            ),
        )
        b = CovariantFunction(
            name="Decide",
            signature=Signature(
                x=(port("Processed"),),
                y=(port("Action"),),
            ),
        )
        return Pattern(
            name="Sequential",
            game=a >> b,
            inputs=[
                PatternInput(
                    name="External",
                    input_type=InputType.SENSOR,
                    target_game="Observe",
                    flow_label="Raw",
                ),
            ],
        )

    def test_single_decision_to_spec(self, single_decision):
        from ogs.dsl.spec_bridge import compile_pattern_to_spec

        spec = compile_pattern_to_spec(single_decision)
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) == 1

    def test_single_decision_canonical(self, single_decision):
        """Games are pure policy: f=empty, X=empty, h=g."""
        from ogs.dsl.spec_bridge import compile_pattern_to_spec

        spec = compile_pattern_to_spec(single_decision)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 1

    def test_sequential_to_spec_with_boundary(self, sequential_pattern):
        from ogs.dsl.spec_bridge import compile_pattern_to_spec

        spec = compile_pattern_to_spec(sequential_pattern)
        assert len(spec.blocks) == 3  # 2 games + 1 boundary
        assert len(spec.entities) == 0  # no state

    def test_sequential_canonical(self, sequential_pattern):
        """Sequential pipeline: 2 policies, 1 boundary, no state."""
        from ogs.dsl.spec_bridge import compile_pattern_to_spec

        spec = compile_pattern_to_spec(sequential_pattern)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 2
        assert len(canon.boundary_blocks) == 1

    def test_pattern_ir_to_system_ir(self, single_decision):
        """PatternIR projects to SystemIR for GDS tooling interop."""
        from ogs.dsl.compile import compile_to_ir

        ir = compile_to_ir(single_decision)
        system_ir = ir.to_system_ir()
        assert isinstance(system_ir, SystemIR)
        assert len(system_ir.blocks) >= 1


# ════════════════════════════════════════════════════════════════
# Software DSL
# ════════════════════════════════════════════════════════════════


class TestSoftwareRoundTrip:
    """Software: each diagram type compiles through GDS pipeline."""

    @pytest.fixture
    def dfd_model(self):
        from gds_software.dfd.elements import (
            DataFlow,
            DataStore,
            ExternalEntity,
            Process,
        )
        from gds_software.dfd.model import DFDModel

        return DFDModel(
            name="DFD",
            external_entities=[ExternalEntity(name="User")],
            processes=[Process(name="Auth")],
            data_stores=[DataStore(name="DB")],
            data_flows=[
                DataFlow(name="Login", source="User", target="Auth"),
                DataFlow(name="Save", source="Auth", target="DB"),
            ],
        )

    @pytest.fixture
    def sm_model(self):
        from gds_software.statemachine.elements import Event, State, Transition
        from gds_software.statemachine.model import StateMachineModel

        return StateMachineModel(
            name="SM",
            states=[State(name="Off", is_initial=True), State(name="On")],
            events=[Event(name="Toggle")],
            transitions=[
                Transition(name="TurnOn", source="Off", target="On", event="Toggle"),
                Transition(name="TurnOff", source="On", target="Off", event="Toggle"),
            ],
        )

    @pytest.fixture
    def dep_model(self):
        from gds_software.dependency.elements import Dep, Module
        from gds_software.dependency.model import DependencyModel

        return DependencyModel(
            name="Dep",
            modules=[Module(name="core", layer=0), Module(name="api", layer=1)],
            deps=[Dep(source="api", target="core")],
        )

    def test_dfd_round_trip(self, dfd_model):
        spec = dfd_model.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

        ir = dfd_model.compile_system()
        assert isinstance(ir, SystemIR)

        canon = project_canonical(spec)
        # DFD with DataStore has mechanisms (state)
        assert len(canon.mechanism_blocks) > 0
        assert len(canon.boundary_blocks) > 0  # ExternalEntity → BoundaryAction

    def test_sm_round_trip(self, sm_model):
        spec = sm_model.compile()
        assert isinstance(spec, GDSSpec)

        ir = sm_model.compile_system()
        assert isinstance(ir, SystemIR)

        canon = project_canonical(spec)
        # State machine has state
        assert len(canon.mechanism_blocks) > 0

    def test_dep_stateless(self, dep_model):
        """Dependency graphs are stateless: h = g, no mechanisms."""
        spec = dep_model.compile()
        canon = project_canonical(spec)
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) > 0

    def test_dfd_verify(self, dfd_model):
        from gds_software.verification.engine import verify

        report = verify(dfd_model)
        assert report.system_name == "DFD"
        assert len(report.findings) > 0


# ════════════════════════════════════════════════════════════════
# Business DSL
# ════════════════════════════════════════════════════════════════


class TestBusinessRoundTrip:
    """Business: CLD, SCN, VSM compile through GDS pipeline."""

    @pytest.fixture
    def cld_model(self):
        from gds_business.cld.elements import CausalLink, Variable
        from gds_business.cld.model import CausalLoopModel

        return CausalLoopModel(
            name="Simple CLD",
            variables=[Variable(name="A"), Variable(name="B")],
            links=[
                CausalLink(source="A", target="B", polarity="+"),
                CausalLink(source="B", target="A", polarity="-"),
            ],
        )

    @pytest.fixture
    def scn_model(self):
        from gds_business.supplychain.elements import (
            DemandSource,
            OrderPolicy,
            Shipment,
            SupplyNode,
        )
        from gds_business.supplychain.model import SupplyChainModel

        return SupplyChainModel(
            name="Simple SCN",
            nodes=[
                SupplyNode(name="Factory"),
                SupplyNode(name="Retailer"),
            ],
            shipments=[
                Shipment(name="F->R", source="Factory", target="Retailer"),
            ],
            demand_sources=[
                DemandSource(name="Customer", target="Retailer"),
            ],
            order_policies=[
                OrderPolicy(name="Reorder", node="Retailer", inputs=["Retailer"]),
            ],
        )

    @pytest.fixture
    def vsm_stateless(self):
        from gds_business.vsm.elements import (
            Customer,
            MaterialFlow,
            ProcessStep,
            Supplier,
        )
        from gds_business.vsm.model import ValueStreamModel

        return ValueStreamModel(
            name="Stateless VSM",
            steps=[
                ProcessStep(name="Step1", cycle_time=10.0),
                ProcessStep(name="Step2", cycle_time=20.0),
            ],
            suppliers=[Supplier(name="Sup")],
            customers=[Customer(name="Cust", takt_time=30.0)],
            material_flows=[
                MaterialFlow(source="Sup", target="Step1"),
                MaterialFlow(source="Step1", target="Step2"),
                MaterialFlow(source="Step2", target="Cust"),
            ],
        )

    @pytest.fixture
    def vsm_stateful(self):
        from gds_business.vsm.elements import (
            InventoryBuffer,
            MaterialFlow,
            ProcessStep,
            Supplier,
        )
        from gds_business.vsm.model import ValueStreamModel

        return ValueStreamModel(
            name="Stateful VSM",
            steps=[
                ProcessStep(name="Cutting", cycle_time=30.0),
                ProcessStep(name="Assembly", cycle_time=25.0),
            ],
            buffers=[
                InventoryBuffer(name="WIP", between=("Cutting", "Assembly")),
            ],
            suppliers=[Supplier(name="Sup")],
            material_flows=[
                MaterialFlow(source="Sup", target="Cutting"),
                MaterialFlow(source="Cutting", target="WIP"),
            ],
        )

    def test_cld_stateless(self, cld_model):
        """CLD: |X|=0, |f|=0, h = g (stateless)."""
        spec = cld_model.compile()
        assert isinstance(spec, GDSSpec)

        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) > 0

    def test_cld_system_ir(self, cld_model):
        ir = cld_model.compile_system()
        assert isinstance(ir, SystemIR)
        assert ir.name == "Simple CLD"

    def test_scn_stateful(self, scn_model):
        """SCN: |X|>0, |f|>0, h = f . g (stateful)."""
        spec = scn_model.compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) > 0
        assert len(canon.mechanism_blocks) > 0
        assert len(canon.policy_blocks) > 0

    def test_vsm_stateless_canonical(self, vsm_stateless):
        """VSM without buffers: |X|=0, h = g."""
        spec = vsm_stateless.compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0

    def test_vsm_stateful_canonical(self, vsm_stateful):
        """VSM with buffers: |X|>0, h = f . g."""
        spec = vsm_stateful.compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) > 0
        assert len(canon.mechanism_blocks) > 0

    def test_business_verify(self, cld_model, scn_model):
        from gds_business.verification.engine import verify

        cld_report = verify(cld_model)
        assert cld_report.system_name == "Simple CLD"

        scn_report = verify(scn_model)
        assert scn_report.system_name == "Simple SCN"


# ════════════════════════════════════════════════════════════════
# Canonical Spectrum — cross-DSL comparison
# ════════════════════════════════════════════════════════════════


class TestCanonicalSpectrum:
    """Validate the canonical h = f . g spectrum across all DSLs.

    The GDS canonical decomposition should reflect each domain's nature:
    - Stateless domains (CLD, OGS, dependency): f = empty, h = g
    - Stateful domains (stockflow, control, SCN): f non-empty, h = f . g
    """

    def test_stockflow_full_dynamical(self):
        """StockFlow is state-dominant: |X|=|stocks|, |f|=|stocks|."""
        from stockflow.dsl.compile import compile_model
        from stockflow.dsl.elements import Auxiliary, Flow, Stock
        from stockflow.dsl.model import StockFlowModel

        model = StockFlowModel(
            name="SIR",
            stocks=[
                Stock(name="S", initial=999.0),
                Stock(name="I", initial=1.0),
                Stock(name="R", initial=0.0),
            ],
            flows=[
                Flow(name="Infection", source="S", target="I"),
                Flow(name="Recovery", source="I", target="R"),
            ],
            auxiliaries=[
                Auxiliary(name="Infection Rate", inputs=["S", "I"]),
                Auxiliary(name="Recovery Rate", inputs=["I"]),
            ],
        )
        spec = compile_model(model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 3
        assert len(canon.mechanism_blocks) == 3

    def test_control_full_dynamical(self):
        """Control is full dynamical: |X|=|states|, |f|=|states|."""
        from gds_control.dsl.compile import compile_model
        from gds_control.dsl.elements import Controller, Input, Sensor, State
        from gds_control.dsl.model import ControlModel

        model = ControlModel(
            name="SISO",
            states=[State(name="x")],
            inputs=[Input(name="r")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )
        spec = compile_model(model)
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 1
        assert len(canon.mechanism_blocks) == 1

    def test_ogs_pure_policy(self):
        """OGS is pure policy: f=empty, X=empty, h=g."""
        from gds.types.interface import port
        from ogs.dsl.games import DecisionGame
        from ogs.dsl.pattern import Pattern
        from ogs.dsl.spec_bridge import compile_pattern_to_spec
        from ogs.dsl.types import Signature

        game = DecisionGame(
            name="Agent",
            signature=Signature(
                x=(port("Obs"),),
                y=(port("Act"),),
                r=(port("Pay"),),
            ),
        )
        spec = compile_pattern_to_spec(Pattern(name="Game", game=game))
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 1

    def test_dependency_stateless(self):
        """Dependency graphs are stateless: h = g."""
        from gds_software.dependency.elements import Dep, Module
        from gds_software.dependency.model import DependencyModel

        model = DependencyModel(
            name="Dep",
            modules=[Module(name="core", layer=0), Module(name="api", layer=1)],
            deps=[Dep(source="api", target="core")],
        )
        spec = model.compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0

    def test_cld_stateless(self):
        """CLD is stateless signal relay: h = g."""
        from gds_business.cld.elements import CausalLink, Variable
        from gds_business.cld.model import CausalLoopModel

        model = CausalLoopModel(
            name="CLD",
            variables=[Variable(name="X"), Variable(name="Y")],
            links=[CausalLink(source="X", target="Y", polarity="+")],
        )
        spec = model.compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0


# ════════════════════════════════════════════════════════════════
# Error Condition Tests
# ════════════════════════════════════════════════════════════════


class TestStockFlowErrorConditions:
    """StockFlow models that trigger specific domain check failures."""

    def test_orphan_stock_warning(self):
        """SF-001: Stock with no flows triggers warning."""
        from stockflow.dsl.elements import Stock
        from stockflow.dsl.model import StockFlowModel
        from stockflow.verification.engine import verify

        model = StockFlowModel(name="Orphan", stocks=[Stock(name="Lonely")])
        report = verify(model, include_gds_checks=False)
        sf001 = [f for f in report.findings if f.check_id == "SF-001" and not f.passed]
        assert len(sf001) == 1
        assert "Lonely" in sf001[0].message

    def test_invalid_flow_target_rejected(self):
        """Flow referencing non-existent stock fails at construction time."""
        from stockflow.dsl.elements import Flow, Stock
        from stockflow.dsl.errors import SFValidationError
        from stockflow.dsl.model import StockFlowModel

        with pytest.raises(SFValidationError):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="A")],
                flows=[Flow(name="F", target="NonExistent")],
            )

    def test_auxiliary_cycle_detected(self):
        """SF-003: Cycles in auxiliary dependency graph trigger error."""
        from stockflow.dsl.elements import Auxiliary, Flow, Stock
        from stockflow.dsl.model import StockFlowModel
        from stockflow.verification.engine import verify

        model = StockFlowModel(
            name="Cycle",
            stocks=[Stock(name="S")],
            flows=[Flow(name="F", target="S")],
            auxiliaries=[
                Auxiliary(name="A", inputs=["B"]),
                Auxiliary(name="B", inputs=["A"]),
            ],
        )
        report = verify(model, include_gds_checks=False)
        sf003 = [f for f in report.findings if f.check_id == "SF-003" and not f.passed]
        assert len(sf003) > 0


class TestControlErrorConditions:
    """Control models that trigger specific domain check failures."""

    def test_undriven_state_warning(self):
        """CS-001: State not driven by any controller."""
        from gds_control.dsl.elements import Sensor, State
        from gds_control.dsl.model import ControlModel
        from gds_control.verification.engine import verify

        model = ControlModel(
            name="Undriven",
            states=[State(name="x")],
            sensors=[Sensor(name="y", observes=["x"])],
        )
        report = verify(model, include_gds_checks=False)
        cs001 = [f for f in report.findings if f.check_id == "CS-001" and not f.passed]
        assert len(cs001) == 1

    def test_unobserved_state_warning(self):
        """CS-002: State not observed by any sensor."""
        from gds_control.dsl.elements import Controller, State
        from gds_control.dsl.model import ControlModel
        from gds_control.verification.engine import verify

        model = ControlModel(
            name="Unobserved",
            states=[State(name="x")],
            controllers=[Controller(name="K", reads=[], drives=["x"])],
        )
        report = verify(model, include_gds_checks=False)
        cs002 = [f for f in report.findings if f.check_id == "CS-002" and not f.passed]
        assert len(cs002) == 1

    def test_invalid_sensor_observes_rejected(self):
        """Sensor observing non-existent state fails at construction."""
        from gds_control.dsl.elements import Sensor, State
        from gds_control.dsl.errors import CSValidationError
        from gds_control.dsl.model import ControlModel

        with pytest.raises(CSValidationError):
            ControlModel(
                name="Bad",
                states=[State(name="x")],
                sensors=[Sensor(name="y", observes=["nonexistent"])],
            )


class TestBusinessErrorConditions:
    """Business models that trigger specific domain check failures."""

    def test_cld_self_loop_rejected_at_construction(self):
        """Self-loops are rejected by model_validator at construction time."""
        from gds_business.cld.elements import CausalLink, Variable
        from gds_business.cld.model import CausalLoopModel

        with pytest.raises(Exception, match="Self-loop"):
            CausalLoopModel(
                name="Self Loop",
                variables=[Variable(name="X")],
                links=[CausalLink(source="X", target="X", polarity="+")],
            )

    def test_cld_unreachable_variable(self):
        """CLD-002: Variable not reachable from any other variable."""
        from gds_business.cld.elements import CausalLink, Variable
        from gds_business.cld.model import CausalLoopModel
        from gds_business.verification.engine import verify

        model = CausalLoopModel(
            name="Disconnected",
            variables=[
                Variable(name="A"),
                Variable(name="B"),
                Variable(name="C"),
            ],
            links=[CausalLink(source="A", target="B", polarity="+")],
        )
        report = verify(model, include_gds_checks=False)
        cld002 = [
            f for f in report.findings if f.check_id == "CLD-002" and not f.passed
        ]
        assert len(cld002) > 0


# ════════════════════════════════════════════════════════════════
# GDS Generic Checks Across DSLs
# ════════════════════════════════════════════════════════════════


class TestGDSGenericChecks:
    """Verify GDS G-001..G-006 run on compiled SystemIR from each DSL.

    G-002 (signature completeness) flags BoundaryAction blocks as having
    no inputs — this is expected since they are exogenous sources.
    """

    def test_stockflow_gds_checks(self):
        from stockflow.dsl.elements import Flow, Stock
        from stockflow.dsl.model import StockFlowModel
        from stockflow.verification.engine import verify

        model = StockFlowModel(
            name="SF",
            stocks=[Stock(name="S")],
            flows=[Flow(name="F", target="S")],
        )
        report = verify(model, include_gds_checks=True)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0

    def test_control_gds_checks(self):
        from gds_control.dsl.elements import Controller, Input, Sensor, State
        from gds_control.dsl.model import ControlModel
        from gds_control.verification.engine import verify

        model = ControlModel(
            name="CS",
            states=[State(name="x")],
            inputs=[Input(name="r")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )
        report = verify(model, include_gds_checks=True)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0

    def test_software_gds_checks(self):
        from gds_software.dfd.elements import DataFlow, ExternalEntity, Process
        from gds_software.dfd.model import DFDModel
        from gds_software.verification.engine import verify

        model = DFDModel(
            name="DFD",
            external_entities=[ExternalEntity(name="User")],
            processes=[Process(name="Auth")],
            data_flows=[DataFlow(name="Login", source="User", target="Auth")],
        )
        report = verify(model)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0

    def test_business_gds_checks(self):
        from gds_business.cld.elements import CausalLink, Variable
        from gds_business.cld.model import CausalLoopModel
        from gds_business.verification.engine import verify

        # Bidirectional CLD — both variables have inputs, so G-002 should pass
        model = CausalLoopModel(
            name="CLD",
            variables=[Variable(name="A"), Variable(name="B")],
            links=[
                CausalLink(source="A", target="B", polarity="+"),
                CausalLink(source="B", target="A", polarity="-"),
            ],
        )
        report = verify(model)
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0
        failed_gds = [f for f in gds_findings if not f.passed]
        assert len(failed_gds) == 0

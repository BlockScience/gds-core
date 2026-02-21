"""Canonical structure stress tests.

Not testing compiler correctness. Testing this claim:

    CanonicalGDS meaningfully captures the semantic essence of
    StockFlow-generated GDSSpecs under real modeling pressure.

Does h = f ∘ g remain interpretable and structurally honest?

Three categories:
  1. Structural edge cases — coupling, aggregation, mixing
  2. Semantic edge cases — minimal models, constraint visibility
  3. Scale — does the decomposition stay clean at realistic size?
"""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import CanonicalGDS, project_canonical

from stockflow.dsl.compile import compile_model
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel


def _canonical(model: StockFlowModel) -> CanonicalGDS:
    """Shorthand: model → spec → canonical."""
    return project_canonical(compile_model(model))


# ═══════════════════════════════════════════════════════════════
# 1. Structural Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestMultiStockMutualFeedback:
    """Two stocks where auxiliaries read BOTH stock levels.

    Predator-prey with cross-coupling: every auxiliary depends on
    every stock. Tests whether canonical decomposition produces a
    coherent state vector and clear dependency structure.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Coupled Stocks",
            stocks=[
                Stock(name="A", initial=100.0),
                Stock(name="B", initial=50.0),
            ],
            flows=[
                Flow(name="A Inflow", target="A"),
                Flow(name="A Outflow", source="A"),
                Flow(name="B Inflow", target="B"),
                Flow(name="B Outflow", source="B"),
            ],
            auxiliaries=[
                # Every aux reads BOTH stocks — full coupling
                Auxiliary(name="A Growth Rate", inputs=["A", "B"]),
                Auxiliary(name="A Decay Rate", inputs=["A", "B"]),
                Auxiliary(name="B Growth Rate", inputs=["A", "B"]),
                Auxiliary(name="B Decay Rate", inputs=["A", "B"]),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_state_vector_is_coherent(self, canonical):
        """X = {(A, level), (B, level)} — one entry per stock."""
        assert set(canonical.state_variables) == {("A", "level"), ("B", "level")}

    def test_no_boundary_inputs(self, canonical):
        """No converters → U is empty."""
        assert len(canonical.boundary_blocks) == 0

    def test_policy_layer_complete(self, canonical):
        """g includes all 4 auxiliaries + 4 flows = 8 policies."""
        assert len(canonical.policy_blocks) == 8

    def test_mechanism_layer_complete(self, canonical):
        """f has exactly 2 mechanisms (one per stock)."""
        assert len(canonical.mechanism_blocks) == 2

    def test_update_map_covers_all_state(self, canonical):
        """Every state variable is updated by exactly one mechanism."""
        updated_vars = set()
        for _mech_name, targets in canonical.update_map:
            for entity, var in targets:
                updated_vars.add((entity, var))
        assert updated_vars == set(canonical.state_variables)

    def test_decision_ports_cover_all_policies(self, canonical):
        """Every policy emits at least one decision port."""
        blocks_with_decisions = {block for block, _port in canonical.decision_ports}
        assert blocks_with_decisions == set(canonical.policy_blocks)


class TestManyToOneAggregation:
    """Multiple flows feeding a single stock.

    Classic accumulation: dX/dt = inflow1 + inflow2 + inflow3 - outflow.
    Tests whether canonical f properly reflects multi-source aggregation.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Reservoir",
            stocks=[Stock(name="Water", initial=1000.0)],
            flows=[
                Flow(name="Rain", target="Water"),
                Flow(name="River", target="Water"),
                Flow(name="Groundwater", target="Water"),
                Flow(name="Evaporation", source="Water"),
            ],
            auxiliaries=[
                Auxiliary(name="Rain Rate", inputs=["Water"]),
                Auxiliary(name="River Rate", inputs=["Water"]),
                Auxiliary(name="Groundwater Rate", inputs=["Water"]),
                Auxiliary(name="Evaporation Rate", inputs=["Water"]),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_single_state_variable(self, canonical):
        assert canonical.state_variables == (("Water", "level"),)

    def test_single_mechanism(self, canonical):
        """One stock → one mechanism, regardless of flow count."""
        assert len(canonical.mechanism_blocks) == 1
        assert "Water Accumulation" in canonical.mechanism_blocks

    def test_mechanism_receives_all_rates(self, model):
        """The mechanism's forward_in has 4 rate ports (one per flow)."""
        spec = compile_model(model)
        mech = spec.blocks["Water Accumulation"]
        assert isinstance(mech, Mechanism)
        assert len(mech.interface.forward_in) == 4

    def test_update_map_targets_single_variable(self, canonical):
        assert len(canonical.update_map) == 1
        mech_name, targets = canonical.update_map[0]
        assert mech_name == "Water Accumulation"
        assert targets == (("Water", "level"),)

    def test_eight_policies(self, canonical):
        """4 auxiliaries + 4 flows = 8 policies in g."""
        assert len(canonical.policy_blocks) == 8


class TestExogenousEndogenousMixing:
    """Model with both converters (BoundaryAction) and auxiliaries (Policy).

    Tests whether canonical decomposition cleanly separates U from g:
    - Converters → boundary_blocks (U)
    - Auxiliaries → policy_blocks (g)
    - No leakage between the two.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Mixed Inputs",
            stocks=[Stock(name="Population", initial=1000.0)],
            flows=[
                Flow(name="Births", target="Population"),
                Flow(name="Deaths", source="Population"),
            ],
            auxiliaries=[
                # Reads both exogenous (converter) and endogenous (stock)
                Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
                Auxiliary(name="Death Rate", inputs=["Population", "Healthcare"]),
            ],
            converters=[
                Converter(name="Fertility"),
                Converter(name="Healthcare"),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_boundary_separation(self, canonical):
        """Converters are classified as boundary (U), not policy (g)."""
        assert set(canonical.boundary_blocks) == {"Fertility", "Healthcare"}

    def test_boundary_not_in_policy(self, canonical):
        """No leakage: boundary blocks don't appear in policy list."""
        assert not set(canonical.boundary_blocks) & set(canonical.policy_blocks)

    def test_input_ports_from_boundary_only(self, canonical):
        """Input space U comes exclusively from BoundaryAction forward_out."""
        input_blocks = {block for block, _port in canonical.input_ports}
        assert input_blocks == set(canonical.boundary_blocks)

    def test_policy_reads_both_sources(self, model):
        """Auxiliary blocks have ports from both stocks and converters."""
        spec = compile_model(model)
        birth_rate = spec.blocks["Birth Rate"]
        port_names = {p.name for p in birth_rate.interface.forward_in}
        # Population Level (endogenous) + Fertility Signal (exogenous)
        assert "Population Level" in port_names
        assert "Fertility Signal" in port_names

    def test_formula_shows_parameters(self, canonical):
        """With converters registered as parameters, formula shows θ."""
        assert canonical.has_parameters
        assert "θ" in canonical.formula()

    def test_block_roles_in_spec(self, model):
        """Verify role classification at the spec level matches canonical."""
        spec = compile_model(model)
        for name, block in spec.blocks.items():
            if isinstance(block, BoundaryAction):
                assert name in {"Fertility", "Healthcare"}
            elif isinstance(block, Mechanism):
                assert name == "Population Accumulation"
            elif isinstance(block, Policy):
                assert name in {
                    "Birth Rate",
                    "Death Rate",
                    "Births",
                    "Deaths",
                }


# ═══════════════════════════════════════════════════════════════
# 2. Semantic Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestFlowWithNoAuxiliaryLayer:
    """Stock → flow → stock with no auxiliary computation.

    The simplest possible dynamics: a single flow between two stocks.
    No auxiliaries means g is just the flow policies (pure rate emitters).
    Does the canonical decomposition still produce interpretable g and f?
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Direct Transfer",
            stocks=[
                Stock(name="Source", initial=100.0),
                Stock(name="Sink", initial=0.0),
            ],
            flows=[
                Flow(name="Transfer", source="Source", target="Sink"),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_state_vector(self, canonical):
        assert set(canonical.state_variables) == {
            ("Source", "level"),
            ("Sink", "level"),
        }

    def test_g_is_flow_only(self, canonical):
        """With no auxiliaries, g consists only of the flow policy."""
        assert set(canonical.policy_blocks) == {"Transfer"}

    def test_f_has_two_mechanisms(self, canonical):
        """Both stocks get a mechanism even with a single flow."""
        assert len(canonical.mechanism_blocks) == 2

    def test_decision_ports_minimal(self, canonical):
        """Single flow → single decision port."""
        assert len(canonical.decision_ports) == 1
        block, port = canonical.decision_ports[0]
        assert block == "Transfer"
        assert "Rate" in port

    def test_no_boundary(self, canonical):
        assert len(canonical.boundary_blocks) == 0

    def test_no_parameters(self, canonical):
        assert not canonical.has_parameters
        assert "θ" not in canonical.formula()


class TestNonNegativeConstraintVisibility:
    """CanonicalGDS is purely algebraic — constraints are NOT visible.

    This is not a bug: canonical form captures WHAT the system IS
    (state, decisions, updates), not HOW it's constrained. Constraints
    live in TypeDef at the spec level. This test documents that boundary.
    """

    @pytest.fixture
    def constrained_model(self):
        return StockFlowModel(
            name="Constrained",
            stocks=[Stock(name="S", initial=10.0, non_negative=True)],
            flows=[Flow(name="F", source="S")],
            auxiliaries=[Auxiliary(name="Rate", inputs=["S"])],
        )

    @pytest.fixture
    def unconstrained_model(self):
        return StockFlowModel(
            name="Unconstrained",
            stocks=[Stock(name="S", initial=10.0, non_negative=False)],
            flows=[Flow(name="F", source="S")],
            auxiliaries=[Auxiliary(name="Rate", inputs=["S"])],
        )

    def test_canonical_identical(self, constrained_model, unconstrained_model):
        """Canonical decomposition is identical regardless of non_negative."""
        c1 = _canonical(constrained_model)
        c2 = _canonical(unconstrained_model)

        assert c1.state_variables == c2.state_variables
        assert c1.boundary_blocks == c2.boundary_blocks
        assert c1.policy_blocks == c2.policy_blocks
        assert c1.mechanism_blocks == c2.mechanism_blocks
        assert c1.update_map == c2.update_map

    def test_constraint_lives_in_spec_types(
        self, constrained_model, unconstrained_model
    ):
        """The constraint difference is visible at spec level, not canonical."""
        spec_c = compile_model(constrained_model)
        spec_u = compile_model(unconstrained_model)

        # Spec-level: different types registered
        assert "Level" in spec_c.types  # non-negative
        assert "UnconstrainedLevel" in spec_u.types

        # Entity variables use different typedefs
        c_typedef = spec_c.entities["S"].variables["level"].typedef
        u_typedef = spec_u.entities["S"].variables["level"].typedef
        assert c_typedef.name == "Level"
        assert u_typedef.name == "UnconstrainedLevel"

        # But canonical sees the same (entity, variable) pair either way
        can_c = project_canonical(spec_c)
        can_u = project_canonical(spec_u)
        assert can_c.state_variables == can_u.state_variables


class TestOrphanStockCanonical:
    """A stock with no flows — the minimal valid model.

    The mechanism still exists (for the stock accumulator), but g is empty.
    This is the degenerate case: h = f ∘ g where g is trivial.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(name="Static", stocks=[Stock(name="X", initial=42.0)])

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_state_exists(self, canonical):
        assert canonical.state_variables == (("X", "level"),)

    def test_g_is_empty(self, canonical):
        """No policies, no decisions — g is identity-like."""
        assert len(canonical.policy_blocks) == 0
        assert len(canonical.decision_ports) == 0

    def test_f_still_exists(self, canonical):
        """Mechanism exists even without flows — it's the stock's accumulator."""
        assert len(canonical.mechanism_blocks) == 1

    def test_formula_is_simple(self, canonical):
        assert canonical.formula() == "h : X → X  (h = f ∘ g)"


# ═══════════════════════════════════════════════════════════════
# 3. Scale — realistic model size
# ═══════════════════════════════════════════════════════════════


class TestLargeModel:
    """Supply chain: 5 stocks, 8 flows, 6 auxiliaries, 3 converters.

    Raw Materials → WIP → Finished Goods → In Transit → Delivered.
    Tests that canonical decomposition stays clean at realistic scale.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Supply Chain",
            stocks=[
                Stock(name="Raw Materials", initial=500.0),
                Stock(name="WIP", initial=100.0),
                Stock(name="Finished Goods", initial=200.0),
                Stock(name="In Transit", initial=50.0),
                Stock(name="Delivered", initial=0.0),
            ],
            flows=[
                # Forward pipeline
                Flow(name="Procurement", target="Raw Materials"),
                Flow(name="Production Start", source="Raw Materials", target="WIP"),
                Flow(name="Production End", source="WIP", target="Finished Goods"),
                Flow(name="Shipment", source="Finished Goods", target="In Transit"),
                Flow(name="Delivery", source="In Transit", target="Delivered"),
                # Waste/losses
                Flow(name="Scrap", source="WIP"),
                Flow(name="Spoilage", source="Finished Goods"),
                Flow(name="Returns", target="Raw Materials"),
            ],
            auxiliaries=[
                Auxiliary(
                    name="Order Rate",
                    inputs=["Finished Goods", "Demand Forecast"],
                ),
                Auxiliary(
                    name="Production Rate",
                    inputs=["Raw Materials", "WIP", "Capacity"],
                ),
                Auxiliary(name="Scrap Rate", inputs=["WIP"]),
                Auxiliary(name="Spoilage Rate", inputs=["Finished Goods"]),
                Auxiliary(
                    name="Shipping Rate", inputs=["Finished Goods", "In Transit"]
                ),
                Auxiliary(name="Delivery Rate", inputs=["In Transit"]),
            ],
            converters=[
                Converter(name="Demand Forecast"),
                Converter(name="Capacity"),
                Converter(name="Return Rate"),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_state_vector_size(self, canonical):
        """X has 5 entries — one per stock."""
        assert len(canonical.state_variables) == 5

    def test_state_variable_names(self, canonical):
        expected = {
            ("Raw Materials", "level"),
            ("WIP", "level"),
            ("Finished Goods", "level"),
            ("In Transit", "level"),
            ("Delivered", "level"),
        }
        assert set(canonical.state_variables) == expected

    def test_boundary_blocks(self, canonical):
        """3 converters → 3 boundary blocks."""
        assert set(canonical.boundary_blocks) == {
            "Demand Forecast",
            "Capacity",
            "Return Rate",
        }

    def test_policy_count(self, canonical):
        """6 auxiliaries + 8 flows = 14 policies."""
        assert len(canonical.policy_blocks) == 14

    def test_mechanism_count(self, canonical):
        """5 stocks → 5 mechanisms."""
        assert len(canonical.mechanism_blocks) == 5

    def test_update_map_complete(self, canonical):
        """Every state variable has exactly one updating mechanism."""
        updated = set()
        for _mech, targets in canonical.update_map:
            for pair in targets:
                updated.add(pair)
        assert updated == set(canonical.state_variables)

    def test_no_duplicate_update_targets(self, canonical):
        """No state variable is updated by more than one mechanism."""
        all_targets = []
        for _mech, targets in canonical.update_map:
            all_targets.extend(targets)
        assert len(all_targets) == len(set(all_targets))

    def test_decision_port_count(self, canonical):
        """Each policy emits exactly one decision port → 14 total."""
        assert len(canonical.decision_ports) == 14

    def test_parameters_from_converters(self, canonical):
        """3 converters → 3 parameters in Θ."""
        assert canonical.has_parameters
        assert len(canonical.parameter_schema) == 3

    def test_role_partition_is_exhaustive(self, canonical, model):
        """Every block in the spec is classified into exactly one role."""
        spec = compile_model(model)
        all_canonical = (
            set(canonical.boundary_blocks)
            | set(canonical.policy_blocks)
            | set(canonical.mechanism_blocks)
        )
        assert all_canonical == set(spec.blocks.keys())

    def test_inter_stock_flows_share_mechanisms(self, model):
        """Production Start sources Raw Materials and targets WIP.

        Both mechanisms should have the same rate port.
        """
        spec = compile_model(model)
        rm_mech = spec.blocks["Raw Materials Accumulation"]
        wip_mech = spec.blocks["WIP Accumulation"]

        rm_ports = {p.name for p in rm_mech.interface.forward_in}
        wip_ports = {p.name for p in wip_mech.interface.forward_in}

        # "Production Start Rate" should appear in both
        assert "Production Start Rate" in rm_ports
        assert "Production Start Rate" in wip_ports


# ═══════════════════════════════════════════════════════════════
# 4. Structural Invariants (must hold for ALL models)
# ═══════════════════════════════════════════════════════════════


class TestCanonicalInvariants:
    """Properties that must hold for any well-formed StockFlow model.

    These are not model-specific — they test the decomposition contract.
    """

    MODELS = [
        # Minimal
        StockFlowModel(name="M1", stocks=[Stock(name="X", initial=1.0)]),
        # Simple
        StockFlowModel(
            name="M2",
            stocks=[Stock(name="X", initial=1.0)],
            flows=[Flow(name="F", target="X")],
        ),
        # With auxiliary
        StockFlowModel(
            name="M3",
            stocks=[Stock(name="X", initial=1.0)],
            flows=[Flow(name="F", target="X")],
            auxiliaries=[Auxiliary(name="A", inputs=["X"])],
        ),
        # With converter
        StockFlowModel(
            name="M4",
            stocks=[Stock(name="X", initial=1.0)],
            flows=[Flow(name="F", target="X")],
            auxiliaries=[Auxiliary(name="A", inputs=["X", "C"])],
            converters=[Converter(name="C")],
        ),
        # Multi-stock
        StockFlowModel(
            name="M5",
            stocks=[
                Stock(name="X", initial=1.0),
                Stock(name="Y", initial=2.0),
            ],
            flows=[Flow(name="F", source="X", target="Y")],
        ),
    ]

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_state_variables_equal_stocks(self, model):
        """len(X) == len(stocks), always."""
        c = _canonical(model)
        assert len(c.state_variables) == len(model.stocks)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_mechanisms_equal_stocks(self, model):
        """One mechanism per stock, always."""
        c = _canonical(model)
        assert len(c.mechanism_blocks) == len(model.stocks)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_boundary_blocks_equal_converters(self, model):
        """Converters → BoundaryActions, one-to-one."""
        c = _canonical(model)
        assert len(c.boundary_blocks) == len(model.converters)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_policies_equal_aux_plus_flows(self, model):
        """Policies = auxiliaries + flows."""
        c = _canonical(model)
        assert len(c.policy_blocks) == len(model.auxiliaries) + len(model.flows)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_update_map_covers_state(self, model):
        """Every state variable is targeted by the update map."""
        c = _canonical(model)
        updated = set()
        for _mech, targets in c.update_map:
            for pair in targets:
                updated.add(pair)
        assert updated == set(c.state_variables)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_role_partition_complete(self, model):
        """boundary ∪ policy ∪ mechanism = all blocks (no gaps, no overlaps)."""
        c = _canonical(model)
        spec = compile_model(model)
        classified = (
            set(c.boundary_blocks) | set(c.policy_blocks) | set(c.mechanism_blocks)
        )
        assert classified == set(spec.blocks.keys())

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_no_control_actions(self, model):
        """StockFlow never produces ControlAction blocks."""
        c = _canonical(model)
        assert len(c.control_blocks) == 0

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_role_partition_disjoint(self, model):
        """boundary ∩ policy ∩ mechanism = ∅ — no block in two roles."""
        c = _canonical(model)
        b = set(c.boundary_blocks)
        p = set(c.policy_blocks)
        m = set(c.mechanism_blocks)
        assert not (b & p), f"boundary ∩ policy: {b & p}"
        assert not (b & m), f"boundary ∩ mechanism: {b & m}"
        assert not (p & m), f"policy ∩ mechanism: {p & m}"

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_no_state_leaks_into_policy(self, model):
        """No stock-generated block appears in policy_blocks."""
        c = _canonical(model)
        stock_accumulators = {f"{s.name} Accumulation" for s in model.stocks}
        assert not stock_accumulators & set(c.policy_blocks)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_no_stock_in_boundary(self, model):
        """No stock accidentally classified as boundary."""
        c = _canonical(model)
        stock_names = {s.name for s in model.stocks}
        stock_accumulators = {f"{s.name} Accumulation" for s in model.stocks}
        assert not stock_names & set(c.boundary_blocks)
        assert not stock_accumulators & set(c.boundary_blocks)

    @pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
    def test_decision_port_count_equals_policies(self, model):
        """Each policy emits exactly one forward_out → |D| == |g|."""
        c = _canonical(model)
        assert len(c.decision_ports) == len(c.policy_blocks)


# ═══════════════════════════════════════════════════════════════
# 5. Declaration Order Independence
# ═══════════════════════════════════════════════════════════════


class TestDeclarationOrderIndependence:
    """Canonical projection must not depend on declaration order.

    Same model, elements listed in different order.
    If canonical differs, execution order is leaking into projection.
    """

    @pytest.fixture
    def model_forward(self):
        """Stocks, flows, auxiliaries declared in natural order."""
        return StockFlowModel(
            name="Forward",
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

    @pytest.fixture
    def model_reversed(self):
        """Same model, every list reversed."""
        return StockFlowModel(
            name="Reversed",
            stocks=[
                Stock(name="Predator", initial=20.0),
                Stock(name="Prey", initial=100.0),
            ],
            flows=[
                Flow(name="Predator Deaths", source="Predator"),
                Flow(name="Predator Births", target="Predator"),
                Flow(name="Prey Deaths", source="Prey"),
                Flow(name="Prey Births", target="Prey"),
            ],
            auxiliaries=[
                Auxiliary(name="Predator Decline", inputs=["Predator"]),
                Auxiliary(name="Predator Growth", inputs=["Prey", "Predator"]),
                Auxiliary(name="Predation", inputs=["Predator", "Prey"]),
                Auxiliary(name="Prey Growth", inputs=["Prey"]),
            ],
        )

    def test_state_variables_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        assert set(c_fwd.state_variables) == set(c_rev.state_variables)

    def test_boundary_blocks_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        assert set(c_fwd.boundary_blocks) == set(c_rev.boundary_blocks)

    def test_policy_blocks_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        assert set(c_fwd.policy_blocks) == set(c_rev.policy_blocks)

    def test_mechanism_blocks_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        assert set(c_fwd.mechanism_blocks) == set(c_rev.mechanism_blocks)

    def test_decision_ports_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        assert set(c_fwd.decision_ports) == set(c_rev.decision_ports)

    def test_update_map_identical(self, model_forward, model_reversed):
        c_fwd = _canonical(model_forward)
        c_rev = _canonical(model_reversed)
        fwd_map = {n: t for n, t in c_fwd.update_map}
        rev_map = {n: t for n, t in c_rev.update_map}
        assert fwd_map == rev_map


# ═══════════════════════════════════════════════════════════════
# 6. Coupling Fidelity
# ═══════════════════════════════════════════════════════════════


class TestCouplingFidelity:
    """Cross-stock dependencies must be preserved in g, not invented in f.

    A flow drains from Stock A into Stock B. An auxiliary reads both.
    Canonical must show:
    - Both stocks in X
    - The auxiliary's ports reflect both dependencies
    - Each mechanism updates only its own stock
    - No cross-stock contamination in the update map
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Coupled Transfer",
            stocks=[
                Stock(name="Tank A", initial=100.0),
                Stock(name="Tank B", initial=0.0),
            ],
            flows=[
                Flow(name="Transfer", source="Tank A", target="Tank B"),
            ],
            auxiliaries=[
                # Reads BOTH stocks — coupling is in g, not f
                Auxiliary(name="Transfer Rate", inputs=["Tank A", "Tank B"]),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_both_stocks_in_state(self, canonical):
        assert set(canonical.state_variables) == {
            ("Tank A", "level"),
            ("Tank B", "level"),
        }

    def test_coupling_is_in_g_not_f(self, model):
        """The auxiliary (g) reads both stocks. The mechanisms (f) don't cross."""
        spec = compile_model(model)

        # g: Transfer Rate auxiliary reads both tank levels
        aux = spec.blocks["Transfer Rate"]
        aux_ports = {p.name for p in aux.interface.forward_in}
        assert "Tank A Level" in aux_ports
        assert "Tank B Level" in aux_ports

        # f: each mechanism updates only its own stock
        mech_a = spec.blocks["Tank A Accumulation"]
        mech_b = spec.blocks["Tank B Accumulation"]
        assert mech_a.updates == [("Tank A", "level")]
        assert mech_b.updates == [("Tank B", "level")]

    def test_update_map_no_cross_contamination(self, canonical):
        """Each mechanism targets exactly one stock — no leakage."""
        for mech_name, targets in canonical.update_map:
            assert len(targets) == 1, (
                f"Mechanism {mech_name!r} updates {len(targets)} variables"
            )
            entity, _var = targets[0]
            # Mechanism name embeds the stock name it owns
            assert entity in mech_name

    def test_shared_flow_appears_in_both_mechanisms(self, model):
        """Transfer Rate port appears in both mechanisms' forward_in."""
        spec = compile_model(model)
        a_ports = {
            p.name for p in spec.blocks["Tank A Accumulation"].interface.forward_in
        }
        b_ports = {
            p.name for p in spec.blocks["Tank B Accumulation"].interface.forward_in
        }
        assert "Transfer Rate" in a_ports
        assert "Transfer Rate" in b_ports


# ═══════════════════════════════════════════════════════════════
# 7. Over-Collapsing Detection
# ═══════════════════════════════════════════════════════════════


class TestOverCollapsing:
    """Canonical projection must not merge distinct policies or lose
    intermediate structure.

    Model: two stocks, one flow draining from both, two auxiliaries
    depending on different stocks, one converter influencing only one
    branch. Tests whether canonical preserves branching.
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Branching",
            stocks=[
                Stock(name="Hot", initial=80.0),
                Stock(name="Cold", initial=20.0),
            ],
            flows=[
                Flow(name="Heat Loss", source="Hot"),
                Flow(name="Heat Gain", target="Cold"),
                Flow(name="Exchange", source="Hot", target="Cold"),
            ],
            auxiliaries=[
                # Branch A: reads Hot only
                Auxiliary(name="Radiation", inputs=["Hot"]),
                # Branch B: reads Cold only
                Auxiliary(name="Absorption", inputs=["Cold", "Ambient"]),
                # Cross-branch: reads both
                Auxiliary(name="Gradient", inputs=["Hot", "Cold"]),
            ],
            converters=[
                Converter(name="Ambient"),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    def test_all_auxiliaries_are_distinct_policies(self, canonical):
        """Three auxiliaries must remain three distinct policies."""
        aux_names = {"Radiation", "Absorption", "Gradient"}
        assert aux_names <= set(canonical.policy_blocks)

    def test_flows_are_distinct_policies(self, canonical):
        """Three flows must remain three distinct policies."""
        flow_names = {"Heat Loss", "Heat Gain", "Exchange"}
        assert flow_names <= set(canonical.policy_blocks)

    def test_total_policy_count(self, canonical):
        """3 aux + 3 flows = 6 policies. No collapsing."""
        assert len(canonical.policy_blocks) == 6

    def test_decision_ports_not_collapsed(self, canonical):
        """Each policy has its own decision port — 6 total."""
        assert len(canonical.decision_ports) == 6
        blocks_with_ports = {b for b, _p in canonical.decision_ports}
        assert len(blocks_with_ports) == 6

    def test_boundary_is_minimal(self, canonical):
        """Only the converter is boundary. Not duplicated."""
        assert set(canonical.boundary_blocks) == {"Ambient"}
        assert len(canonical.input_ports) == 1

    def test_converter_not_duplicated_in_ports(self, canonical):
        """One converter → one input port. No inflation."""
        input_blocks = [b for b, _p in canonical.input_ports]
        assert input_blocks == ["Ambient"]

    def test_asymmetric_dependency_preserved(self, model):
        """Radiation reads only Hot; Absorption reads Cold + Ambient.

        These are structurally different — canonical must not merge them.
        """
        spec = compile_model(model)

        rad_ports = {p.name for p in spec.blocks["Radiation"].interface.forward_in}
        abs_ports = {p.name for p in spec.blocks["Absorption"].interface.forward_in}

        assert rad_ports == {"Hot Level"}
        assert abs_ports == {"Cold Level", "Ambient Signal"}
        assert rad_ports != abs_ports  # structurally distinct


# ═══════════════════════════════════════════════════════════════
# 8. Complex Model — Semantic Pressure
# ═══════════════════════════════════════════════════════════════


class TestComplexPredatorPreyHarvesting:
    """Predator-prey + harvesting + seasonal forcing.

    2 stocks, 5 flows, 5 auxiliaries, 2 converters.
    This model has everything: coupling, exogenous input, multi-flow
    aggregation, and asymmetric dependency structure.

    The question: does canonical still feel minimal and natural,
    or do compression artifacts appear?
    """

    @pytest.fixture
    def model(self):
        return StockFlowModel(
            name="Ecosystem Management",
            stocks=[
                Stock(name="Prey", initial=500.0),
                Stock(name="Predator", initial=50.0),
            ],
            flows=[
                Flow(name="Prey Reproduction", target="Prey"),
                Flow(name="Predation Loss", source="Prey"),
                Flow(name="Harvest", source="Prey"),
                Flow(name="Predator Reproduction", target="Predator"),
                Flow(name="Predator Starvation", source="Predator"),
            ],
            auxiliaries=[
                # Endogenous: prey growth depends on prey density
                Auxiliary(name="Prey Growth Rate", inputs=["Prey"]),
                # Coupling: predation depends on both populations
                Auxiliary(name="Predation Rate", inputs=["Prey", "Predator"]),
                # Exogenous: harvest depends on prey + seasonal quota
                Auxiliary(
                    name="Harvest Rate",
                    inputs=["Prey", "Season"],
                ),
                # Coupling: predator growth depends on prey availability
                Auxiliary(
                    name="Predator Growth Rate",
                    inputs=["Predator", "Prey"],
                ),
                # Endogenous: starvation depends on predator density + carrying capacity
                Auxiliary(
                    name="Starvation Rate",
                    inputs=["Predator", "Carrying Capacity"],
                ),
            ],
            converters=[
                Converter(name="Season"),
                Converter(name="Carrying Capacity"),
            ],
        )

    @pytest.fixture
    def canonical(self, model):
        return _canonical(model)

    @pytest.fixture
    def spec(self, model):
        return compile_model(model)

    # ── State integrity ──

    def test_state_vector(self, canonical):
        assert set(canonical.state_variables) == {
            ("Prey", "level"),
            ("Predator", "level"),
        }

    # ── Boundary integrity ──

    def test_boundary_is_exogenous_only(self, canonical):
        """Season and Carrying Capacity are the only exogenous inputs."""
        assert set(canonical.boundary_blocks) == {"Season", "Carrying Capacity"}

    def test_boundary_not_in_g_or_f(self, canonical):
        """Clean partition: U ∩ (g ∪ f) = ∅."""
        boundary = set(canonical.boundary_blocks)
        assert not boundary & set(canonical.policy_blocks)
        assert not boundary & set(canonical.mechanism_blocks)

    # ── Policy integrity — no over-collapsing ──

    def test_policy_count(self, canonical):
        """5 aux + 5 flows = 10 distinct policies."""
        assert len(canonical.policy_blocks) == 10

    def test_all_auxiliaries_preserved(self, canonical):
        expected = {
            "Prey Growth Rate",
            "Predation Rate",
            "Harvest Rate",
            "Predator Growth Rate",
            "Starvation Rate",
        }
        assert expected <= set(canonical.policy_blocks)

    def test_all_flows_preserved(self, canonical):
        expected = {
            "Prey Reproduction",
            "Predation Loss",
            "Harvest",
            "Predator Reproduction",
            "Predator Starvation",
        }
        assert expected <= set(canonical.policy_blocks)

    # ── Mechanism integrity ──

    def test_mechanism_count(self, canonical):
        assert len(canonical.mechanism_blocks) == 2

    def test_prey_mechanism_aggregates_three_flows(self, spec):
        """Prey Accumulation receives: Prey Reproduction, Predation Loss, Harvest."""
        mech = spec.blocks["Prey Accumulation"]
        ports = {p.name for p in mech.interface.forward_in}
        assert ports == {
            "Prey Reproduction Rate",
            "Predation Loss Rate",
            "Harvest Rate",
        }

    def test_predator_mechanism_aggregates_two_flows(self, spec):
        """Predator Accumulation receives: Predator Reproduction, Predator Starvation."""
        mech = spec.blocks["Predator Accumulation"]
        ports = {p.name for p in mech.interface.forward_in}
        assert ports == {
            "Predator Reproduction Rate",
            "Predator Starvation Rate",
        }

    def test_update_map_no_cross_stock(self, canonical):
        """Each mechanism updates only its own stock."""
        update_dict = {name: targets for name, targets in canonical.update_map}
        assert update_dict["Prey Accumulation"] == (("Prey", "level"),)
        assert update_dict["Predator Accumulation"] == (("Predator", "level"),)

    # ── Coupling fidelity ──

    def test_predation_rate_reads_both_stocks(self, spec):
        """Cross-coupling in g: Predation Rate depends on Prey AND Predator."""
        aux = spec.blocks["Predation Rate"]
        ports = {p.name for p in aux.interface.forward_in}
        assert "Prey Level" in ports
        assert "Predator Level" in ports

    def test_harvest_rate_reads_stock_and_boundary(self, spec):
        """Mixed dependency: Harvest Rate depends on Prey (endogenous)
        and Season (exogenous)."""
        aux = spec.blocks["Harvest Rate"]
        ports = {p.name for p in aux.interface.forward_in}
        assert "Prey Level" in ports
        assert "Season Signal" in ports

    def test_starvation_reads_stock_and_boundary(self, spec):
        """Starvation Rate depends on Predator (endogenous)
        and Carrying Capacity (exogenous)."""
        aux = spec.blocks["Starvation Rate"]
        ports = {p.name for p in aux.interface.forward_in}
        assert "Predator Level" in ports
        assert "Carrying Capacity Signal" in ports

    # ── Parameters ──

    def test_parameter_schema(self, canonical):
        assert canonical.has_parameters
        assert canonical.parameter_schema.names() == {
            "Season",
            "Carrying Capacity",
        }

    # ── The meta-question: is this still minimal? ──

    def test_canonical_is_minimal(self, canonical):
        """Verify the decomposition has no redundancy.

        Minimal means:
        - |X| = number of stocks (2)
        - |U| = number of exogenous inputs (2)
        - |g| = number of decision-making blocks (10)
        - |f| = number of state-updating blocks (2)
        - |D| = number of decision outputs (10)
        - Every state variable updated exactly once
        - No unclassified blocks
        """
        assert len(canonical.state_variables) == 2
        assert len(canonical.boundary_blocks) == 2
        assert len(canonical.policy_blocks) == 10
        assert len(canonical.mechanism_blocks) == 2
        assert len(canonical.decision_ports) == 10
        assert len(canonical.control_blocks) == 0

        # No redundancy in update map
        updated = set()
        for _mech, targets in canonical.update_map:
            for pair in targets:
                assert pair not in updated, f"Duplicate update: {pair}"
                updated.add(pair)
        assert updated == set(canonical.state_variables)

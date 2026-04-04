"""Gordon-Schaefer Bioeconomic Fishery — all four roles, all four operators.

The first GDS example to combine every composition operator (>>, |,
.feedback(), .loop()) with all four block roles (BoundaryAction, Policy,
ControlAction, Mechanism).  Models a fish population with logistic growth,
harvest by a profit-driven fishing fleet, and a quota system that constrains
the allowable catch within each timestep.

Concepts Covered:
    - All 4 block roles: BoundaryAction, Policy, ControlAction, Mechanism
    - All 4 composition operators: >>, |, .feedback(), .loop()
    - ControlAction with backward_out for within-timestep quota feedback
    - Policy with backward_in receiving CONTRAVARIANT feedback
    - Mechanisms with forward_out enabling cross-timestep temporal loops
    - Multi-entity state (Fish Stock + Fleet)
    - Rich parameter space Θ (6 parameters)

Prerequisites: sir_epidemic (roles, >>), thermostat (.feedback(), ControlAction),
               lotka_volterra (.loop(), temporal COVARIANT)

GDS Decomposition:
    X  = (Fish Stock.biomass, Fleet.effort)
    U  = (Observe Stock, Observe Effort, Environmental Conditions, Market Price)
    g  = (Compute Growth, Compute Harvest Pressure, Compute Profit)
    d  = (Enforce Quota)
    f  = (Update Fish Stock, Update Fleet)
    Θ  = {intrinsic_growth_rate, base_carrying_capacity,
           catchability_coefficient, cost_per_unit_effort,
           quota_limit, effort_adjustment_speed}

Composition:
    tier_0 = (Observe Stock | Observe Effort | Environmental Conditions
              | Market Price)
    tier_1 = (Compute Growth | Compute Harvest Pressure)
    tier_2 = Enforce Quota
    tier_3 = Compute Profit
    tier_4 = (Update Fish Stock | Update Fleet)

    pipeline = tier_0 >> tier_1 >> tier_2 >> tier_3 >> tier_4
    system = pipeline
        .feedback([Enforce Quota → Compute Harvest Pressure]  CONTRAVARIANT)
        .loop([Update Fish Stock → Compute Growth,
               Update Fish Stock → Compute Harvest Pressure,
               Update Fleet → Compute Harvest Pressure]  COVARIANT)
"""

from gds.blocks.composition import Wiring
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: Six distinct value types capturing the bioeconomic
# domain's quantities. Population and EffortLevel are non-negative;
# BiomassRate and Currency allow negative values (decline, loss).
# ══════════════════════════════════════════════════════════════════

# Fish biomass — continuous approximation of a discrete population.
Population = TypeDef(
    name="Population",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Non-negative fish biomass (tonnes)",
)

# Rate of change of biomass — can be negative (population decline).
BiomassRate = TypeDef(
    name="BiomassRate",
    python_type=float,
    description="Rate of biomass change (tonnes/timestep)",
)

# Fishing effort — fleet activity level, non-negative.
EffortLevel = TypeDef(
    name="EffortLevel",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Non-negative fishing effort (vessel-days)",
)

# Revenue, cost, profit — can be negative (losses).
Currency = TypeDef(
    name="Currency",
    python_type=float,
    description="Monetary value (can be negative for losses)",
)

# Environmental modifier — scales carrying capacity (0, 2].
UnitFraction = TypeDef(
    name="UnitFraction",
    python_type=float,
    constraint=lambda x: 0 < x <= 2,
    description="Environmental modifier in (0, 2]",
)

# Positive rate constants for growth/catchability/adjustment parameters.
GrowthParameter = TypeDef(
    name="GrowthParameter",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Positive rate parameter",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Two entities with one variable each. Fish Stock
# tracks biomass (N); Fleet tracks effort level (E). Together they
# form the 2-dimensional state X = (N, E).
# ══════════════════════════════════════════════════════════════════

fish_stock = Entity(
    name="Fish Stock",
    variables={
        "biomass": StateVariable(name="biomass", typedef=Population, symbol="N"),
    },
    description="Fish population biomass",
)

fleet = Entity(
    name="Fleet",
    variables={
        "effort": StateVariable(name="effort", typedef=EffortLevel, symbol="E"),
    },
    description="Fishing fleet effort level",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Nine spaces for inter-block signals. Notable:
#   - QuotaFeedbackSpace carries CONTRAVARIANT backward flow
#   - StockObservationSpace and EffortObservationSpace carry
#     COVARIANT temporal signals via .loop()
# ══════════════════════════════════════════════════════════════════

stock_observation_space = Space(
    name="StockObservationSpace",
    fields={"biomass": Population},
    description="Observed fish stock biomass",
)

effort_observation_space = Space(
    name="EffortObservationSpace",
    fields={"effort_level": EffortLevel},
    description="Observed fleet effort level",
)

environmental_space = Space(
    name="EnvironmentalSpace",
    fields={"carrying_capacity_modifier": UnitFraction},
    description="Environmental conditions affecting carrying capacity",
)

market_space = Space(
    name="MarketSpace",
    fields={"price_per_unit": Currency},
    description="Market price per unit of catch",
)

growth_rate_space = Space(
    name="GrowthRateSpace",
    fields={"growth_rate": BiomassRate},
    description="Computed logistic growth rate",
)

harvest_pressure_space = Space(
    name="HarvestPressureSpace",
    fields={"desired_harvest": BiomassRate},
    description="Desired harvest before quota enforcement",
)

regulated_harvest_space = Space(
    name="RegulatedHarvestSpace",
    fields={"actual_harvest": BiomassRate},
    description="Harvest after quota enforcement",
)

quota_feedback_space = Space(
    name="QuotaFeedbackSpace",
    fields={"quota_remaining": BiomassRate},
    description="Remaining quota fed back to harvest computation (CONTRAVARIANT)",
)

profit_space = Space(
    name="ProfitSpace",
    fields={"profit_per_effort": Currency},
    description="Profit signal driving fleet effort adjustment",
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition with all four GDS roles
# GDS Mapping:
#   BoundaryAction (4): exogenous inputs U — no forward_in
#   Policy (3):         decision functions g — forward flow only
#                       (Compute Harvest Pressure also has backward_in
#                       for quota feedback within the timestep)
#   ControlAction (1):  admissibility constraint d — Enforce Quota
#                       caps harvest and sends quota info backward
#   Mechanism (2):      state updates f — Update Fish Stock and
#                       Update Fleet, both with forward_out for .loop()
# ══════════════════════════════════════════════════════════════════

# -- BoundaryActions: exogenous inputs U ----------------------------

# Initial fish stock observation — seed for temporal loop at t=0.
observe_stock = BoundaryAction(
    name="Observe Stock",
    interface=Interface(
        forward_out=(port("Stock Observation"),),
    ),
    tags={"domain": "Ecology"},
)

# Initial fleet effort observation — seed for temporal loop at t=0.
observe_effort = BoundaryAction(
    name="Observe Effort",
    interface=Interface(
        forward_out=(port("Effort Observation"),),
    ),
    tags={"domain": "Economics"},
)

# Environmental conditions — modifies effective carrying capacity.
environmental_conditions = BoundaryAction(
    name="Environmental Conditions",
    interface=Interface(
        forward_out=(port("Environmental Signal"),),
    ),
    tags={"domain": "Ecology"},
)

# Market price — exogenous price signal for revenue computation.
market_price = BoundaryAction(
    name="Market Price",
    interface=Interface(
        forward_out=(port("Market Signal"),),
    ),
    tags={"domain": "Economics"},
)

# -- Policies: decision functions g ---------------------------------

# Logistic growth: r * N * (1 - N / (K * env_modifier))
# Reads stock observation + environmental signal, emits growth rate.
compute_growth = Policy(
    name="Compute Growth",
    interface=Interface(
        forward_in=(port("Stock Observation"), port("Environmental Signal")),
        forward_out=(port("Growth Rate"),),
    ),
    params_used=["intrinsic_growth_rate", "base_carrying_capacity"],
    tags={"domain": "Ecology"},
)

# Harvest pressure: q * E * N (Schaefer production function).
# Reads stock + effort observations. Also receives quota feedback
# via backward_in — the quota remaining informs whether to reduce
# fishing intensity within the same timestep.
compute_harvest_pressure = Policy(
    name="Compute Harvest Pressure",
    interface=Interface(
        forward_in=(port("Stock Observation"), port("Effort Observation")),
        forward_out=(port("Harvest Pressure"),),
        backward_in=(port("Quota Feedback"),),
    ),
    params_used=["catchability_coefficient"],
    tags={"domain": "Shared"},
)

# Profit: (price * actual_harvest) - (cost * effort).
# Reads regulated harvest (post-quota) and market price.
compute_profit = Policy(
    name="Compute Profit",
    interface=Interface(
        forward_in=(port("Regulated Harvest"), port("Market Signal")),
        forward_out=(port("Profit Signal"),),
    ),
    params_used=["cost_per_unit_effort"],
    tags={"domain": "Economics"},
)

# -- ControlAction: admissibility constraint d ----------------------

# Enforce Quota: caps harvest at quota_limit.
# Forward: receives desired harvest, emits regulated (capped) harvest.
# Backward: sends quota remaining back to harvest computation within
# the same timestep via backward_out (CONTRAVARIANT feedback).
enforce_quota = ControlAction(
    name="Enforce Quota",
    interface=Interface(
        forward_in=(port("Harvest Pressure"),),
        forward_out=(port("Regulated Harvest"),),
        backward_out=(port("Quota Feedback"),),
    ),
    params_used=["quota_limit"],
    tags={"domain": "Regulation"},
)

# -- Mechanisms: state update functions f ---------------------------

# Update Fish Stock: new_biomass = biomass + growth - actual_harvest.
# forward_out emits updated stock observation for .loop() — feeds
# Compute Growth and Compute Harvest Pressure at the next timestep.
update_fish_stock = Mechanism(
    name="Update Fish Stock",
    interface=Interface(
        forward_in=(port("Growth Rate"), port("Regulated Harvest")),
        forward_out=(port("Stock Observation"),),
    ),
    updates=[("Fish Stock", "biomass")],
    tags={"domain": "Ecology"},
)

# Update Fleet: effort adjusts toward profitability.
# forward_out emits updated effort observation for .loop() — feeds
# Compute Harvest Pressure at the next timestep.
update_fleet = Mechanism(
    name="Update Fleet",
    interface=Interface(
        forward_in=(port("Profit Signal"),),
        forward_out=(port("Effort Observation"),),
    ),
    updates=[("Fleet", "effort")],
    params_used=["effort_adjustment_speed"],
    tags={"domain": "Economics"},
)


def build_spec() -> GDSSpec:
    """Build the complete Gordon-Schaefer fisheries specification.

    Registers all types, spaces, entities, blocks, parameters, and
    wirings into a single GDSSpec. The wiring includes both forward
    wires and backward wires (quota feedback) — the directionality
    is determined by the block interfaces (backward_out → backward_in).
    Temporal wires (mechanism → policy) appear as regular Wire entries;
    the temporal semantics are expressed via .loop() in build_system().
    """
    spec = GDSSpec(
        name="Gordon-Schaefer Fishery",
        description=(
            "Bioeconomic fishery model with logistic growth, "
            "Schaefer harvest, quota enforcement, and effort dynamics"
        ),
    )

    # Types
    spec.register_type(Population)
    spec.register_type(BiomassRate)
    spec.register_type(EffortLevel)
    spec.register_type(Currency)
    spec.register_type(UnitFraction)
    spec.register_type(GrowthParameter)

    # Spaces
    spec.register_space(stock_observation_space)
    spec.register_space(effort_observation_space)
    spec.register_space(environmental_space)
    spec.register_space(market_space)
    spec.register_space(growth_rate_space)
    spec.register_space(harvest_pressure_space)
    spec.register_space(regulated_harvest_space)
    spec.register_space(quota_feedback_space)
    spec.register_space(profit_space)

    # Entities
    spec.register_entity(fish_stock)
    spec.register_entity(fleet)

    # Blocks
    spec.register_block(observe_stock)
    spec.register_block(observe_effort)
    spec.register_block(environmental_conditions)
    spec.register_block(market_price)
    spec.register_block(compute_growth)
    spec.register_block(compute_harvest_pressure)
    spec.register_block(enforce_quota)
    spec.register_block(compute_profit)
    spec.register_block(update_fish_stock)
    spec.register_block(update_fleet)

    # Parameters — Θ: six bioeconomic constants
    spec.register_parameter("intrinsic_growth_rate", GrowthParameter)
    spec.register_parameter("base_carrying_capacity", Population)
    spec.register_parameter("catchability_coefficient", GrowthParameter)
    spec.register_parameter("cost_per_unit_effort", Currency)
    spec.register_parameter("quota_limit", Population)
    spec.register_parameter("effort_adjustment_speed", GrowthParameter)

    # Wiring — forward, backward, and temporal connections
    spec.register_wiring(
        SpecWiring(
            name="Fishery Dynamics",
            block_names=[
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
            ],
            wires=[
                # Tier 0 → Tier 1: observations + environment to rate policies
                Wire(
                    source="Observe Stock",
                    target="Compute Growth",
                    space="StockObservationSpace",
                ),
                Wire(
                    source="Observe Stock",
                    target="Compute Harvest Pressure",
                    space="StockObservationSpace",
                ),
                Wire(
                    source="Observe Effort",
                    target="Compute Harvest Pressure",
                    space="EffortObservationSpace",
                ),
                Wire(
                    source="Environmental Conditions",
                    target="Compute Growth",
                    space="EnvironmentalSpace",
                ),
                # Tier 1 → Tier 2: harvest pressure to quota enforcement
                Wire(
                    source="Compute Harvest Pressure",
                    target="Enforce Quota",
                    space="HarvestPressureSpace",
                ),
                # Tier 2 → Tier 3: regulated harvest + market to profit
                Wire(
                    source="Enforce Quota",
                    target="Compute Profit",
                    space="RegulatedHarvestSpace",
                ),
                Wire(
                    source="Market Price",
                    target="Compute Profit",
                    space="MarketSpace",
                ),
                # Tier 2 → Tier 4: regulated harvest to fish stock update
                Wire(
                    source="Enforce Quota",
                    target="Update Fish Stock",
                    space="RegulatedHarvestSpace",
                ),
                # Tier 1 → Tier 4: growth rate to fish stock update
                Wire(
                    source="Compute Growth",
                    target="Update Fish Stock",
                    space="GrowthRateSpace",
                ),
                # Tier 3 → Tier 4: profit to fleet update
                Wire(
                    source="Compute Profit",
                    target="Update Fleet",
                    space="ProfitSpace",
                ),
                # Backward wire: quota feedback (CONTRAVARIANT)
                Wire(
                    source="Enforce Quota",
                    target="Compute Harvest Pressure",
                    space="QuotaFeedbackSpace",
                ),
                # Temporal wires: mechanisms → policies (COVARIANT via .loop())
                Wire(
                    source="Update Fish Stock",
                    target="Compute Growth",
                    space="StockObservationSpace",
                ),
                Wire(
                    source="Update Fish Stock",
                    target="Compute Harvest Pressure",
                    space="StockObservationSpace",
                ),
                Wire(
                    source="Update Fleet",
                    target="Compute Harvest Pressure",
                    space="EffortObservationSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the fishery system with feedback AND temporal loop.

    This is the first GDS example to combine .feedback() and .loop() on
    the same composition tree, demonstrating both within-timestep and
    cross-timestep information flow:

    Step-by-step composition:
      1. Parallel tiers with | (independent blocks at each level)
      2. Sequential pipeline with >> (five tiers of computation)
      3. .feedback() for within-timestep backward quota signal (CONTRAVARIANT)
      4. .loop() for cross-timestep state propagation (COVARIANT)

    Token overlap at each >> boundary (StackComposition accumulates all ports):
      tier_0 >> tier_1: {stock observation, effort observation,
                         environmental signal} overlap ✓
      (...) >> tier_2:  {harvest pressure} overlap ✓
      (...) >> tier_3:  {regulated harvest, market signal} overlap ✓
      (...) >> tier_4:  {growth rate, regulated harvest, profit signal} overlap ✓
    """
    # Step 1: Parallel composition within tiers
    tier_0 = observe_stock | observe_effort | environmental_conditions | market_price
    tier_1 = compute_growth | compute_harvest_pressure
    tier_4 = update_fish_stock | update_fleet

    # Step 2: Sequential pipeline across tiers
    pipeline = tier_0 >> tier_1 >> enforce_quota >> compute_profit >> tier_4

    # Step 3: Within-timestep feedback — quota enforcement informs harvest
    # computation via CONTRAVARIANT backward flow. The ControlAction's
    # backward_out sends the remaining quota to the Policy's backward_in.
    with_feedback = pipeline.feedback(
        [
            Wiring(
                source_block="Enforce Quota",
                source_port="Quota Feedback",
                target_block="Compute Harvest Pressure",
                target_port="Quota Feedback",
                direction=FlowDirection.CONTRAVARIANT,
            ),
        ]
    )

    # Step 4: Cross-timestep temporal loop — mechanism outputs feed back
    # to policy inputs at the NEXT timestep. Three COVARIANT wirings:
    # fish stock feeds both growth and harvest, fleet feeds harvest.
    system = with_feedback.loop(
        [
            Wiring(
                source_block="Update Fish Stock",
                source_port="Stock Observation",
                target_block="Compute Growth",
                target_port="Stock Observation",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Update Fish Stock",
                source_port="Stock Observation",
                target_block="Compute Harvest Pressure",
                target_port="Stock Observation",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Update Fleet",
                source_port="Effort Observation",
                target_block="Compute Harvest Pressure",
                target_port="Effort Observation",
                direction=FlowDirection.COVARIANT,
            ),
        ],
        exit_condition="stock_collapsed",
    )

    return compile_system(name="Gordon-Schaefer Fishery", root=system)

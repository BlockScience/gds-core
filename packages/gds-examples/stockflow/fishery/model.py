"""Gordon-Schaefer Common-Pool Resource Fishery — raw GDS model.

Variant 1 (unregulated): n symmetric fishers harvest a shared fish stock.
Each fisher chooses effort to maximize individual profit. The Nash
equilibrium depletes the stock below the socially optimal level —
the tragedy of the commons.

This model is the base layer for a multi-variant case study that
exercises the entire GDS improvement roadmap. Variant 2 (regulated)
adds a ControlAction output map and regulator. Variant 3 (disturbed)
adds environmental disturbance inputs. See fishery-case-study.md.

Concepts Covered:
    - TypeDef with domain-specific constraints (biomass, effort, catch)
    - Multi-entity state space (population + n fisher profits)
    - Temporal .loop() for population → observation feedback
    - AdmissibleInputConstraint (harvest feasibility)
    - TransitionSignature (mechanism read dependencies)
    - Analytical benchmark validation (Gordon-Schaefer closed forms)

GDS Decomposition:
    X  = (N, pi_1, ..., pi_n)   — fish biomass + per-fisher cumulative profit
    U  = (p)                     — exogenous market price
    g  = {price, observer, fishers, harvest_rate, growth_rate}
    f  = {population_dynamics, profit_1, ..., profit_n}
    Theta = {r, K, q, p, c, m}

Composition:
    (price | observer) >> (fisher_1 | ... | fisher_n)
        >> (harvest_rate | growth_rate)
        >> (population_dynamics | profit_1 | ... | profit_n)
        .loop(population_dynamics -> observer, harvest_rate, growth_rate)

Analytical Benchmarks (Gordon 1954, Schaefer 1957, Clark 1990):
    N_MSY   = K / 2
    H_MSY   = r * K / 4
    N_inf   = c / (p * q)                  (bionomic / open-access)
    N_nash  = (K + n * N_inf) / (n + 1)    (n-player Cournot)
    N_MEY   = (K + N_inf) / 2              (social optimum = sole owner)
"""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import CanonicalGDS, project_canonical
from gds.compiler.compile import compile_system
from gds.constraints import AdmissibleInputConstraint, TransitionSignature
from gds.ir.models import SystemIR
from gds.parameters import ParameterDef
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════

N_FISHERS = 3  # default number of fishers for the example

# ══════════════════════════════════════════════════════════════════
# Types — domain-specific value constraints
# ══════════════════════════════════════════════════════════════════

Biomass = TypeDef(
    name="Biomass",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Fish biomass (non-negative)",
)

Effort = TypeDef(
    name="Effort",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Fishing effort (non-negative)",
)

Catch = TypeDef(
    name="Catch",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Harvest quantity (non-negative)",
)

Profit = TypeDef(
    name="Profit",
    python_type=float,
    description="Economic rent (may be negative)",
)

Price = TypeDef(
    name="Price",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Fish market price (positive)",
)

RateParam = TypeDef(
    name="RateParam",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Positive rate parameter (r, q, m)",
)

Capacity = TypeDef(
    name="Capacity",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Carrying capacity (positive)",
)

CostParam = TypeDef(
    name="CostParam",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Cost per unit effort (positive)",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X
# ══════════════════════════════════════════════════════════════════

fish_population = Entity(
    name="Fish Population",
    variables={
        "level": StateVariable(name="level", typedef=Biomass, symbol="N"),
    },
    description="Shared fish stock biomass",
)


def _build_fisher_entity(i: int) -> Entity:
    """Build a fisher entity with cumulative profit state."""
    return Entity(
        name=f"Fisher {i}",
        variables={
            "cumulative_profit": StateVariable(
                name="cumulative_profit", typedef=Profit, symbol=f"π_{i}"
            ),
        },
        description=f"Fisher {i} — profit accumulation",
    )


def build_fisher_entities(n: int = N_FISHERS) -> list[Entity]:
    return [_build_fisher_entity(i) for i in range(1, n + 1)]


# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels
# ══════════════════════════════════════════════════════════════════

biomass_signal_space = Space(
    name="BiomassSignalSpace",
    fields={"value": Biomass},
    description="Signal carrying observed fish stock level",
)

effort_signal_space = Space(
    name="EffortSignalSpace",
    fields={"value": Effort},
    description="Signal carrying a fisher's chosen effort level",
)

catch_signal_space = Space(
    name="CatchSignalSpace",
    fields={"value": Catch},
    description="Signal carrying total harvest rate",
)

growth_signal_space = Space(
    name="GrowthSignalSpace",
    fields={"value": Biomass},
    description="Signal carrying natural growth rate",
)

price_signal_space = Space(
    name="PriceSignalSpace",
    fields={"value": Price},
    description="Signal carrying exogenous market price",
)

profit_signal_space = Space(
    name="ProfitSignalSpace",
    fields={"value": Profit},
    description="Signal carrying per-period profit",
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition
# ══════════════════════════════════════════════════════════════════

# --- BoundaryAction: exogenous market price ---

market_price = BoundaryAction(
    name="Market Price",
    interface=Interface(
        forward_out=(port("Price Signal"),),
    ),
    params_used=["p"],
    tags={"domain": "Market"},
)

# --- Policy: stock observation (temporal loop target) ---

stock_observer = Policy(
    name="Stock Observer",
    interface=Interface(
        forward_in=(port("Population Level"),),
        forward_out=(port("Observed Stock"),),
    ),
    tags={"domain": "Observation"},
)


# --- Policy: fisher decisions (one per fisher) ---


def _build_fisher_block(i: int) -> Policy:
    """Each fisher observes stock + price, chooses effort."""
    return Policy(
        name=f"Fisher {i}",
        interface=Interface(
            forward_in=(
                port("Observed Stock"),
                port("Price Signal"),
            ),
            forward_out=(port(f"Fisher {i} Effort"),),
        ),
        params_used=["q", "c"],
        tags={"domain": "Decision", "player": str(i)},
    )


def build_fisher_blocks(n: int = N_FISHERS) -> list[Policy]:
    return [_build_fisher_block(i) for i in range(1, n + 1)]


# --- Policy: harvest rate computation ---


def _build_harvest_rate_block(n: int = N_FISHERS) -> Policy:
    """Aggregates individual efforts into total harvest: H = q * (sum e_i) * N."""
    effort_ports = tuple(port(f"Fisher {i} Effort") for i in range(1, n + 1))
    return Policy(
        name="Harvest Rate",
        interface=Interface(
            forward_in=(port("Population Level"), *effort_ports),
            forward_out=(port("Total Harvest"),),
        ),
        params_used=["q"],
        tags={"domain": "Computation"},
    )


# --- Policy: growth rate computation ---

growth_rate = Policy(
    name="Growth Rate",
    interface=Interface(
        forward_in=(port("Population Level"),),
        forward_out=(port("Natural Growth"),),
    ),
    params_used=["r", "K", "m"],
    tags={"domain": "Computation"},
)

# --- Mechanism: population dynamics ---

population_dynamics = Mechanism(
    name="Population Dynamics",
    interface=Interface(
        forward_in=(
            port("Natural Growth"),
            port("Total Harvest"),
        ),
        forward_out=(port("Population Level"),),  # enables .loop()
    ),
    updates=[("Fish Population", "level")],
    tags={"domain": "State Update"},
)


# --- Mechanism: profit accumulation (one per fisher) ---


def _build_profit_mechanism(i: int) -> Mechanism:
    """pi_i' = pi_i + p * q * e_i * N - c * e_i."""
    return Mechanism(
        name=f"Profit {i}",
        interface=Interface(
            forward_in=(
                port(f"Fisher {i} Effort"),
                port("Price Signal"),
                port("Total Harvest"),
            ),
        ),
        updates=[(f"Fisher {i}", "cumulative_profit")],
        tags={"domain": "State Update", "player": str(i)},
    )


def build_profit_mechanisms(n: int = N_FISHERS) -> list[Mechanism]:
    return [_build_profit_mechanism(i) for i in range(1, n + 1)]


# ══════════════════════════════════════════════════════════════════
# Spec
# ══════════════════════════════════════════════════════════════════


def build_spec(n: int = N_FISHERS) -> GDSSpec:
    """Build the complete unregulated fishery specification.

    Registers types, spaces, entities, blocks, parameters, wiring,
    admissibility constraints, and transition signatures.
    """
    spec = GDSSpec(
        name="Gordon-Schaefer Fishery (Unregulated)",
        description=(
            f"Common-pool resource fishery with {n} symmetric fishers. "
            "No regulation — Nash equilibrium depletes stock below MSY."
        ),
    )

    fisher_entities = build_fisher_entities(n)
    fisher_blocks = build_fisher_blocks(n)
    harvest_rate = _build_harvest_rate_block(n)
    profit_mechs = build_profit_mechanisms(n)

    # Types
    for td in [Biomass, Effort, Catch, Profit, Price, RateParam, Capacity, CostParam]:
        spec.register_type(td)

    # Spaces
    for sp in [
        biomass_signal_space,
        effort_signal_space,
        catch_signal_space,
        growth_signal_space,
        price_signal_space,
        profit_signal_space,
    ]:
        spec.register_space(sp)

    # Entities
    spec.register_entity(fish_population)
    for ent in fisher_entities:
        spec.register_entity(ent)

    # Blocks
    spec.register_block(market_price)
    spec.register_block(stock_observer)
    for fb in fisher_blocks:
        spec.register_block(fb)
    spec.register_block(harvest_rate)
    spec.register_block(growth_rate)
    spec.register_block(population_dynamics)
    for pm in profit_mechs:
        spec.register_block(pm)

    # Parameters (Theta)
    spec.register_parameter(
        ParameterDef(
            name="r",
            typedef=RateParam,
            description="Intrinsic growth rate",
            bounds=(0.05, 2.0),
        )
    )
    spec.register_parameter(
        ParameterDef(
            name="K",
            typedef=Capacity,
            description="Carrying capacity",
            bounds=(1_000.0, 1_000_000.0),
        )
    )
    spec.register_parameter(
        ParameterDef(
            name="q",
            typedef=RateParam,
            description="Catchability coefficient",
            bounds=(1e-6, 1e-2),
        )
    )
    spec.register_parameter(
        ParameterDef(
            name="p",
            typedef=Price,
            description="Market price per unit harvest",
            bounds=(100.0, 50_000.0),
        )
    )
    spec.register_parameter(
        ParameterDef(
            name="c",
            typedef=CostParam,
            description="Cost per unit effort",
            bounds=(100.0, 100_000.0),
        )
    )
    spec.register_parameter(
        ParameterDef(
            name="m",
            typedef=RateParam,
            description="Natural mortality rate",
            bounds=(0.0, 0.5),
        )
    )

    # Wiring
    all_block_names = [
        "Market Price",
        "Stock Observer",
        *[f"Fisher {i}" for i in range(1, n + 1)],
        "Harvest Rate",
        "Growth Rate",
        "Population Dynamics",
        *[f"Profit {i}" for i in range(1, n + 1)],
    ]

    wires = [
        # Price → each fisher
        *[
            Wire(source="Market Price", target=f"Fisher {i}", space="PriceSignalSpace")
            for i in range(1, n + 1)
        ],
        # Price → each profit mechanism
        *[
            Wire(source="Market Price", target=f"Profit {i}", space="PriceSignalSpace")
            for i in range(1, n + 1)
        ],
        # Observer → each fisher
        *[
            Wire(
                source="Stock Observer",
                target=f"Fisher {i}",
                space="BiomassSignalSpace",
            )
            for i in range(1, n + 1)
        ],
        # Each fisher → harvest rate
        *[
            Wire(
                source=f"Fisher {i}",
                target="Harvest Rate",
                space="EffortSignalSpace",
            )
            for i in range(1, n + 1)
        ],
        # Each fisher → their profit mechanism
        *[
            Wire(
                source=f"Fisher {i}",
                target=f"Profit {i}",
                space="EffortSignalSpace",
            )
            for i in range(1, n + 1)
        ],
        # Harvest rate → population dynamics
        Wire(
            source="Harvest Rate",
            target="Population Dynamics",
            space="CatchSignalSpace",
        ),
        # Harvest rate → each profit mechanism
        *[
            Wire(
                source="Harvest Rate",
                target=f"Profit {i}",
                space="CatchSignalSpace",
            )
            for i in range(1, n + 1)
        ],
        # Growth rate → population dynamics
        Wire(
            source="Growth Rate",
            target="Population Dynamics",
            space="GrowthSignalSpace",
        ),
    ]

    spec.register_wiring(
        SpecWiring(
            name="Fishery Pipeline",
            block_names=all_block_names,
            wires=wires,
            description="Unregulated fishery: price+observation → decisions → harvest+growth → state update",
        )
    )

    # Admissibility constraints (paper Def 2.5)
    spec.register_admissibility(
        AdmissibleInputConstraint(
            name="market_viability",
            boundary_block="Market Price",
            depends_on=[("Fish Population", "level")],
            constraint=lambda state, price: state[("Fish Population", "level")] > 0,
            description="Market price is only meaningful when stock exists (N > 0)",
        )
    )

    # Transition signatures (paper Def 2.7)
    spec.register_transition_signature(
        TransitionSignature(
            mechanism="Population Dynamics",
            reads=[("Fish Population", "level")],
            depends_on_blocks=["Harvest Rate", "Growth Rate"],
            preserves_invariant="N >= 0 when harvest <= standing stock",
        )
    )
    for i in range(1, n + 1):
        spec.register_transition_signature(
            TransitionSignature(
                mechanism=f"Profit {i}",
                reads=[(f"Fisher {i}", "cumulative_profit")],
                depends_on_blocks=[f"Fisher {i}", "Harvest Rate", "Market Price"],
            )
        )

    return spec


# ══════════════════════════════════════════════════════════════════
# System compilation
# ══════════════════════════════════════════════════════════════════


def build_system(n: int = N_FISHERS) -> SystemIR:
    """Build and compile the fishery system with temporal feedback.

    Composition tree:
        (Market Price | Stock Observer)
            >> (Fisher 1 | ... | Fisher n)
            >> (Harvest Rate | Growth Rate)
            >> (Population Dynamics | Profit 1 | ... | Profit n)
            .loop(Population Dynamics -> Stock Observer, Harvest Rate, Growth Rate)
    """
    from gds.blocks.composition import Wiring
    from gds.ir.models import FlowDirection

    fisher_blocks = build_fisher_blocks(n)
    harvest_rate = _build_harvest_rate_block(n)
    profit_mechs = build_profit_mechanisms(n)

    # Tier 0: exogenous inputs + observer
    tier0 = market_price | stock_observer

    # Tier 1: fisher decisions (parallel)
    tier1 = fisher_blocks[0]
    for fb in fisher_blocks[1:]:
        tier1 = tier1 | fb

    # Tier 2: rate computations (parallel)
    tier2 = harvest_rate | growth_rate

    # Tier 3: state updates (parallel)
    tier3 = population_dynamics
    for pm in profit_mechs:
        tier3 = tier3 | pm

    # Sequential pipeline with explicit wiring between tiers
    # (token overlap doesn't hold across all tier boundaries, so we
    # use StackComposition with explicit wiring where needed)
    from gds.blocks.composition import StackComposition

    pipeline = StackComposition(
        name="Fishery Pipeline",
        first=StackComposition(
            name="Tiers 0-1",
            first=tier0,
            second=tier1,
            wiring=[
                # Observer → each fisher
                *[
                    Wiring(
                        source_block="Stock Observer",
                        source_port="Observed Stock",
                        target_block=f"Fisher {i}",
                        target_port="Observed Stock",
                    )
                    for i in range(1, n + 1)
                ],
                # Price → each fisher
                *[
                    Wiring(
                        source_block="Market Price",
                        source_port="Price Signal",
                        target_block=f"Fisher {i}",
                        target_port="Price Signal",
                    )
                    for i in range(1, n + 1)
                ],
            ],
        ),
        second=StackComposition(
            name="Tiers 2-3",
            first=tier2,
            second=tier3,
            wiring=[
                Wiring(
                    source_block="Harvest Rate",
                    source_port="Total Harvest",
                    target_block="Population Dynamics",
                    target_port="Total Harvest",
                ),
                Wiring(
                    source_block="Growth Rate",
                    source_port="Natural Growth",
                    target_block="Population Dynamics",
                    target_port="Natural Growth",
                ),
                # Efforts + harvest + price → profit mechanisms
                *[
                    Wiring(
                        source_block=f"Fisher {i}",
                        source_port=f"Fisher {i} Effort",
                        target_block=f"Profit {i}",
                        target_port=f"Fisher {i} Effort",
                    )
                    for i in range(1, n + 1)
                ],
            ],
        ),
        wiring=[
            # Fisher efforts → harvest rate
            *[
                Wiring(
                    source_block=f"Fisher {i}",
                    source_port=f"Fisher {i} Effort",
                    target_block="Harvest Rate",
                    target_port=f"Fisher {i} Effort",
                )
                for i in range(1, n + 1)
            ],
        ],
    )

    # Temporal loop: population level feeds back to observer and rate computations
    system = pipeline.loop(
        [
            Wiring(
                source_block="Population Dynamics",
                source_port="Population Level",
                target_block="Stock Observer",
                target_port="Population Level",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Population Dynamics",
                source_port="Population Level",
                target_block="Harvest Rate",
                target_port="Population Level",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Population Dynamics",
                source_port="Population Level",
                target_block="Growth Rate",
                target_port="Population Level",
                direction=FlowDirection.COVARIANT,
            ),
        ],
        exit_condition="steady_state",
    )

    return compile_system(name="Gordon-Schaefer Fishery", root=system)


def build_canonical(n: int = N_FISHERS) -> CanonicalGDS:
    """Project the canonical form h = f . g."""
    return project_canonical(build_spec(n))


# ══════════════════════════════════════════════════════════════════
# Analytical benchmarks (validation targets)
# ══════════════════════════════════════════════════════════════════

# Default parameter values (overfishing scenario: N_inf < N_MSY)
DEFAULTS = {
    "r": 0.5,        # intrinsic growth rate (year^-1)
    "K": 100_000.0,  # carrying capacity (tonnes)
    "q": 1e-4,       # catchability (boat-day^-1)
    "p": 2_000.0,    # market price ($/tonne)
    "c": 5_000.0,    # cost per effort ($/boat-day)
    "m": 0.05,       # natural mortality (year^-1)
    "n": N_FISHERS,
}


def analytical_benchmarks(
    r: float = DEFAULTS["r"],
    K: float = DEFAULTS["K"],
    q: float = DEFAULTS["q"],
    p: float = DEFAULTS["p"],
    c: float = DEFAULTS["c"],
    n: int = DEFAULTS["n"],
) -> dict:
    """Compute closed-form Gordon-Schaefer results for test validation."""
    N_inf = c / (p * q)          # bionomic equilibrium (open access)
    N_MSY = K / 2                # maximum sustainable yield stock
    N_MEY = (K + N_inf) / 2      # maximum economic yield stock
    H_MSY = r * K / 4            # MSY harvest
    E_MSY = r / (2 * q)          # MSY effort
    E_inf = (r / q) * (1 - N_inf / K)  # bionomic effort

    # n-player Nash equilibrium (Cournot on common pool)
    e_nash = r * (p * q * K - c) / ((n + 1) * p * q**2 * K)
    E_nash = n * e_nash
    N_nash = (K + n * N_inf) / (n + 1)

    # Effort ratio: Nash uses 2n/(n+1) times optimal effort
    effort_ratio = 2 * n / (n + 1)

    # Optimal regulation
    Q_MSY = r * K / 4
    Q_MEY = r * (K**2 - N_inf**2) / (4 * K)
    tau_MEY = (p * q * K - c) / 2  # Pigouvian tax

    return {
        # Biological
        "N_MSY": N_MSY,
        "H_MSY": H_MSY,
        "E_MSY": E_MSY,
        # Bionomic
        "N_inf": N_inf,
        "E_inf": E_inf,
        # Economic optimum
        "N_MEY": N_MEY,
        # Nash equilibrium
        "e_nash": e_nash,
        "E_nash": E_nash,
        "N_nash": N_nash,
        "effort_ratio": effort_ratio,
        # Regulation
        "Q_MSY": Q_MSY,
        "Q_MEY": Q_MEY,
        "tau_MEY": tau_MEY,
        # Ordering (should hold when overfishing occurs)
        "overfishing": N_inf < N_MSY,
    }

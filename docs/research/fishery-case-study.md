# Case Study: Gordon-Schaefer Common-Pool Resource Fishery

> Comprehensive design document for a single case study that exercises the entire
> [GDS-Core Improvement Roadmap](improvement-roadmap.md). The Gordon-Schaefer fishery
> model is chosen because it naturally requires stock-flow dynamics, game-theoretic
> analysis, regulatory control, disturbance modeling, and dual time representations —
> touching 13 of 15 roadmap items without contrivance.
>
> **Theoretical basis:** Gordon (1954), Schaefer (1957), Clark (1990, *Mathematical Bioeconomics*).

---

## 1. Why This System

The tragedy of the commons is the most studied cross-lens disagreement in economics:
the Nash equilibrium (each fisher maximizes individual catch) is dynamically stable but
socially suboptimal. That single fact requires every analysis capability the roadmap
proposes.

The fishery is modeled in three progressive variants:

| Variant | What it demonstrates | Roadmap items exercised |
|---------|---------------------|------------------------|
| **V1: Unregulated** | Tragedy of the commons — Nash equilibrium depletes stock | T0-1, T0-4, T1-1, T1-2, T2-2, T2-3 |
| **V2: Regulated** | ControlAction/duality — regulator observes catch, sets quota | T0-3, T1-1, T1-2, T2-1, T2-3 |
| **V3: Disturbed** | Disturbance formalization — environmental shock bypasses decisions | T1-3, T2-2 |

All three share the same stock-flow substrate and compile to the same canonical algebra.

---

## 2. Entities and State Variables

| Entity | Variable | Type | Units | Domain | Description |
|--------|----------|------|-------|--------|-------------|
| Fish Population | `level` | `LevelType` (float, ≥ 0) | tonnes | BiomassSpace | Total fish biomass N |
| Fisher *i* (×n) | `cumulative_profit` | float | $ | ProfitSpace | Accumulated economic rent π_i |
| Regulator | `quota` | float, ≥ 0 | tonnes/year | QuotaSpace | Current total allowable catch Q |

**State space X:**

```
X = {N, π_1, ..., π_n, Q}
dim(X) = n + 2  (1 biomass + n profits + 1 quota)
```

In the unregulated variant (V1), the Regulator entity is absent: `dim(X) = n + 1`.

---

## 3. Parameters (Θ)

All declared with bounds in `ParameterSchema`. The PSUU sweep (T1-2) must respect these.

| Parameter | Symbol | TypeDef | Bounds | Default | Units | Source |
|-----------|--------|---------|--------|---------|-------|--------|
| Intrinsic growth rate | r | float, > 0 | [0.05, 2.0] | 0.5 | year⁻¹ | Biological |
| Carrying capacity | K | float, > 0 | [1000, 1_000_000] | 100_000 | tonnes | Ecological |
| Catchability | q | float, > 0 | [1e-6, 1e-2] | 1e-4 | (boat-day)⁻¹ | Technological |
| Fish price | p | float, > 0 | [100, 50_000] | 2000 | $/tonne | Market |
| Cost per effort | c | float, > 0 | [100, 100_000] | 5000 | $/boat-day | Economic |
| Natural mortality | m | float, ≥ 0 | [0, 0.5] | 0.05 | year⁻¹ | Biological |
| Number of fishers | n | int, > 0 | [1, 100] | 10 | — | Structural |
| Target stock (V2) | N_target | float, > 0 | [0, K] | K/2 | tonnes | Policy |

**Default parameterization produces overfishing:** With `c = 5000`, `p = 2000`, `q = 1e-4`:

```
N_∞ = c/(pq) = 5000/(2000 × 0.0001) = 25,000 tonnes
N_MSY = K/2 = 50,000 tonnes
N_∞ < N_MSY  →  overfishing under open access ✓
```

---

## 4. Analytical Benchmarks (Validation Targets)

These are closed-form results from the Gordon-Schaefer model. Every simulation result
and cross-lens query must be validated against them.

### 4.1 Biological Equilibria

```python
# Maximum Sustainable Yield
N_MSY = K / 2
H_MSY = r * K / 4
E_MSY = r / (2 * q)

# Bionomic equilibrium (open access, zero rent)
N_oo = c / (p * q)
E_oo = (r / q) * (1 - N_oo / K)

# Maximum Economic Yield (social optimum)
N_MEY = (K + N_oo) / 2
E_MEY = (r / (2 * q)) * (1 - N_oo / K)

# Ordering (when c/(pq) < K/2, i.e., overfishing occurs)
assert N_oo < N_MSY < N_MEY < K
assert E_MEY < E_MSY < E_oo
```

### 4.2 n-Player Nash Equilibrium

```python
# Symmetric Nash effort (Cournot on common pool)
e_nash = r * (p * q * K - c) / ((n + 1) * p * q**2 * K)
E_nash = n * e_nash

# Nash equilibrium stock
N_nash = (K + n * N_oo) / (n + 1)

# Limiting behavior
assert abs(N_nash - N_oo) < epsilon  # as n → ∞ (tragedy)
# n = 1 (sole owner): N_nash = (K + N_oo) / 2 = N_MEY

# Effort ratio: Nash uses 2n/(n+1) × optimal effort
assert abs(E_nash / E_MEY - 2 * n / (n + 1)) < epsilon
```

### 4.3 Optimal Regulation

```python
# Quota that achieves MSY
Q_MSY = r * K / 4

# Quota that achieves MEY
Q_MEY = r * (K**2 - N_oo**2) / (4 * K)

# Pigouvian effort tax for MEY
tau_MEY = (p * q * K - c) / 2
```

### 4.4 Dynamic Stability

```python
# Continuous-time: eigenvalue at equilibrium N* with fixed effort E
eigenvalue = -(r - q * E)  # negative iff E < r/q (viable fishery)

# Discrete-time: Jacobian at N*
jacobian = 1 - (r - q * E)
# Stable iff |jacobian| < 1, i.e., 0 < r - q*E < 2

# All three equilibria (bionomic, MSY, MEY) are stable fixed points
# when effort is held constant at the equilibrium level
```

### 4.5 Default Parameter Validation Table

With `r=0.5, K=100000, q=1e-4, p=2000, c=5000, m=0.05, n=10`:

| Quantity | Formula | Value | Units |
|----------|---------|-------|-------|
| N_∞ | c/(pq) | 25,000 | tonnes |
| N_MSY | K/2 | 50,000 | tonnes |
| N_MEY | (K + N_∞)/2 | 62,500 | tonnes |
| H_MSY | rK/4 | 12,500 | tonnes/year |
| E_MSY | r/(2q) | 2,500 | boat-days |
| E_∞ | (r/q)(1 - N_∞/K) | 3,750 | boat-days |
| N_nash (n=10) | (K + 10·N_∞)/11 | 31,818 | tonnes |
| e_nash | r(pqK-c)/((n+1)pq²K) | 310.9 | boat-days/fisher |
| Q*_MSY | rK/4 | 12,500 | tonnes/year |
| τ*_MEY | (pqK-c)/2 | 7,500 | $/boat-day |

---

## 5. GDS Type System

### 5.1 TypeDefs

```python
BiomassType = TypeDef(
    name="Biomass", python_type=float,
    constraint=lambda x: x >= 0,
    description="Fish biomass (non-negative)", units="tonnes",
)
EffortType = TypeDef(
    name="Effort", python_type=float,
    constraint=lambda x: x >= 0,
    description="Fishing effort", units="boat-days",
)
CatchType = TypeDef(
    name="Catch", python_type=float,
    constraint=lambda x: x >= 0,
    description="Harvest quantity", units="tonnes/year",
)
ProfitType = TypeDef(
    name="Profit", python_type=float,
    description="Economic rent (may be negative)", units="$",
)
QuotaType = TypeDef(
    name="Quota", python_type=float,
    constraint=lambda x: x >= 0,
    description="Total allowable catch", units="tonnes/year",
)
GrowthRateType = TypeDef(
    name="GrowthRate", python_type=float,
    description="Perturbed growth rate (may be reduced by disturbance)",
    units="year⁻¹",
)
```

### 5.2 Spaces

| Space | Fields | Used by |
|-------|--------|---------|
| BiomassSpace | `{value: BiomassType}` | Fish Population entity, stock level ports |
| EffortSpace | `{value: EffortType}` | Fisher decision outputs |
| CatchSpace | `{value: CatchType}` | Harvest rate ports, CatchObservation output |
| ProfitSpace | `{value: ProfitType}` | Fisher profit entity |
| QuotaSpace | `{value: QuotaType}` | Regulator quota entity, regulator policy output |
| GrowthRateSpace | `{value: GrowthRateType}` | Environmental shock + growth rate auxiliary |

---

## 6. Block Architecture

### 6.1 Variant 1: Unregulated Fishery

#### BoundaryActions (exogenous inputs U)

| Block | Ports | Params | Description |
|-------|-------|--------|-------------|
| `Market Price` | out: `"Market Price Signal"` | `[p]` | Exogenous fish price |

#### Policies (decision layer g)

| Block | Inputs | Outputs | Description |
|-------|--------|---------|-------------|
| `Stock Observer` | in: `"Fish Population Level"` | out: `"Observed Stock Signal"` | Fishers observe current stock (perfect information) |
| `Fisher i` (×n) | in: `"Observed Stock Signal"`, `"Market Price Signal"` | out: `"Fisher i Effort"` | Each fisher chooses effort to maximize profit |
| `Harvest Rate` | in: `"Fisher i Effort"` (×n), `"Fish Population Level"` | out: `"Total Harvest Rate"` | Computes H = q · (Σe_i) · N |
| `Growth Rate` | in: `"Fish Population Level"` | out: `"Natural Growth Rate"` | Computes G = r·N·(1 - N/K) - m·N |

#### Mechanisms (state update f)

| Block | Inputs | Outputs | Updates | Description |
|-------|--------|---------|---------|-------------|
| `Population Dynamics` | in: `"Natural Growth Rate"`, `"Total Harvest Rate"` | out: `"Fish Population Level"` | `[("Fish Population", "level")]` | N' = N + G - H |
| `Profit Accumulation i` (×n) | in: `"Fisher i Effort"`, `"Total Harvest Rate"`, `"Market Price Signal"` | — | `[("Fisher i", "cumulative_profit")]` | π_i' = π_i + p·h_i - c·e_i |

#### Composition Tree

```
(Market Price | Stock Observer)
  >> (Fisher 1 | Fisher 2 | ... | Fisher n)
  >> (Harvest Rate | Growth Rate)
  >> (Population Dynamics | Profit 1 | ... | Profit n)
  .loop(Population Dynamics → Stock Observer)     # temporal, covariant
  .loop(Population Dynamics → Growth Rate)        # temporal, covariant
  .loop(Population Dynamics → Harvest Rate)       # temporal, covariant
```

#### Canonical Decomposition (expected)

```
X = {N, π_1, ..., π_n}
U = {p}
g = {Market Price, Stock Observer, Fisher 1..n, Harvest Rate, Growth Rate}
f = {Population Dynamics, Profit Accumulation 1..n}
h = f ∘ g

|X| = n + 1,  |f| = n + 1,  |C| = 0  (no ControlAction in V1)
```

---

### 6.2 Variant 2: Regulated Fishery (adds ControlAction + Regulator)

Everything from V1, plus:

#### ControlAction (output map C — NEW, exercises T0-3)

| Block | Inputs | Outputs | Description |
|-------|--------|---------|-------------|
| `Catch Observation` | in: `"Total Harvest Rate"`, `"Fish Population Level"` | out: `"Observed Total Catch"` | y = C(N, H) — what the regulator can see. This IS the output map. |

**Duality at work:** From inside the fishery system, `Catch Observation` is an output map — it produces the observable signal y. From outside (the regulator's perspective), y is the input signal the regulator acts on.

#### Additional Policy (regulator decision)

| Block | Inputs | Outputs | Description |
|-------|--------|---------|-------------|
| `Regulator Policy` | in: `"Observed Total Catch"` | out: `"Quota Signal"` | Q' = g_reg(Y, N_target). Adjusts quota based on observed catch vs. target. |

#### Modified Fisher (quota-constrained)

| Block | Inputs | Outputs | Description |
|-------|--------|---------|-------------|
| `Fisher i` (×n) | in: `"Observed Stock Signal"`, `"Market Price Signal"`, **`"Quota Signal"`** | out: `"Fisher i Effort"` | e_i = min(e*_i, Q/n). Effort capped by quota share. |

#### Composition Tree

```
(Market Price | Stock Observer | Catch Observation)
  >> Regulator Policy
  >> (Fisher 1 | Fisher 2 | ... | Fisher n)
  >> (Harvest Rate | Growth Rate)
  >> (Population Dynamics | Profit 1 | ... | Profit n)
  .loop(Population Dynamics → Stock Observer)
  .loop(Population Dynamics → Growth Rate)
  .loop(Population Dynamics → Harvest Rate)
  .loop(Population Dynamics → Catch Observation)  # ControlAction reads state
  .loop(Regulator Policy → Regulator Quota)       # quota state update
```

#### Canonical Decomposition (expected)

```
X = {N, π_1, ..., π_n, Q}
U_c = {p}                        (controlled — fishers observe)
Y = {Observed Total Catch}       (output map — ControlAction)
g = {Market Price, Stock Observer, Regulator Policy, Fisher 1..n, Harvest Rate, Growth Rate}
f = {Population Dynamics, Profit Accumulation 1..n, Quota Update}
C = {Catch Observation}
h = f ∘ g

|X| = n + 2,  |f| = n + 2,  |C| = 1  (one ControlAction)
```

---

### 6.3 Variant 3: Disturbed Fishery (adds disturbance, exercises T1-3)

Everything from V2, plus:

#### Disturbance-Tagged BoundaryAction

| Block | Ports | Tags | Description |
|-------|-------|------|-------------|
| `Environmental Shock` | out: `"Growth Rate Perturbation"` | `{"role": "disturbance"}` | Exogenous shock to growth rate. Bypasses all decision-makers. |

**Routing:** `Environmental Shock` wires directly to `Growth Rate` auxiliary (which feeds `Population Dynamics`). It does NOT wire to any Policy block. DST-001 verifies this.

#### Modified Growth Rate

| Block | Inputs | Outputs | Description |
|-------|--------|---------|-------------|
| `Growth Rate` | in: `"Fish Population Level"`, **`"Growth Rate Perturbation"`** | out: `"Natural Growth Rate"` | G = (r + w)·N·(1 - N/K) - m·N, where w is the disturbance |

#### Extended Canonical

```
X = {N, π_1, ..., π_n, Q}
U_c = {p}                        (controlled — observed by policy)
W = {Growth Rate Perturbation}   (disturbance — bypasses g)
Y = {Observed Total Catch}
g: X × U_c → D                  (policy map — does NOT see W)
f: X × D × W → X                (state update — W enters directly)
C: X × D → Y                    (output map)
```

---

## 7. Game-Theoretic Formulation (OGS / PatternIR)

The same system expressed as an Open Game for cross-lens analysis (T2-3).

### 7.1 Game Structure

```python
# Each fisher is a DecisionGame
fisher_i = DecisionGame(
    name=f"Fisher {i}",
    signature=Signature(
        x=(port("Observed Stock"), port("Market Price"), port("Quota")),
        y=(port(f"Fisher {i} Effort"),),
        r=(port(f"Fisher {i} Payoff"),),       # utility feedback
        s=(),                                    # no coutility
    ),
    logic="Choose effort e_i to maximize π_i = p·q·e_i·N - c·e_i, subject to e_i ≤ Q/n",
    tags={"domain": "Harvesting", "player": str(i)},
)

# Stock dynamics as a CovariantFunction (no strategic choice)
population_update = CovariantFunction(
    name="Population Update",
    signature=Signature(
        x=(port("Total Effort"), port("Current Stock")),
        y=(port("Next Stock"),),
    ),
    logic="N' = N + r·N·(1 - N/K) - q·E·N",
)

# Payoff evaluation as a TerminalGame
payoff_eval = TerminalGame(
    name="Payoff Evaluation",
    signature=Signature(
        x=(port("Fisher Efforts"), port("Stock Level"), port("Price")),
        r=(port("Fisher 1 Payoff"), ..., port(f"Fisher {n} Payoff")),
    ),
    logic="π_i = p·q·e_i·N - c·e_i for each fisher",
)
```

### 7.2 Pattern Composition

```python
pattern = Pattern(
    name="Fishery Harvesting Game",
    games=[
        Source(name="Nature", ...),       # emits stock level, price
        fisher_1, fisher_2, ..., fisher_n,
        population_update,
        payoff_eval,
    ],
    flows=[
        # Forward (covariant): Nature → Fishers → Population Update
        Flow("Nature", "Stock Level", "Fisher 1", "Observed Stock"),
        ...
        Flow(f"Fisher {i}", f"Fisher {i} Effort", "Population Update", "Total Effort"),
        # Backward (contravariant): Payoff Eval → Fishers (utility feedback)
        Flow("Payoff Evaluation", f"Fisher {i} Payoff", f"Fisher {i}", f"Fisher {i} Payoff",
             direction=FlowDirection.CONTRAVARIANT),
    ],
    terminal_condition=TerminalCondition(condition_type="iteration_limit", threshold=100),
    action_spaces={
        f"Fisher {i}": ActionSpace(
            game_name=f"Fisher {i}",
            action_type="continuous",
            bounds=(0.0, 1000.0),  # effort bounds
        ) for i in range(1, n + 1)
    },
)
```

### 7.3 Canonical Bridge (compile_pattern_to_spec)

The OGS pattern compiles to GDSSpec via `compile_pattern_to_spec()`. Expected result:

```
f = ∅  (population_update is CovariantFunction → mapped to Policy, not Mechanism)
X = ∅  (no state in the game-theoretic lens — state is in the dynamical lens)
g = all games
h = g  (pure policy, no state transition — the OGS degenerate form)
```

This is correct and expected: the game-theoretic lens sees the fishery as a **stateless** strategic interaction. The state (fish population, profits) lives in the dynamical lens. The cross-lens query infrastructure (T2-3) connects them.

---

## 8. Cross-Lens Queries (T2-3)

These are the publishable results. Each query compares the PatternIR (game lens) with CanonicalGDS (dynamical lens).

### 8.1 Unregulated: Is the Nash Equilibrium a Fixed Point?

```python
result = query.is_nash_equilibrium_a_fixed_point(
    pattern_ir=unregulated_pattern,
    canonical_gds=unregulated_canonical,
)
# Expected: True
# The Nash equilibrium effort E_nash produces stock N_nash = (K + n·N_∞)/(n+1),
# which IS a stable fixed point of the population dynamics.
# This is the tragedy: the bad outcome is stable.
```

### 8.2 Unregulated: Is the Stable Attractor Incentive-Compatible?

```python
result = query.is_stable_attractor_incentive_compatible(
    canonical_gds=unregulated_canonical,
    pattern_ir=unregulated_pattern,
    attractor_state={"Fish Population": {"level": N_MSY}},  # MSY stock
)
# Expected: False
# N_MSY is a stable fixed point (if effort = E_MSY), but E_MSY is NOT a Nash
# equilibrium — each fisher has incentive to increase effort above E_MSY/n.
# The socially optimal outcome is not individually rational.
```

### 8.3 Regulated: Does the Quota Align the Lenses?

```python
# With optimal quota Q* = rK/4
result_nash = query.is_nash_equilibrium_a_fixed_point(
    pattern_ir=regulated_pattern,
    canonical_gds=regulated_canonical,
)
# Expected: True (Nash equilibrium under quota constraint is at MSY)

result_ic = query.is_stable_attractor_incentive_compatible(
    canonical_gds=regulated_canonical,
    pattern_ir=regulated_pattern,
    attractor_state={"Fish Population": {"level": N_MSY}},
)
# Expected: True (under the quota, MSY IS incentive-compatible)
```

**The regulation parameter Q is the mechanism that aligns the two lenses.** The PSUU sweep (T1-2) finds Q* by sweeping over quota values and checking when both cross-lens queries return True.

### 8.4 Disturbed: Is the Aligned Outcome Robust?

```python
# Under environmental disturbance w ~ N(0, σ²)
result = query.is_stable_attractor_incentive_compatible(
    canonical_gds=disturbed_canonical,
    pattern_ir=disturbed_pattern,
    attractor_state={"Fish Population": {"level": N_MSY}},
)
# Expected: depends on disturbance magnitude σ
# For small σ: True (regulation survives noise)
# For large σ: False (stock crashes below MSY despite regulation)
# The critical σ* is itself a parameter sweep result
```

---

## 9. Behavioral Verification (T2-2)

### 9.1 BV-001: Universal Invariants

| Predicate | Channel | DSL | Expected (V1) | Expected (V2) | Expected (V3) |
|-----------|---------|-----|----------------|----------------|----------------|
| N ≥ 0 (non-negative stock) | Fish Population Level | stockflow | PASS | PASS | PASS (small σ), FAIL (large σ) |
| π_total ≥ 0 (positive aggregate rent) | Σ Profit | custom | FAIL (V1 may have negative rent if c high) | PASS (under optimal quota) | depends |
| H ≤ Q (quota respected) | Total Harvest Rate | custom | N/A (no quota) | PASS | PASS |

### 9.2 BV-002: Fixed-Point (Convergence)

| Predicate | Channel | Eq definition | Expected (V1) | Expected (V2) |
|-----------|---------|--------------|----------------|----------------|
| Stock steady state | Fish Population Level | \|N(t) - N(t-1)\| < ε | PASS (converges to N_nash) | PASS (converges to N_MSY) |
| Profit steady state | Fisher i Profit rate | \|Δπ(t) - Δπ(t-1)\| < ε | PASS (constant rent at equilibrium) | PASS |

### 9.3 Falsification Cases

| System | Structural | Behavioral | Result |
|--------|-----------|------------|--------|
| V1 with r > 2, no harvest | G/SC pass | BV-002 FAIL (discrete logistic oscillation) | Structural ✓, behavioral ✗ |
| V1 with c → 0 (cheap fishing) | G/SC pass | BV-001 borderline (N → 0) | Stock near-collapse despite well-formed spec |
| V2 with Q = 0 (fishery closed) | G/SC pass | BV-002 PASS, BV-001 PASS (stock recovers to K) | Trivial regulation |
| V3 with σ >> r | G/SC pass | BV-001 FAIL (stock crashes negative) | Disturbance overwhelms regulation |

---

## 10. Structural Analysis (T2-1)

### 10.1 Structural Reachability (graph queries on SystemIR)

| From (BoundaryAction) | To (Entity variable) | Reachable? | Path |
|------------------------|---------------------|------------|------|
| Market Price → Fish Population.level | Yes | Market Price → Fisher i → Harvest Rate → Population Dynamics |
| Market Price → Fisher i.cumulative_profit | Yes | Market Price → Fisher i → Profit Accumulation i |
| Environmental Shock → Fish Population.level | Yes (direct) | Env Shock → Growth Rate → Population Dynamics |
| Environmental Shock → Fisher i.cumulative_profit | Yes (indirect) | Env Shock → Growth Rate → Pop Dynamics → (loop) → Stock Observer → Fisher i → Profit i |

### 10.2 Structural Distinguishability (requires T0-3)

| From (Entity variable) | To (ControlAction output) | Distinguishable? | Path |
|------------------------|--------------------------|-------------------|------|
| Fish Population.level → Observed Total Catch | Yes | Pop Dynamics → Catch Observation |
| Fisher i.cumulative_profit → Observed Total Catch | No | No path from profit to catch observation |

**Interpretation:** The regulator can observe the fish stock (indirectly, through catch data) but cannot observe individual fisher profits. This is a structural limitation of the regulatory design — no amount of policy sophistication can overcome unobservable state.

---

## 11. Execution Contracts (T1-1)

### 11.1 Discrete-Time (primary)

```python
ExecutionContract(
    time_domain="discrete",
    synchrony="synchronous",
    observation_delay=0,
    update_ordering="Moore",
)
```

**Semantics:**

```
d[t]   = g(x[t], u_c[t])                  # all policies execute on current state
x[t+1] = f(x[t], d[t], w[t])              # all mechanisms update simultaneously
y[t]   = C(x[t], d[t])                    # output map reads current state + decisions
```

**Discrete-time map:**

```
N[t+1] = N[t] + r·N[t]·(1 - N[t]/K) - q·E[t]·N[t] - m·N[t] + w[t]
```

### 11.2 Continuous-Time (T2-4, same canonical structure)

```python
ExecutionContract(
    time_domain="continuous",
)
```

**Semantics (ODE):**

```
dN/dt = r·N·(1 - N/K) - q·E·N - m·N + w(t)
```

**Same wiring topology, same canonical decomposition.** Different solver: RK4 or scipy `solve_ivp` via SolverInterface.

### 11.3 Game Layer (atemporal)

```python
ExecutionContract(
    time_domain="atemporal",
)
```

The game-theoretic PatternIR carries no time model. Cross-lens queries (T2-3) must handle the contract mismatch: the dynamical lens is discrete/continuous, the game lens is atemporal. This is a valid comparison — the game lens computes equilibria, the dynamical lens checks if those equilibria are fixed points.

---

## 12. PSUU Parameter Sweep (T1-2)

### 12.1 Sweep Configuration

```python
# ParameterSchema from GDSSpec (structural bounds)
schema = spec.parameter_schema  # r, K, q, p, c, m, n, N_target

# ParameterSpace (search domain — must validate against schema)
space = ParameterSpace(params={
    "r": Continuous(0.1, 1.0),
    "c": Continuous(1000, 20000),
    "n": Integer(2, 50),
    "N_target": Continuous(10000, 80000),  # only for V2
})

# PSUU-001 validation: all bounds within ParameterSchema constraints
space.validate_against_schema(schema)  # must pass before sweep starts
```

### 12.2 Sweep Objectives

| Objective | KPI | Optimization |
|-----------|-----|--------------|
| Find critical fisher count | N_nash(n) vs N_MSY | At what n does N_nash drop below N_MSY? |
| Find optimal quota | \|N_steady - N_MSY\| | Minimize stock deviation from MSY |
| Find robustness boundary | P(N > 0 \| σ) | Maximum disturbance σ with 95% stock survival |
| Validate effort ratio | E_nash / E_MEY | Should equal 2n/(n+1) — analytical validation |

---

## 13. AdmissibleInputConstraint (existing infrastructure)

The fishery naturally demonstrates state-dependent input admissibility (paper Def 2.5):

```python
AdmissibleInputConstraint(
    name="Effort Viability",
    boundary_block="Market Price",
    depends_on=[("Fish Population", "level")],
    constraint=lambda state, price: state[("Fish Population", "level")] > 0,
    description="Market price is only meaningful if stock exists (N > 0)",
)

AdmissibleInputConstraint(
    name="Harvest Feasibility",
    boundary_block="Environmental Shock",  # disturbance variant
    depends_on=[("Fish Population", "level")],
    constraint=lambda state, w: state[("Fish Population", "level")] + w > -r,
    description="Disturbance cannot reduce effective growth rate below -r",
)
```

---

## 14. TransitionSignature (existing infrastructure)

```python
TransitionSignature(
    mechanism="Population Dynamics",
    reads=[("Fish Population", "level")],
    depends_on_blocks=["Harvest Rate", "Growth Rate"],
    preserves_invariant="N ≥ 0 if BV-001 holds",
)

TransitionSignature(
    mechanism="Profit Accumulation i",
    reads=[("Fisher i", "cumulative_profit")],
    depends_on_blocks=[f"Fisher {i}", "Harvest Rate", "Market Price"],
)
```

---

## 15. Packages Exercised

| Package | Role | Variant |
|---------|------|---------|
| **gds-framework** | Core spec, canonical form, all G/SC checks, ControlAction role | V1, V2, V3 |
| **gds-stockflow** | Fish population dynamics (Stock, Flow, Auxiliary, Converter) | V1, V2, V3 |
| **gds-games** | Harvesting game (DecisionGame, CovariantFunction, Pattern) | V1, V2 |
| **gds-control** | Regulatory controller (Sensor → Controller → Plant) | V2, V3 |
| **gds-sim** | Discrete-time simulation, Moore semantics | V1, V2, V3 |
| **gds-continuous** | Continuous-time ODE simulation via SolverInterface | V1 (cont.), V2 (cont.) |
| **gds-analysis** | Structural reachability, behavioral checks, spec→sim bridge | V1, V2, V3 |
| **gds-psuu** | Parameter sweep over Θ with PSUU-001 validation | V1, V2, V3 |
| **gds-viz** | Composition diagrams, phase portraits (N vs H) | V1, V2, V3 |
| **gds-owl** | Formal ontology export (fishery domain) | V2 |
| **gds-examples** | The case study itself, marimo notebooks | All |

**11 of 14 packages.** Not used: gds-software (no software architecture diagram), gds-business (fishery is not CLD/SCN/VSM), gds-symbolic (no symbolic math unless doing analytical stability via SymPy).

---

## 16. Roadmap Item Mapping

| Roadmap Item | How the Fishery Exercises It |
|---|---|
| **T0-1** Check specs | All 15 G/SC checks run on compiled fishery SystemIR/GDSSpec |
| **T0-2** Traceability | Fishery tests tagged with `@pytest.mark.requirement` markers |
| **T0-3** ControlAction | `Catch Observation` is a ControlAction. Duality: catch is simultaneously system output and regulator input. SC-010 validates forward-path routing. |
| **T0-4** Temporal agnosticism | Same fishery model in discrete + continuous time. OGS pattern is atemporal. Three ExecutionContracts on one system. |
| **T1-1** ExecutionContract | Discrete/Moore for stockflow, continuous for ODE, atemporal for game layer. SC-011 checks cross-composition compatibility. |
| **T1-2** PSUU ↔ Θ | Sweep over (r, c, n, N_target, Q) validated against ParameterSchema bounds. PSUU-001 catches out-of-bounds sweeps. |
| **T1-3** Disturbance | `Environmental Shock` tagged `{"role": "disturbance"}`, wires to Growth Rate (mechanism path), bypasses all policies. DST-001 validates. |
| **T1-4** Assurance | Verification passport filled out for V1 and V2. Explicit: structural checks pass, behavioral checks needed for stability/convergence claims. |
| **T2-1** Reachability | Structural reachability: can disturbance reach stock? Can regulator observe profit? Graph queries answer without simulation. |
| **T2-2** Behavioral | BV-001: N ≥ 0. BV-002: stock converges to steady state. Falsification: r > 2 discrete oscillation, large σ crash. |
| **T2-3** Cross-lens | **The core result.** Nash equilibrium IS a stable fixed point (tragedy). Regulation aligns lenses. Disturbance breaks alignment. |
| **T2-4** Continuous-time | Same canonical form, different ExecutionContract, different solver. Discrete and continuous results converge to same steady state. |
| **T3-3** Stochastic (future) | Environmental shock becomes stochastic: w ~ N(0, σ²). Probabilistic BV-001: P(N ≥ 0) ≥ 0.95. |

---

## 17. Implementation Sequence

The fishery case study is built incrementally as roadmap phases complete:

### After Phase 1 (Foundations)

- Build V1 (unregulated) using gds-stockflow for population dynamics
- Build the OGS Pattern for the n-player harvesting game
- Validate all G/SC checks pass on the compiled system
- Write check specifications for every check that fires
- Validate analytical benchmarks: N_nash, E_nash, H_MSY against closed-form formulas

### After Phase 2 (Traceability + PSUU)

- Add `@pytest.mark.requirement` markers to all fishery tests
- Connect PSUU sweep to ParameterSchema — sweep over n, validate N_nash(n) = (K + n·N_∞)/(n+1)
- Verify PSUU-001 catches a sweep with c < 0 (outside declared bounds)
- Fill out verification passport for V1

### After Phase 3 (Execution Semantics)

- Build V2 (regulated) — add Catch Observation (ControlAction) and Regulator Policy
- Attach ExecutionContracts to all three layers (discrete, continuous, atemporal)
- Build V3 (disturbed) — add Environmental Shock with disturbance tag
- Verify DST-001 passes (disturbance doesn't wire to Policy)
- Verify SC-010 passes (Catch Observation doesn't wire to Policy in forward path)
- Verify SC-011 passes (compatible execution contracts within each layer)

### After Phase 4 (Analysis + Behavioral)

- Run structural reachability/distinguishability queries
- Register BV-001 (N ≥ 0) and BV-002 (convergence) predicates
- Run behavioral verification on all three variants
- Execute cross-lens queries — the publishable results
- Build continuous-time variant — verify convergence to same steady state
- Run full PSUU sweep to find optimal quota and robustness boundary

### Publishable Output

A single document or notebook showing:

1. The unregulated fishery: game and dynamical lenses agree on a bad outcome (tragedy)
2. The regulated fishery: optimal quota aligns the lenses (resolution)
3. The disturbed fishery: environmental noise can break the alignment (fragility)
4. The parameter sweep: the critical regulation parameter that transitions between regimes
5. Dual time models: same result in discrete and continuous time (specification ≠ simulation)

All validated against closed-form Gordon-Schaefer analytical results.

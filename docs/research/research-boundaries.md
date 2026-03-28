# Research Boundaries and Open Questions

> Design note documenting the architectural boundary between structural compositional modeling (validated) and dynamical execution/analysis (next frontier). Written after the third independent DSL (gds-control) compiled cleanly to GDSSpec with no canonical modifications.

---

## Status: What Has Been Validated

Three independent DSLs now compile to the same algebraic core:

| DSL | Domain | Decision layer (g) | Update layer (f) | Canonical |
|---|---|---|---|---|
| gds-stockflow | System dynamics | Auxiliaries + Flows | Accumulation mechanisms | Clean |
| gds-control | Control theory | Sensors + Controllers | Plant dynamics | Clean |
| gds-games (OGS) | Game theory | All games (observation → decision → evaluation) | ∅ (no state update) | Clean — via `compile_pattern_to_spec()` |

All three reduce to the same canonical form without modification:

```
d = g(x, u)
x' = f(x, d)
```

Key structural facts:

- Canonical `h = f ∘ g` has survived three domains with no extensions required.
- No DSL uses `ControlAction` — all non-state-updating blocks map to `Policy`.
- Role partition (boundary, policy, mechanism) is complete and disjoint in every case.
- Cross-built equivalence (DSL-compiled vs hand-built) has been verified at Spec, Canonical, and SystemIR levels for all three DSLs.
- OGS canonical validation confirms `f = ∅`, `X = ∅` — compositional game theory is a **degenerate dynamical system** where `h = g` (pure policy, no state transition). See [RQ3](#research-question-3-ogs-as-degenerate-dynamical-system) below.

A canonical composition pattern has emerged across DSLs:

```
(peripheral observers | exogenous inputs)
    >> (decision logic)
    >> (state dynamics)
.loop(state → observers)
```

This motif appears in system dynamics, state-space control, and (structurally) reinforcement learning. It is not prescribed by the algebra — it is a convergent pattern discovered through independent DSL development.

---

## Research Question 1: MIMO Semantics in a Compositional Dynamical Substrate

### Background

The current architecture represents multi-input multi-output (MIMO) systems structurally as collections of scalar ports. Cross-coupling is encoded inside block-local semantics (e.g., update functions), not in the wiring topology.

For example in gds-control:

- Each state variable is its own Entity.
- Each controller output is a separate port.
- Each dynamics mechanism reads multiple scalar control ports.
- Coupling (e.g., matrix A or B terms) is embedded inside `f`.

This is sufficient for structural modeling and canonical decomposition.

However, classical control theory treats `x ∈ R^n`, `u ∈ R^m`, `y ∈ R^p` as vector spaces with explicit matrix semantics. This raises a fundamental architectural question.

### The Question

**Should MIMO structure remain decomposed into scalar channels (structural MIMO), or should vector-valued spaces become first-class citizens in the type system (algebraic MIMO)?**

### Option A — Structural MIMO (Current Design)

Each dimension is modeled as an independent scalar port. Vector structure emerges from parallel composition.

**Properties:**
- Canonical remains dimension-agnostic
- TypeDef and Space remain scalar
- Coupling lives in block-local semantics
- Dimensionality is implicit (count of states, inputs, etc.)

**Advantages:**
- Minimal extension to Layer 0
- Canonical remains purely structural
- DSLs remain lightweight
- Works across stockflow, games, and control without special treatment

**Limitations:**
- No static dimension checking
- Cannot extract A, B, C, D matrices directly from structure
- No structural controllability/observability analysis
- No rank-based reasoning
- Numerical coupling invisible at IR level

**Interpretation:** This treats GDS as a structural substrate, not a linear algebra system.

### Option B — First-Class Vector Spaces

Introduce vector-valued spaces with explicit dimensionality:

```python
StateSpace(n)
InputSpace(m)
OutputSpace(p)
```

Ports carry structured types, not scalars.

**Properties:**
- Dimensionality becomes explicit
- Wiring validates dimension compatibility
- Canonical operates over vector-valued X and U
- Matrix structure potentially extractable

**Advantages:**
- Enables structural controllability tests
- Enables matrix extraction
- Enables symbolic linearization
- Closer alignment with classical control theory

**Costs:**
- Type system complexity increases
- Cross-DSL consistency must be preserved
- Potential leakage of numerical semantics into structural core
- Requires careful integration with canonical

### Deeper Structural Question

Is GDS intended to be:

1. A compositional topology algebra (structure only), or
2. A compositional linear-algebra-aware modeling language?

If (1), structural MIMO is sufficient.
If (2), vector semantics become necessary.

### Possible Hybrid Approach

- Keep scalar structural core (Layer 0 unchanged)
- Add optional dimensional metadata to spaces
- Build matrix extraction as a canonical post-processing tool (Layer 4)

This preserves architectural purity while enabling analysis. The metadata would be inert — stripped at compile time like tags — but available to projection tools that know how to interpret it.

### Current Recommendation

Stay with structural MIMO. The scalar decomposition is correct for the current purpose (structural modeling and canonical decomposition). Vector semantics should be explored only when a concrete analysis tool (e.g., structural controllability) demonstrates that scalar decomposition is genuinely insufficient, not merely inconvenient.

---

## Research Question 2: What Does a Timestep Mean Across DSLs?

### Background

Temporal recurrence is represented structurally via `.loop()` and temporal wirings. This operator is used in multiple DSLs with different semantic intentions:

| DSL | Temporal Meaning | What `.loop()` Represents |
|---|---|---|
| StockFlow | State persistence | Stock level at t feeds auxiliaries at t+1 |
| Control | State observation | Plant state at t feeds sensors at t+1 |
| OGS | Round iteration | Decisions at round t feed observations at round t+1 |

At the IR level, all temporal wirings are identical:

```
source → target (temporal, covariant)
```

Canonical treats recurrence purely algebraically — `x' = f(x, g(x, u))` — without encoding evaluation scheduling, delay, or sampling semantics.

This is correct structurally. But it is incomplete for execution.

### The Question

**What is the formal meaning of a timestep in GDS, and should execution semantics be standardized across DSLs?**

### Current Implicit Assumption

All current DSLs assume synchronous discrete-time execution (Moore-style):

1. Compute `d = g(x[t], u[t])`
2. Compute `x[t+1] = f(x[t], d)`
3. All observation and control occur within one step

### Where This Breaks Down

Different domains could legitimately interpret `.loop()` differently:

| Domain | Temporal Interpretation |
|---|---|
| StockFlow | Accumulation (state += flow * dt) |
| Control | Sampling (sensor reads current state) |
| Delayed control | `x[t-1]` feeds controller, not `x[t]` |
| Hybrid systems | Mode-dependent recurrence |
| Continuous-time | Integration over dt |

The algebra does not distinguish these. The structural fact "information flows from state output to sensor input across timesteps" is the same in all cases. The semantic question "is this observation delayed?" is invisible at the IR level.

### The Core Tension

`.loop()` encodes **structural recurrence** but not **scheduling semantics**.

If simulation is introduced, the following questions must be answered:

- Is temporal wiring zero-delay or one-step delay?
- Are updates synchronous or staged?
- Does observation occur before or after state update?
- Is the timestep uniform across all temporal wirings?

Without explicit execution semantics, different DSLs may assume incompatible timestep meanings while sharing the same IR.

### Option A — Canonical Execution Model

Define execution directly from canonical:

```python
d = g(x, u)       # observation + decision
x_next = f(x, d)  # state update
```

All DSLs must conform to this synchronous discrete-time semantics. A timestep is always: observe, decide, update. No delays. No staging.

**Advantages:**
- Minimal
- Uniform
- Canonical becomes directly executable

**Limitations:**
- Cannot express delayed observation without additional state variables
- Continuous-time requires external discretization
- Hybrid timing needs extensions beyond `.loop()`

### Option B — Execution Semantics Layer

Introduce an explicit execution contract as metadata, not as part of the IR:

```python
@dataclass(frozen=True)
class ExecutionSemantics:
    synchronous: bool = True
    observation_delay: int = 0
    integration_scheme: str = "explicit"
```

Keep IR structural. Attach semantics externally. Each DSL declares its own execution contract. A simulation harness reads the contract and dispatches accordingly.

**Advantages:**
- Clean separation of structure and dynamics
- Supports multiple scheduling regimes
- Preserves canonical purity
- DSLs remain composable at the structural level even with different execution semantics

**Costs:**
- Additional abstraction layer
- Increased conceptual surface area
- Cross-DSL simulation becomes a compatibility question rather than a guarantee

### Deeper Question

Is GDS:

1. A structural modeling algebra only?
2. Or a full dynamical execution framework?

If (1), temporal semantics remain external and domain-local (consistent with the current architecture principle: "Simulation is domain-local").
If (2), a principled shared timestep model must be defined.

### Current Recommendation

Temporal semantics should remain external. The architecture document already states: "The protocol provides no execution semantics." This is correct. The right approach is:

1. Keep `.loop()` as purely structural recurrence (no scheduling meaning at Layer 0).
2. Each DSL defines its own execution contract if/when it adds simulation.
3. A shared discrete-time runner (if built) operates on canonical form and assumes synchronous Moore semantics as the default.
4. DSLs that need different timing (delays, continuous, hybrid) declare it explicitly and are not required to be cross-simulatable.

---

## Research Question 3: OGS as Degenerate Dynamical System

### Finding

Canonical projection of OGS patterns produces:

```
X = ∅       (no state variables — games have no persistent entities)
U = inputs  (PatternInput → BoundaryAction)
D = all game forward_out ports
g = all games (observation → decision → evaluation)
f = ∅       (no mechanisms — games don't update state)
```

The canonical decomposition reduces to `h = g`. There is no state transition. The system is **pure policy**.

This is not a failure of the projection — it is the correct structural characterization of compositional game theory within GDS.

### Why X = ∅ Is Expected

Games compute equilibria. They do not write to persistent state variables. The game-theoretic objects (strategies, utilities, coutilities) flow through the composition as signals, not as state updates. Even corecursive loops (repeated games) carry information forward as observations, not as entity mutations.

In category-theoretic terms: open games are morphisms in a symmetric monoidal category with feedback. They are maps, not state machines. The "state" of a repeated game is the sequence of past plays — which in OGS is modeled as observations flowing through the composition (the History game), not as Entity variables.

### Why f = ∅ Is Semantically Correct

No OGS game type performs a state update:

| Game Type | Port Structure | Role |
|---|---|---|
| DecisionGame | (X,Y,R,S) → full 4-port | Policy — strategic choice |
| CovariantFunction | (X,Y) → forward only | Policy — observation transform |
| ContravariantFunction | (R,S) → backward only | Policy — utility transform |
| DeletionGame | (X,∅) → discard | Policy — information loss |
| DuplicationGame | (X, X×X) → broadcast | Policy — information copy |
| CounitGame | (X,∅,∅,X) → future conditioning | Policy — temporal reference |

All six map to `Policy`. None updates an Entity. Therefore `f` is empty and the mechanism layer is vacuous.

### The Spectrum of Canonical Dimensionality

Three domains now provide three distinct points on the canonical spectrum:

| Domain | |X| | |f| | |g| | Canonical Form | Interpretation |
|---|---|---|---|---|---|
| OGS (games) | 0 | 0 | all | `h = g` | Stateless — pure equilibrium computation |
| Control | n | n | sensors + controllers | `h = f ∘ g` | Full — observation, decision, state update |
| StockFlow | n | n | auxiliaries + flows | `h = f ∘ g` | State-dominant — accumulation dynamics |

This reveals that `h = f ∘ g` is not merely "a decomposition of dynamical systems." It is a **transition calculus** that gracefully degenerates:

- When `f = ∅`: the system is pure policy (games, decision logic, signal processing)
- When `g` is thin: the system is state-dominant (accumulation, diffusion)
- When both are substantial: the system is a full feedback dynamical system

The unifying abstraction is `(x, u) ↦ x'` with varying dimensionality of X. All three domains are specializations of this map.

### Structural Gap That Was Bridged

OGS originally had no path to canonical:

1. OGS blocks subclassed `OpenGame(Block)`, not GDS roles (`Policy`/`Mechanism`/`BoundaryAction`)
2. OGS produced `PatternIR → SystemIR`, never `GDSSpec`
3. `project_canonical()` classifies blocks via `isinstance` against role classes

The bridge (`compile_pattern_to_spec()`) resolves this by:
- Mapping all atomic games to `Policy` blocks (preserving their GDS Interface)
- Mapping `PatternInput` to `BoundaryAction`
- Resolving flows via the existing compiler, then registering as `SpecWiring`

This is a parallel path — `PatternIR` remains for OGS-specific tooling (reports, visualization, game-theoretic vocabulary). The bridge enables canonical projection without replacing the existing pipeline.

### Implication for PatternIR

`PatternIR` is no longer required for semantic correctness. Its remaining justifications:

1. **Report generation** — Jinja2 templates reference `OpenGameIR` fields (game_type, signature as X/Y/R/S)
2. **Game-theoretic vocabulary** — `FlowType.OBSERVATION` vs `FlowType.UTILITY_COUTILITY` carries domain meaning
3. **Visualization** — Mermaid generators use game-specific metadata

These are view-layer concerns (Layer 4). Whether to consolidate `PatternIR` into `GDSSpec` + metadata is a refactoring question, not a correctness question. The bridge proves they produce equivalent canonical results.

---

## Research Question 4: Cross-Lens Analysis — When Equilibrium and Reachability Disagree

### Background

With three DSLs compiling to GDSSpec, the framework now supports two independent analytical lenses on the same system:

1. **Game-theoretic lens** (via PatternIR) — equilibria, incentive compatibility, strategic structure, utility propagation
2. **Dynamical lens** (via GDSSpec/CanonicalGDS) — reachability, controllability, stability, state-space structure

These lenses are orthogonal. Neither subsumes the other:

- Game equilibrium does not imply dynamical stability (a Nash equilibrium can be an unstable fixed point)
- Dynamical stability does not imply strategic optimality (a stable attractor can be Pareto-dominated)
- Reachability does not imply incentive compatibility (a reachable state may require irrational agent behavior)

### The Question

**When the two lenses disagree for a concrete system, what does that disagreement mean — and which lens, if either, should be treated as normative?**

### Why Neither Lens Can Be Normative

If the game-theoretic lens is normative ("redesign dynamics to enforce equilibrium"), you assume the equilibrium concept is correct for the domain. But Nash equilibria can be dynamically unstable, Pareto-dominated, or unreachable from feasible initial conditions.

If the dynamical lens is normative ("redesign incentives to force stability"), you assume the target attractor is desirable. But stable attractors can be socially inefficient or represent lock-in traps.

### The Architectural Answer

GDS is a **diagnostic instrument**, not a normative engine.

The framework's value is in surfacing the disagreement. When equilibrium and reachability conflict, that conflict is information:

- "Your incentive design has unintended dynamical consequences" (equilibrium exists but is unreachable)
- "Your dynamics have unintended strategic consequences" (stable point exists but is not an equilibrium)

The modeler resolves the tension using domain knowledge. The framework provides the structured vocabulary to state the problem precisely.

### Implications for Architecture

This means the two-lens architecture must remain genuinely parallel:

```
Pattern
 ├─ PatternIR  → game-theoretic analysis (equilibria, incentives)
 └─ GDSSpec    → dynamical analysis (reachability, stability)
```

Neither representation should absorb the other. If canonical were extended to encode equilibrium concepts, or if PatternIR were extended to encode reachability, the lenses would collapse and the diagnostic power would be lost.

The correct architectural move is to build **cross-lens queries** — analyses that take both representations as input and report on their (dis)agreement:

- "Is this Nash equilibrium a stable fixed point of the state dynamics?"
- "Is this stable attractor consistent with individual rationality?"
- "Does this reachable state satisfy incentive compatibility?"

These are research-level questions that require both lenses simultaneously.

### Connection to Timestep Semantics (RQ2)

Cross-lens disagreement can also arise from implicit timestep incompatibility. If the game-theoretic lens assumes simultaneous play but the dynamical lens assumes sequential evaluation, "equilibrium" and "stability" may refer to different execution models operating on the same structural specification.

This reinforces the RQ2 recommendation: temporal semantics must remain explicit and domain-local. Cross-lens analysis must verify that both lenses assume compatible execution semantics before comparing their conclusions.

### Trigger

This question becomes concrete when:

| Trigger | What It Reveals |
|---|---|
| Building a game-theoretic + dynamical co-analysis tool | Whether the two lenses can be queried simultaneously |
| A concrete system where equilibrium ≠ stable fixed point | Whether the framework can express the disagreement |
| Mechanism design applications | Whether the framework supports prescriptive (not just descriptive) use |
| Lean/formal verification exports | Whether canonical's analytical lossyness causes proof gaps |

### Current Recommendation

Do not attempt to resolve the tension architecturally. Keep the lenses parallel. Build cross-lens analysis as a separate concern that consumes both representations. The framework's role is to make the question askable, not to answer it.

---

## Strategic Assessment

These questions mark the boundary between:

- **Structural compositional modeling** — validated by three DSLs, canonical proven stable
- **Dynamical execution and control-theoretic analysis** — the next frontier

They are the first genuine architectural fork points after validating canonical centrality.

### What This Means for Development Priority

Neither question requires immediate resolution. Both are triggered by concrete future work:

| Trigger | Research Question Activated |
|---|---|
| Building a structural controllability analyzer | RQ1 (MIMO semantics) |
| Building a shared simulation harness | RQ2 (timestep semantics) |
| Adding a continuous-time DSL | RQ1 + RQ2 |
| Adding a hybrid systems DSL | RQ1 + RQ2 |
| Extracting state-space matrices (A, B, C, D) | RQ1 |
| Consolidating OGS PatternIR into GDSSpec | RQ3 (refactoring decision) |
| Adding a stateless DSL (signal processing, Bayesian networks) | RQ3 (validates X=∅ pattern) |

Until one of these triggers occurs, the current architecture is complete and correct for its stated purpose: structural compositional modeling with formal verification and canonical decomposition.

### The Stability Claim

After three independent domains with three distinct canonical profiles (`h = g`, `h = f ∘ g` full, `h = f ∘ g` state-dominant):

- The composition algebra (Layer 0) is validated and should not change.
- The canonical projection (`h = f ∘ g`) is correctly minimal — and gracefully degenerates when `f = ∅`.
- The role system (Boundary, Policy, Mechanism) covers all three domains without `ControlAction`.
- The type/space system handles semantic separation across all three domains.
- The temporal loop pattern is structurally uniform and semantically adequate for structural modeling.
- Cross-built equivalence holds at Spec, Canonical, and SystemIR levels for all three DSLs.

The canonical form `(x, u) ↦ x'` with varying dimensionality of X now functions as a **unified transition calculus** — not merely a decomposition of dynamical systems, but a typed algebra of transition structure that absorbs stateless (games), stateful (control), and state-dominant (stockflow) formalisms under one composition substrate.

Further DSLs (signal processing, compartmental models, queueing networks) should compile to this same substrate without architectural changes. If they don't, that is a signal that the boundary has been reached — not that the architecture needs extension.

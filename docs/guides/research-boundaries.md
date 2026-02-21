# Research Boundaries and Open Questions

> Design note documenting the architectural boundary between structural compositional modeling (validated) and dynamical execution/analysis (next frontier). Written after the third independent DSL (gds-control) compiled cleanly to GDSSpec with no canonical modifications.

---

## Status: What Has Been Validated

Three independent DSLs now compile to the same algebraic core:

| DSL | Domain | Decision layer (g) | Update layer (f) | Canonical |
|---|---|---|---|---|
| gds-stockflow | System dynamics | Auxiliaries + Flows | Accumulation mechanisms | Clean |
| gds-control | Control theory | Sensors + Controllers | Plant dynamics | Clean |
| gds-games (OGS) | Game theory | Observation → Decision | Utility/coutility | Projected via `to_system_ir()` |

All three reduce to the same canonical form without modification:

```
d = g(x, u)
x' = f(x, d)
```

Key structural facts:

- Canonical `h = f ∘ g` has survived three domains with no extensions required.
- No DSL uses `ControlAction` — all non-state-updating blocks map to `Policy`.
- Role partition (boundary, policy, mechanism) is complete and disjoint in every case.
- Cross-built equivalence (DSL-compiled vs hand-built) has been verified at Spec, Canonical, and SystemIR levels for both stockflow and control.

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

## Strategic Assessment

These two questions mark the boundary between:

- **Structural compositional modeling** — validated by three DSLs, canonical proven stable
- **Dynamical execution and control-theoretic analysis** — the next frontier

They are the first genuine architectural fork points after validating canonical centrality.

### What This Means for Development Priority

Neither question requires immediate resolution. Both are triggered by concrete future work:

| Trigger | Research Question Activated |
|---|---|
| Building a structural controllability analyzer | RQ1 (MIMO semantics) |
| Building a shared simulation harness | RQ2 (timestep semantics) |
| Adding a continuous-time DSL | Both |
| Adding a hybrid systems DSL | Both |
| Extracting state-space matrices (A, B, C, D) | RQ1 |

Until one of these triggers occurs, the current architecture is complete and correct for its stated purpose: structural compositional modeling with formal verification and canonical decomposition.

### The Stability Claim

After three independent domains:

- The composition algebra (Layer 0) is validated and should not change.
- The canonical projection (`h = f ∘ g`) is correctly minimal.
- The role system (Boundary, Policy, Mechanism) covers all three domains without `ControlAction`.
- The type/space system handles semantic separation across all three domains.
- The temporal loop pattern is structurally uniform and semantically adequate for structural modeling.

Further DSLs (signal processing, compartmental models, queueing networks) should compile to this same substrate without architectural changes. If they don't, that is a signal that the boundary has been reached — not that the architecture needs extension.

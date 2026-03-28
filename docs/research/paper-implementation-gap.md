# Paper vs. Implementation: Gap Analysis

> Systematic comparison of the GDS software implementation against
> Zargham & Shorish (2022), *Generalized Dynamical Systems Part I: Foundations*
> (DOI: 10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc).
>
> Purpose: identify what the software faithfully implements, what it extends
> beyond the paper, and what paper concepts remain unimplemented. Concludes
> with a concrete bridge proposal.

---

## 1. Core Object Mapping

### 1.1 Faithfully Implemented

| Paper (Section 2) | Notation | Software | Notes |
|---|---|---|---|
| State Space (Def 2.1) | X | `Entity` + `StateVariable`; X = product of all entity variables | Product structure is explicit |
| State (Def 2.2) | x in X | Dict of entity -> variable -> value | At runtime only (gds-sim) |
| Trajectory (Def 2.3) | x_0, x_1, ... | gds-sim trajectory execution | Deferred to simulation package |
| Input Space (Def 2.4) | U | `BoundaryAction.forward_out` ports | Structural only |
| Input (Def 2.4) | u in U | Signal on boundary port | At runtime only |
| State Update Map (Def 2.6) | f : X x U_x -> X | `Mechanism` blocks with `updates` field | Structural skeleton only -- f_struct (which entity/variable) is captured, f_behav (the function) is not stored |
| Input Map (Def 2.8) | g : X -> U_x | `Policy` blocks | Same: structural identity only |
| State Transition Map (Def 2.9) | h = f\|_x . g | `project_canonical()` computes formula | Declared composition, not executable |
| GDS (Def 2.10) | {h, X} | `CanonicalGDS` dataclass | Faithful for structural identity |

### 1.2 Structurally Implemented (Steps 1-2 of Bridge Proposal)

| Paper (Section 2) | Notation | Software | Notes |
|---|---|---|---|
| Admissible Input Space (Def 2.5) | U_x subset U | `AdmissibleInputConstraint` — dependency graph (which state variables constrain which inputs) | Structural skeleton (R1). The actual constraint predicate is R3/lossy, same as TypeDef.constraint. SC-008 validates references. |
| Restricted State Update Map (Def 2.7) | f\|_x : U_x -> X | `TransitionSignature` — read dependencies (which state variables a mechanism reads) | Structural skeleton (R1). Complements Mechanism.updates (writes). SC-009 validates references. |

### 1.3 Not Implemented

| Paper (Section 2-4) | Notation | What It Does | Why It Matters |
|---|---|---|---|
| Admissible Input Map (Def 2.5) | U : X -> P(U) | The actual function computing the admissible input set | R3 — requires runtime evaluation. The structural dependency graph is captured (see 1.2), but the computation is not. |
| Metric on State Space (Asm 3.2) | d_X : X x X -> R | Distance between states | Required for contingent derivative, reachability rate |
| Attainability Correspondence (Def 3.1) | F : X x R+ x R+ => X | Set of states reachable at time t from (x_0, t_0) | Foundation for reachability and controllability |
| Contingent Derivative (Def 3.3) | D'F(x_0, t_0, t) | Generalized rate of change (set-valued) | Connects trajectories to input maps; enables existence proofs |
| Constraint Set (Asm 3.5) | C(x, t; g) subset X | Compact, convex set restricting contingent derivatives | Required for Theorem 3.6 (existence of solutions) |
| Existence of Solutions (Thm 3.6) | D'F = C(x_0, t_0) | Conditions under which a trajectory exists | The paper's core analytical result |
| Reachable Set (Def 4.1) | R(x) = union{f(x,u)} | Immediately reachable states from x | Foundation for configuration space and controllability |
| Configuration Space (Def 4.2) | X_C subset X | Mutually reachable connected component | Characterizes the "live" portion of state space |
| Local Controllability (Thm 4.4) | 0-controllable from eta_0 | Conditions for steering to equilibrium | Engineering design guarantee |
| Observability / Design Invariants (Sec 4.4) | P(x_i) = TRUE | Properties that should hold along trajectories | Design verification (invariant checking) |

### 1.4 Software Extensions Beyond the Paper

| Software Concept | Purpose | Paper Status |
|---|---|---|
| Composition algebra (>>, \|, .feedback(), .loop()) | Build h from typed, composable blocks | Paper takes h as given; no composition operators |
| Bidirectional interfaces (F_in, F_out, B_in, B_out) | Contravariant/covariant flow directions | Paper has unidirectional f, g |
| Four-role partition (Boundary, Policy, Mechanism, ControlAction) | Typed block classification | Paper has monolithic f and g |
| Token-based type system | Structural auto-wiring via port name matching | No counterpart |
| Parameters Theta (ParameterDef, ParameterSchema) | Explicit configuration space | Paper alludes to "factors that change h" but never formalizes |
| Decision space D | Intermediate space between g and f | Paper's g maps X -> U_x directly |
| Verification checks (G-001..G-006, SC-001..SC-009) | Structural validation | Paper assumes well-formed h |
| Compiler pipeline (flatten -> wire -> hierarchy) | Build IR from composition tree | No counterpart |
| SystemIR intermediate representation | Flat, inspectable system graph | No counterpart |
| Domain DSLs (stockflow, control, games, software, business) | Domain-specific compilation to GDS | No counterpart |
| Spaces (typed product spaces) | Signal spaces between blocks | Paper has U (input space) only |

---

## 2. Structural Divergences

### 2.1 The Canonical Form Signature

**Paper:**
```
g : X -> U_x           (input map: state -> admissible input)
f : X x U_x -> X       (state update: state x input -> next state)
h(x) = f(x, g(x))      (autonomous after g is fixed)
```

**Software:**
```
g : X x U -> D          (policy: state x exogenous input -> decisions)
f : X x D -> X          (mechanism: state x decisions -> next state)
h(x) = f(x, g(x, u))   (not autonomous -- exogenous U remains)
```

Key differences:

1. **The software interposes a decision space D.** The paper's g selects
   directly from the input space U. The software's g maps to a separate
   decision space D, distinct from U. This adds an explicit "observation ->
   decision" decomposition that the paper leaves inside g.

2. **The software's h is not autonomous.** The paper's h(x) = f(x, g(x)) is
   a function of state alone -- once g is chosen, the system is autonomous.
   The software's canonical form retains exogenous inputs U, making h a
   function of both state and environment.

3. **Admissible input restriction is absent.** The paper's g maps to U_x
   (state-dependent admissible subset). The software's BoundaryAction
   produces inputs unconditionally -- U_x = U for all x.

### 2.2 The Role Decomposition

The paper has two maps (f and g) with no further internal structure. The
software decomposes these into four block roles:

```
Paper g  -->  Software BoundaryAction + ControlAction + Policy
Paper f  -->  Software Mechanism
```

The ControlAction role (endogenous observation) has no paper analog. It
represents an internal decomposition of the paper's g into an observation
stage feeding a decision stage. This is an engineering design, not a
mathematical distinction from the paper.

### 2.3 What the Paper Assumes That the Software Must Build

The paper says "let h : X -> X be a state transition map" and proceeds to
analyze its properties. The software must answer: *how do you construct h
from components?*

The entire composition algebra -- the block tree, the operators, the
compiler, the wiring system, the token-based type matching -- is the
software's answer to this question. It is the primary contribution of the
implementation relative to the paper.

---

## 3. Analytical Machinery Gap

The paper devotes approximately 40% of its content (Sections 3-4) to
analytical machinery that the software does not implement. This machinery
falls into two categories:

### 3.1 Contingent Representation (Paper Section 3)

**What it provides:** Given a GDS {h, X} and initial conditions (x_0, t_0),
the contingent derivative D'F characterizes the set of directions in which
the system can evolve. Under regularity conditions (Assumption 3.5: constraint
set C is compact, convex, continuous), Theorem 3.6 guarantees the existence
of a solution trajectory.

**Why it matters:** This is the paper's mechanism for proving that a GDS
specification is *realizable* -- that trajectories satisfying the constraints
actually exist. Without it, a GDSSpec is a structural blueprint with no
guarantee that it corresponds to a well-defined dynamical process.

**Software status:** Entirely absent. The software can verify structural
invariants (all variables updated, no cycles, references valid) but cannot
determine whether the specified dynamics admit a trajectory.

### 3.2 Differential Inclusion Representation (Paper Section 4)

**What it provides:** The reachable set R(x) = union{f(x,u) : u in U_x}
defines what's immediately reachable from x. The configuration space X_C
is the mutually reachable connected component. Local controllability
(Theorem 4.4) gives conditions under which the system can be steered to
equilibrium.

**Why it matters:** These are the tools for engineering design verification:
- Can the system reach a desired operating point?
- Can it be steered back after perturbation?
- Is the reachable set consistent with safety constraints?

**Software status:** SC-003 (reachability) checks structural graph
reachability ("can signals propagate from block A to block B through
wirings"). This is topological, not dynamical. The paper's reachability
asks: "given concrete state x, which states x' can the system reach under
some input sequence?" -- a fundamentally different question.

### 3.3 The Remaining Gap

The structural skeletons of U_x and f|_x are now captured
(AdmissibleInputConstraint and TransitionSignature). What remains is the
analytical machinery that *uses* these structures: the metric on X, the
reachable set R(x), the configuration space X_C, and the contingent
derivative. These require runtime evaluation of f and g — they are
behavioral (R3), not structural.

---

## 4. Bridge Proposal

The gap between paper and implementation can be bridged incrementally.
Each step adds analytical capability while preserving the existing
structural core. Steps are ordered by dependency and increasing difficulty.

### Step 1: Admissible Input Map U_x -- IMPLEMENTED

**What:** State-dependent input constraints on the specification.

**Paper reference:** Definition 2.5 -- U : X -> P(U).

**Implementation:** `gds.AdmissibleInputConstraint` (frozen Pydantic model
in `gds/constraints.py`):

```python
from gds import AdmissibleInputConstraint

spec.register_admissibility(
    AdmissibleInputConstraint(
        name="balance_limit",
        boundary_block="market_order",
        depends_on=[("agent", "balance")],
        constraint=lambda state, u: u["quantity"] <= state["agent"]["balance"],
        description="Cannot sell more than owned balance"
    )
)
```

**What was delivered:**
- SC-008 (`check_admissibility_references`): validates boundary block exists,
  is a BoundaryAction, depends_on references valid (entity, variable) pairs
- `CanonicalGDS.admissibility_map`: populated by `project_canonical()`
- `SpecQuery.admissibility_dependency_map()`: boundary -> state variable deps
- OWL export/import with BNode-based tuple reification for depends_on
- SHACL shapes for structural validation
- Round-trip test (constraint callable is lossy, structural fields preserved)
- Keyed by `name` (not `boundary_block`) to allow multiple constraints per
  BoundaryAction

**Structural vs. behavioral split:**
- U_x_struct: the dependency relation (boundary -> state variables) -- R1
- U_x_behav: the actual constraint function -- R3 (same as TypeDef.constraint)

### Step 2: Restricted State Update Map f|_x -- IMPLEMENTED

**What:** Mechanism read dependencies (which state variables a mechanism reads).

**Paper reference:** Definition 2.7 -- f|_x : U_x -> X.

**Implementation:** `gds.TransitionSignature` (frozen Pydantic model in
`gds/constraints.py`):

```python
from gds import TransitionSignature

spec.register_transition_signature(
    TransitionSignature(
        mechanism="Heater",
        reads=[("Room", "temperature"), ("Environment", "outdoor_temp")],
        depends_on_blocks=["Controller"],
        preserves_invariant="energy conservation"
    )
)
```

**What was delivered:**
- SC-009 (`check_transition_reads`): validates mechanism exists, is a
  Mechanism, reads references valid (entity, variable) pairs,
  depends_on_blocks references registered blocks
- `CanonicalGDS.read_map`: populated by `project_canonical()`
- `SpecQuery.mechanism_read_map()`, `SpecQuery.variable_readers()`
- OWL export/import with BNode-based tuple reification for reads
- SHACL shapes for structural validation
- Round-trip test (structural fields preserved)
- `writes` deliberately omitted -- `Mechanism.updates` already tracks those
- One signature per mechanism (intentional simplification)

### Step 3: Metric on State Space

**What:** Equip X with a distance function, enabling the notion of "how far"
states are from each other.

**Paper reference:** Assumption 3.2 -- d_X : X x X -> R, a metric.

**Concrete design:**

```python
@dataclass(frozen=True)
class StateMetric:
    """A metric on the state space, enabling distance-based analysis."""
    name: str
    metric: Callable[[dict, dict], float]   # (state_1, state_2) -> distance
    covers: list[str]                        # entity.variable names in scope
    description: str = ""
```

For common cases, provide built-in metrics:

```python
# Euclidean metric over all numeric state variables
euclidean_state_metric(spec: GDSSpec) -> StateMetric

# Weighted metric with per-variable scaling
weighted_state_metric(spec: GDSSpec, weights: dict[str, float]) -> StateMetric
```

**Impact:**
- Enables Delta_x = d_X(x+, x) -- rate of change between successive states
- Foundation for reachable set computation (Step 5)
- Foundation for contingent derivative (Step 6)

**Prerequisite:** Runtime state representation (gds-sim integration).

**Structural vs. behavioral:** The metric itself is R3 (arbitrary callable).
The declaration that "these state variables participate in the metric" is
R1. The metric's properties (e.g., "Euclidean", "Hamming") could be R2
if annotated as metadata.

### Step 4: Reachable Set R(x)

**What:** Given a concrete state x and the state update map f, compute the
set of immediately reachable next states.

**Paper reference:** Definition 4.1 -- R(x) = union_{u in U_x} {f(x, u)}.

**Concrete design:**

```python
def reachable_set(
    spec: GDSSpec,
    state: dict,
    f: Callable[[dict, dict], dict],   # state update function
    input_sampler: Callable[[], Iterable[dict]],  # enumerates/samples U_x
) -> set[dict]:
    """Compute R(x) by evaluating f(x, u) for all admissible u."""
```

For finite/discrete input spaces, this is exact enumeration. For
continuous input spaces, this requires sampling or symbolic analysis.

**Impact:**
- First dynamical analysis capability
- Enables "what-if" analysis: "from this state, what states can I reach?"
- Foundation for configuration space (Step 5)

**Prerequisite:** Steps 1 (U_x), 3 (metric for measuring distance).
Requires gds-sim or equivalent runtime.

### Step 5: Configuration Space X_C

**What:** The mutually reachable connected component of the state space --
the set of states from which any other state in X_C is reachable.

**Paper reference:** Definition 4.2 -- X_C subset X such that for each
x in X_C, there exists x_0 and a reachable sequence reaching x.

**Concrete design:**

```python
def configuration_space(
    spec: GDSSpec,
    f: Callable,
    input_sampler: Callable,
    initial_states: Iterable[dict],
    max_depth: int = 100,
) -> set[frozenset]:
    """Compute X_C via BFS/DFS over R(x) from initial states."""
```

For finite state spaces, this is graph search over the reachability
graph. For continuous state spaces, this requires approximation
(grid-based, interval arithmetic, or abstraction).

**Impact:**
- Answers "is the target state reachable from the initial condition?"
- Identifies disconnected components (states the system can never reach)
- Foundation for controllability analysis

**Prerequisite:** Step 4 (reachable set).

### Step 6: Contingent Derivative (Research Frontier)

**What:** The generalized derivative that characterizes the set of
directions in which the system can evolve, given constraints.

**Paper reference:** Definition 3.3, Theorem 3.6.

**Why this is hard:** The contingent derivative requires:
1. A metric on X (Step 3)
2. The attainability correspondence F (requires iterating R(x) over time)
3. Convergence analysis (sequences converging to x_0 with rate limit)
4. The constraint set C(x, t; g) to be compact, convex, continuous

This is the paper's deepest analytical contribution and the hardest to
implement. It may be more appropriate as a separate analytical package
(e.g., gds-analysis) rather than part of gds-framework.

**Concrete approach:**

For the special case of discrete-time systems with finite input spaces:
- The contingent derivative reduces to the set of finite differences
  Delta_x / Delta_t for all admissible transitions
- Compactness of C is automatic (finite set)
- Convexity may or may not hold (depends on the transitions)
- Continuity must be checked numerically

For continuous state spaces:
- Requires interval arithmetic or symbolic differentiation
- Significantly harder; likely requires external tools (e.g., sympy,
  scipy, or a dedicated reachability library like CORA or JuliaReach)

**Prerequisite:** Steps 3-5. Likely a separate package.

### Step 7: Controllability Analysis (Research Frontier)

**What:** Conditions under which the system can be steered from any state
in a neighborhood to a target state.

**Paper reference:** Theorem 4.4 (local controllability).

**Requires:**
- Reachable set R(x) with metric (Steps 3-4)
- The boundary mapping partial_R to be Lipschitzian (numerical check)
- Closed, convex values (property of R)
- A controllable closed, strictly convex reachable process near target

This is the most advanced analytical capability in the paper and would
represent a significant research contribution if implemented. It connects
GDS to classical control theory results (controllability, observability)
in a generalized setting.

**Suggested approach:** Start with the linear case (where controllability
reduces to rank conditions on matrices) and generalize incrementally.
This connects directly to RQ1 (MIMO semantics) in research-boundaries.md.

---

## 5. Dependency Graph

```
Step 1: AdmissibleInputConstraint (U_x declaration)   -- DONE (gds-framework)
Step 2: TransitionSignature (f|_x declaration)         -- DONE (gds-framework)
    |
    v
Step 3: StateMetric (d_X on X)                        -- DONE (gds-framework)
    |
    v
Step 4: Reachable Set R(x)                            -- DONE (gds-analysis)
    |
    v
Step 5: Configuration Space X_C                       -- DONE (gds-analysis)
    |
    v
Step 6: Contingent Derivative D'F                     -- research frontier
Step 7: Local Controllability                          -- research frontier
```

Steps 1-3 are structural annotations in gds-framework with full OWL/SHACL
support in gds-owl. Steps 4-5 are runtime analysis in gds-analysis, which
bridges gds-framework to gds-sim. Steps 6-7 are research-level and may
require external tooling (SymPy, JuliaReach).

---

## 6. Package Placement

| Step | Where | Status |
|---|---|---|
| 1 (U_x) | gds-framework (constraints.py, spec.py) | **Done** — SC-008, OWL, SHACL |
| 2 (f\|_x signature) | gds-framework (constraints.py, spec.py, canonical.py) | **Done** — SC-009, OWL, SHACL |
| 3 (metric) | gds-framework (constraints.py, spec.py) | **Done** — StateMetric, OWL, SHACL |
| 4 (R(x)) | gds-analysis (reachability.py) | **Done** — `reachable_set()`, `ReachabilityResult` |
| 5 (X_C) | gds-analysis (reachability.py) | **Done** — `configuration_space()` (iterative Tarjan SCC) |
| 6 (D'F) | gds-analysis (future) | Research frontier |
| 7 (controllability) | gds-analysis (future) | Research frontier |

The `gds-analysis` package depends on both `gds-framework`
(for GDSSpec, CanonicalGDS) and `gds-sim` (for state evaluation), sitting
at the top of the dependency graph:

```
gds-framework  <--  gds-sim  <--  gds-analysis
     ^                                  |
     |                                  |
     +----------------------------------+
```

---

## 7. What Does Not Need Bridging

Some paper concepts are intentionally absent for good architectural reasons:

1. **Continuous-time dynamics (xdot = f(x(t)))** -- The paper presents this
   as an alternative representation. The software is discrete-time by design.
   Continuous-time would require a fundamentally different execution model.
   Per RQ2 in research-boundaries.md, temporal semantics should remain
   domain-local.

2. **The full attainability correspondence F as an axiomatic foundation** --
   The paper notes (Section 3.2) that Roxin's original work defined GDS via
   the attainability correspondence. The software defines GDS via the
   composition algebra instead. These are equivalent starting points that
   lead to different tooling.

3. **Convexity requirements on C(x, t; g)** -- The paper's existence theorem
   (Theorem 3.6) requires convexity. Many real systems (discrete decisions,
   combinatorial action spaces) violate this. The software should not impose
   convexity as a requirement -- it should report when convexity holds
   (as metadata) and note when existence theorems apply.

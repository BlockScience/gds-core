# GDS Architecture

> Living architecture document for contributors building new semantic layers or DSLs on the GDS protocol.

---

## 1. Architectural Principles

Five principles govern the design of the GDS ecosystem:

**Composition is syntactic and fundamental.**
The four operators (`>>`, `|`, `.feedback()`, `.loop()`) are structural — they assemble block trees without knowing what the blocks *mean*. No operator requires domain knowledge. This is the protocol layer.

**Semantics are plural and layered.**
The same composition tree can mean different things depending on the semantic interpretation. GDS interprets `>>` as "policy feeds mechanism"; OGS interprets it as "observation feeds decision". The protocol does not choose between them — it provides the shared syntax that both interpretations compose over.

**Simulation is domain-local.**
The protocol provides no execution semantics. Each semantic layer defines its own execution model (discrete-time dynamics for GDS, equilibrium computation for OGS, continuous integration for stock-flow). The protocol never runs a model — it only structures one.

**Canonical projections enable future unification.**
Each semantic layer can define a canonical projection that extracts its normal form from a specification. GDS projects to `h = f . g` (state transition as policy composed with mechanism). OGS will project to Nash equilibrium conditions. These projections are pure functions of the specification — always derivable, never authoritative. Whether they are related by a natural transformation is an open research question.

**Scope: causal block-diagram formalisms with uniform time semantics.**
The algebra covers systems where information flows directionally through blocks, time advances uniformly, and composition is expressed as block wiring. This includes dynamical systems, game theory, control systems, stock-flow, signal processing, compartmental models, and queueing networks. It does not cover acausal formalisms, hybrid automata, or multi-rate systems (see [Section 5](#5-scope-boundary)).

---

## 2. Layer Definitions

The ecosystem is organized into five layers. Each layer has explicit ownership (what it provides) and prohibitions (what it must not introduce).

### Layer 0 — Composition Core (the protocol)

The domain-neutral engine. Everything here works without knowing whether you're building a dynamical system, a game, or a stock-flow model.

**Owns:**
- `Block` (abstract), `AtomicBlock` (leaf base class)
- `Interface` (4-slot: `forward_in`, `forward_out`, `backward_in`, `backward_out`)
- `Port` (named, with `type_tokens: frozenset[str]`)
- 4 sealed composition operators: `StackComposition` (`>>`), `ParallelComposition` (`|`), `FeedbackLoop` (`.feedback()`), `TemporalLoop` (`.loop()`)
- `flatten()` — DFS traversal producing `list[AtomicBlock]`
- Token-based structural matching: `tokenize()`, `tokens_overlap()`, `tokens_subset()`
- `compile_system()` — 3-stage compiler: flatten, wire, hierarchy
- Auto-wiring for `>>` via token overlap on `forward_out` / `forward_in`
- Structural IR: `SystemIR`, `BlockIR`, `WiringIR`, `HierarchyNodeIR`
- `FlowDirection` (COVARIANT / CONTRAVARIANT), `CompositionType` (SEQUENTIAL / PARALLEL / FEEDBACK / TEMPORAL)
- Generic verification checks G-001 through G-006 (operate on `SystemIR`)
- `Wiring` (frozen dataclass for explicit connections)
- `Tagged` mixin (inert metadata, stripped at compile time)

**Prohibits:**
- State, time, dynamics, equilibrium, utility — no domain semantics
- No execution or simulation of any kind
- No domain-specific types, enums, or vocabulary
- No knowledge of what blocks *mean* — only how they *connect*

**Key files:**
```
packages/gds-framework/gds/blocks/base.py        # Block, AtomicBlock
packages/gds-framework/gds/blocks/composition.py  # 4 sealed operators, Wiring
packages/gds-framework/gds/types/interface.py      # Interface, Port
packages/gds-framework/gds/types/tokens.py         # tokenize, tokens_overlap, tokens_subset
packages/gds-framework/gds/compiler/compile.py     # compile_system
packages/gds-framework/gds/ir/models.py            # SystemIR, BlockIR, WiringIR, HierarchyNodeIR
packages/gds-framework/gds/verification/generic_checks.py  # G-001..G-006
```

### Layer 1 — Semantic Interpretations

Each domain defines what composition *means*. A semantic interpretation fills out the [Semantic Layer Contract](#4-the-semantic-layer-contract) — it assigns domain meaning to every operator and defines validation rules.

**Owns (per interpretation):**
- Domain block subclasses (subclass `AtomicBlock` only, never operators)
- Domain IR types (extend `BlockIR`/`WiringIR` or define parallel types)
- Domain verification checks
- `to_system_ir()` projection — bridge from domain IR to protocol `SystemIR`
- Canonical projection (recommended) — domain normal form

**Current implementations:**

| Interpretation | Block base | IR type | Checks | Canonical form |
|---|---|---|---|---|
| **GDS dynamics** | `BoundaryAction`, `Policy`, `Mechanism`, `ControlAction` (roles) | Uses `BlockIR` directly | SC-001..SC-007 (on `GDSSpec`) | `CanonicalGDS` via `project_canonical()` |
| **OGS game theory** | `OpenGame` (via `DomainBlock`) → 6 atomic game types | `OpenGameIR`, `FlowIR`, `PatternIR` | T-001..T-006, S-001..S-007 (on `PatternIR`) | Not yet implemented |

**Key contract:** Each semantic interpretation must answer the seven questions in [Section 4](#4-the-semantic-layer-contract).

**Key files — GDS semantics:**
```
packages/gds-framework/gds/spec.py             # GDSSpec registry
packages/gds-framework/gds/canonical.py         # CanonicalGDS, project_canonical()
packages/gds-framework/gds/blocks/roles.py      # BoundaryAction, Policy, Mechanism, ControlAction
packages/gds-framework/gds/verification/spec_checks.py  # SC-001..SC-007
```

**Key files — OGS semantics:**
```
packages/gds-games/ogs/dsl/base.py       # OpenGame(DomainBlock)
packages/gds-games/ogs/dsl/games.py      # 6 atomic game types
packages/gds-games/ogs/dsl/types.py      # Signature(Interface), GameType, FlowType
packages/gds-games/ogs/ir/models.py      # PatternIR, OpenGameIR, FlowIR, to_system_ir()
packages/gds-games/ogs/dsl/compile.py    # compile_to_ir()
packages/gds-games/ogs/verification/     # T-001..T-006, S-001..S-007
```

### Layer 2 — DSLs (domain grammars)

DSLs restrict and sugar the semantic layer. They provide convenience constructors, domain vocabulary, and registration patterns that make the semantic layer ergonomic for model authors.

**Owns:**
- Convenience constructors and factory functions
- Domain vocabulary (naming conventions, enums)
- Specification registries (`GDSSpec`, `Pattern`)
- Helper functions for common patterns (`port()`, `interface()`, `typedef()`, `entity()`, `space()`)
- Domain-specific composition extensions (e.g., `.corecursive()` on `OpenGame`)

**Current implementations:**

| DSL | Registry | Key helpers |
|---|---|---|
| **gds-framework GDS layer** | `GDSSpec` (register_type/space/entity/block/wiring/parameter, `.collect()`) | `typedef()`, `entity()`, `space()`, `port()`, `interface()` from `gds/__init__.py` |
| **gds-games OGS layer** | `Pattern` (groups games + flows + metadata) | `Signature(x=, y=, r=, s=)`, `reactive_decision_agent()`, library factories |

### Layer 3 — Models (concrete instantiations)

Populated by users, not framework authors. Each model is a concrete system specification using a DSL from Layer 2.

**Current implementations:**
```
packages/gds-examples/control/thermostat/     # Thermostat control system (GDS)
packages/gds-examples/stockflow/sir_epidemic/  # SIR epidemic model (GDS)
packages/gds-examples/stockflow/lotka_volterra/# Lotka-Volterra predator-prey (GDS)
packages/gds-examples/games/insurance/         # Insurance game (OGS)
packages/gds-examples/games/prisoners_dilemma/ # Prisoner's Dilemma (OGS)
packages/gds-examples/games/crosswalk/         # Crosswalk game (OGS)
```

### Layer 4 — Projections & Views

Read-only transformations that extract information from Layer 0–2 artifacts. These never modify specifications — they only produce derived outputs.

**Structural views** (from `SystemIR`):
- `system_to_mermaid()` — flat block topology diagrams (`gds_viz/mermaid.py`)
- `hierarchy_to_mermaid()` — composition tree visualization

**Semantic views** (from `GDSSpec` / `PatternIR`):
- `project_canonical()` → `CanonicalGDS` — formal GDS decomposition
- `canonical_to_mermaid()` — visualize canonical structure (`gds_viz/canonical.py`)
- `traceability_matrix()` — entity-block traceability (`gds_viz/traceability.py`)
- Architecture views — domain-grouped diagrams (`gds_viz/architecture.py`)
- OGS reports — 7 Jinja2 Markdown templates (`ogs/reports/`)
- OGS diagrams — 6 Mermaid generators (`ogs/viz.py`)

**Key files:**
```
packages/gds-viz/gds_viz/mermaid.py         # system_to_mermaid (structural)
packages/gds-viz/gds_viz/canonical.py       # canonical_to_mermaid (semantic)
packages/gds-viz/gds_viz/architecture.py    # architecture diagrams
packages/gds-viz/gds_viz/traceability.py    # traceability matrix
packages/gds-games/ogs/viz.py               # OGS Mermaid generators
packages/gds-games/ogs/reports/             # OGS Markdown report generators
```

---

## 3. The Structural Pipeline

The compiler transforms a Block composition tree into flat `SystemIR`. It performs three independent traversals:

### Current Implementation

```
compile_system(name, root, block_compiler, composition_type, source)
    │
    ├── root.flatten()              → list[AtomicBlock]
    │   └── block_compiler(b)       → list[BlockIR]
    │
    ├── _extract_wirings(root)      → list[WiringIR]
    │   └── _walk_wirings(block)    # recursive DFS
    │       ├── StackComposition    → explicit wiring OR auto-wire via token overlap
    │       ├── ParallelComposition → recurse only (no wiring)
    │       ├── FeedbackLoop        → mark is_feedback=True
    │       └── TemporalLoop        → mark is_temporal=True
    │
    └── _extract_hierarchy(root)    → HierarchyNodeIR
        └── flatten_sequential_chains()  # collapse single-child >> chains
```

### Compiler Extension Point

Domain packages provide a `block_compiler: Callable[[AtomicBlock], BlockIR]` callback. This is how Layer 1 injects its vocabulary into the structural pipeline:

- **GDS default:** extracts name + interface signature → `BlockIR`
- **OGS:** maps `AtomicGame` → `OpenGameIR` (game_type, logic, color_code, tags)

The compiler never interprets the block — it calls the callback and trusts the result.

### How OGS Reuses the Pipeline

OGS (`ogs/dsl/compile.py`) reuses the decomposed pipeline stages with domain-specific callbacks:

- **`flatten_blocks(pattern.game, _compile_game)`** — produces `list[OpenGameIR]`
- **`extract_wirings(pattern.game, _ogs_wiring_emitter)`** — produces `list[FlowIR]` with `FlowType` inference (observation, choice_observation, utility_coutility)
- **Hierarchy extraction stays OGS-specific** — GDS produces `TEMPORAL` for `TemporalLoop`; OGS needs `CORECURSIVE` for `CorecursiveLoop`, so it keeps its own `_extract_hierarchy`
- **Input-to-flow generation** — `PatternInput` objects generate `FlowIR` entries (OGS-specific, not part of the pipeline)

### Pipeline Decomposition

The structural pipeline is decomposed into composable stages with generic callbacks:

```python
# Layer 0 owns traversal, Layer 1 owns vocabulary

def flatten_blocks(root, block_compiler) -> list[B]:
    """DFS flatten + per-block compilation. Generic over return type B."""

def extract_wirings(root, wiring_emitter) -> list[W]:
    """DFS wiring extraction + per-wiring emission. Generic over return type W."""

def extract_hierarchy(root) -> HierarchyNodeIR:
    """Hierarchy tree extraction + chain flattening. Always returns GDS HierarchyNodeIR."""

def compile_system(name, root, ..., inputs=None) -> SystemIR:
    """Convenience assembly: calls the above three, produces SystemIR."""
```

**Design principles:**

- **Layer 0 owns traversal, Layer 1 owns vocabulary.** The DFS walk over the composition tree is protocol logic. The transformation of each node into domain IR is Layer 1 logic. These are cleanly separated.
- **Generic return types on pipeline stages.** `flatten_blocks` returns `list[B]` where `B` is determined by the `block_compiler`. This lets OGS produce `list[OpenGameIR]` directly.
- **Emitters cannot inject new edges or modify traversal.** A `wiring_emitter` callback transforms the wiring at each node, but it cannot change which nodes are visited or add edges between nodes the tree doesn't connect.
- **Default emitters preserve current behavior exactly.** Passing `None` for the callbacks produces identical output to calling `compile_system()` with defaults.

**Key types:**

| Type | Purpose |
|---|---|
| `StructuralWiring` | Protocol-internal frozen dataclass for wiring data before emission |
| `WiringOrigin` | Sealed enum: `AUTO`, `EXPLICIT`, `FEEDBACK`, `TEMPORAL` |
| `WiringIR.category` | Open string field, default `"dataflow"`, protocol only interprets `"dataflow"` |
| `InputIR` | Typed external input: `name` + `metadata` bag. Domain packages map richer fields into `metadata` |
| `sanitize_id` | Canonical name-to-identifier function, used by hierarchy extraction and Mermaid rendering |

### Layer 0 Stabilization

The following gaps between the architecture document and the codebase have been closed:

1. **Typed `InputIR`** — `SystemIR.inputs` is `list[InputIR]` (was `list[dict[str, Any]]`). OGS projects its richer `InputIR` (with `input_type`, `schema_hint`, `shape`) into the metadata bag. `compile_system()` accepts an optional `inputs` parameter; Layer 0 never infers inputs.

2. **Real G-003 direction consistency** — replaced the stub (always-pass INFO) with two validations: flag consistency (COVARIANT+is_feedback and CONTRAVARIANT+is_temporal contradictions) and contravariant port-slot matching via `tokens_subset` against backward_out/backward_in signature slots.

3. **Unified `sanitize_id`** — single canonical definition in `gds.ir.models.sanitize_id()`, replacing 5 duplicated copies across gds-framework and gds-games. Includes a leading-digit guard for Mermaid compatibility.

With these changes, Layer 0 is formally consistent with the architecture document and ready for new DSL development.

---

## 4. The Semantic Layer Contract

Every semantic interpretation must answer these questions. Together, they fully specify how a domain maps onto the composition algebra.

### The Seven Questions

| # | Question | What it determines |
|---|---|---|
| 1 | **Block semantics** — what does a block represent? | Vocabulary of atomic components |
| 2 | **Sequential (>>)** — what operation is induced? | Forward information flow meaning |
| 3 | **Parallel (\|)** — what is the product structure? | Independence / concurrency model |
| 4 | **Feedback (.feedback())** — what fixed-point or closure? | Within-timestep backward flow |
| 5 | **Temporal (.loop())** — what cross-step semantics? | State persistence / iteration |
| 6 | **Execution model** — static? discrete-time? continuous? equilibrium? | How the specification is *run* |
| 7 | **Validation layer** — what domain invariants? What checks? | Correctness criteria |
| 8 | **Canonical projection** (recommended) — what is the domain normal form? | Mathematical structure extraction |

### Worked Example: GDS (Generalized Dynamical Systems)

| # | Answer |
|---|---|
| 1 | Blocks are typed components of a state transition: `BoundaryAction` (exogenous input U), `ControlAction` (endogenous feedback), `Policy` (decision mapping g), `Mechanism` (state update f). |
| 2 | `>>` chains policy into mechanism: `g` feeds `f`, yielding `h = f . g`. Token overlap ensures type-compatible connections. |
| 3 | `\|` composes independent subsystems. No shared wiring. Product of state spaces. |
| 4 | `.feedback()` closes a backward loop within one timestep — backward_out signals feed backward_in. Direction is CONTRAVARIANT. |
| 5 | `.loop()` carries state forward across timesteps — forward_out at t feeds forward_in at t+1. Direction must be COVARIANT. This is the discrete-time state evolution operator. |
| 6 | Discrete-time dynamical system: `x(t+1) = h_θ(x(t), u(t))`. Static specification — GDS defines structure, not a simulator. |
| 7 | SC-001 completeness (all entities have update paths), SC-002 determinism (single writer per variable), SC-003 reachability, SC-004 type safety (wire space references), SC-005 parameter references, SC-006 canonical wellformedness (mechanisms exist), SC-007 canonical wellformedness (state space non-empty). Operate on `GDSSpec`. |
| 8 | `project_canonical(spec) → CanonicalGDS`: extracts X (state), U (input), D (decisions), Θ (parameters), g (policy map), f (state transition). Pure function, always derivable. |

### Worked Example: OGS (Open Game Specification)

| # | Answer |
|---|---|
| 1 | Blocks are open games with `Signature(x, y, r, s)` — observation inputs (X), decision outputs (Y), utility inputs (R), coutility outputs (S). Six atomic types: Decision, FunctionCovariant, FunctionContravariant, Deletion, Duplication, Counit. |
| 2 | `>>` passes observations forward and utilities backward. Y of the first game feeds X of the second (covariant); R of the second feeds S of the first (contravariant). |
| 3 | `\|` is the monoidal product — independent games with separate observation/utility channels. |
| 4 | `.feedback()` closes a contravariant S→R loop within one round — utility coutility feedback. Used for agent best-response fixed points. |
| 5 | `.corecursive()` (maps to `.loop()` / TemporalLoop at protocol level) carries Y→X forward across rounds — covariant temporal iteration. Used for repeated games and dynamic mechanisms. |
| 6 | Equilibrium computation. The specification defines the game structure; execution means finding Nash equilibria or computing best responses. Not simulation. |
| 7 | T-001..T-006 (type checks: domain-codomain matching, signature completeness, flow type consistency, input resolution, unused inputs, dangling flows). S-001..S-007 (structural: sequential compatibility, parallel independence, feedback compatibility, acyclicity, decision space validation, corecursive wiring, initialization completeness). All operate on `PatternIR`. Plus optional delegation to GDS G-001..G-006 via `to_system_ir()`. |
| 8 | Not yet implemented. Expected: extraction of strategy profiles, payoff structure, and equilibrium conditions. |

### Template for New Semantic Layers

When building a new DSL (e.g., `gds-stockflow`, `gds-control`), fill out this template:

```markdown
## [Domain Name] Semantic Layer

### 1. Block semantics
What does a block represent in this domain?
What are the atomic block types?

### 2. Sequential composition (>>)
What does "A then B" mean? What flows forward?

### 3. Parallel composition (|)
What does "A alongside B" mean? What is the independence guarantee?

### 4. Feedback (.feedback())
What backward loop is being closed? Within what time frame?

### 5. Temporal loop (.loop())
What state persists across steps? What is a "step"?

### 6. Execution model
How is this specification *run*? Static analysis? Simulation? Optimization?

### 7. Validation layer
What domain invariants must hold? List specific checks.

### 8. Canonical projection (recommended)
What is the domain normal form? What mathematical structure does it extract?
```

---

## 5. Scope Boundary

### In Scope

The composition algebra covers **causal block-diagram formalisms** — systems where:
- Information flows directionally through blocks (ports have direction)
- Time advances uniformly (one global clock or no time at all)
- Composition is expressed as block wiring (connectivity, not constraint solving)

This includes:

| Formalism | How it maps |
|---|---|
| Dynamical systems | Blocks = transition components, `>>` = function composition, `.loop()` = state evolution |
| Compositional game theory | Blocks = open games, `>>` = sequential play, `\|` = independent games, `.feedback()` = best response |
| Control systems | Blocks = plant/controller/sensor, `>>` = signal flow, `.feedback()` = closed-loop control |
| Stock-flow diagrams | Blocks = stocks/flows/auxiliaries, `>>` = rate computation, `.loop()` = accumulation |
| Signal processing | Blocks = filters/transforms, `>>` = pipeline, `\|` = multichannel |
| Compartmental models | Blocks = compartments/transfers, `>>` = flow between compartments |
| Queueing networks | Blocks = queues/servers, `>>` = routing, `\|` = parallel servers |
| Bayesian networks | Blocks = conditional distributions, `>>` = conditional dependency chain |

### Out of Scope

These formalisms require capabilities the protocol does not provide. Attempting to encode them in the current algebra leads to impedance mismatches, workarounds, or incorrect models.

**Acausal physical modeling (bond graphs, Modelica)**
Requires conjugate effort-flow port pairs where the distinction between input and output is determined by the solver, not the modeler. The protocol's directional ports (`forward_in`/`forward_out`) assume the modeler assigns direction.

**Hybrid automata with guarded transitions**
Requires conditional wiring — edges that exist only when a guard predicate evaluates to true. The protocol's wirings are unconditional; there is no mechanism for evaluable guards on edges.

**Multi-rate cyber-physical systems**
Requires clock or rate annotations on temporal wiring — different blocks stepping at different frequencies. The protocol's `.loop()` assumes uniform time advancement.

**Higher-order block transformations**
Requires `Block → Block` in the type system — blocks that take other blocks as arguments and return new blocks. The protocol's type system is first-order: blocks contain other blocks only through composition operators.

---

## 6. Deferred Enhancements

These are extensions that have been considered and deliberately deferred. Each should be implemented only when a concrete DSL demonstrates the need.

**Interface reduction on `>>`**
Currently, `>>` concatenates all ports from both operands into the composite interface. An interface reduction would hide internal ports that are "consumed" by the sequential wiring, exposing only the true external boundary. Deferred because: (a) it changes the semantics of `interface` on composed blocks, which many downstream tools depend on, and (b) no current DSL requires it for correctness.

**Port-level annotations (units, physical domain)**
Ports could carry metadata beyond tokens — physical units (`m/s`, `kg`), domain tags (`electrical`, `thermal`). Deferred because: the token system handles current matching needs, and annotations would complicate the matching algebra without a concrete use case.

**Token subtype hierarchy**
Currently, tokens are flat sets — `{"temperature"}` is just a set of one string. A hierarchy (e.g., `temperature < thermal < physical`) would enable more precise matching. Deferred because: no current model requires hierarchical type refinement at the structural level.

**Directional token matching**
Currently, auto-wiring matches `forward_out` tokens against `forward_in` tokens with no directionality in the tokens themselves. Directional tokens would distinguish "this port *produces* temperature" from "this port *consumes* temperature". Deferred because: the port slot (forward_out vs forward_in) already encodes direction.

**Fan-out as protocol primitive**
Currently, if a single output port must feed multiple downstream blocks, the domain layer handles duplication (OGS has a Duplication game type). Elevating fan-out to the protocol would make it universally available. Deferred because: it works correctly at the domain level, and protocol-level fan-out raises questions about copy semantics that are domain-dependent.

**Algebraic law enforcement**
The composition operators satisfy algebraic laws (associativity of `>>` and `|`, identity elements). The protocol could normalize trees to canonical forms — e.g., `(a >> b) >> c` ≡ `a >> (b >> c)`. Deferred because: normalization changes tree structure, which affects hierarchy visualization and debugging. Laws should be stated and proven, but not enforced by default.

---

## 7. Long-Term Research Directions

These are open questions at the boundary of engineering and theory.

**Canonical projection unification.**
GDS projects specifications to `h = f . g`. OGS will project to equilibrium structure. Stock-flow will project to system dynamics equations. Are these projections related by a natural transformation? If the composition algebra is a free category and each semantic layer is a functor into its target category, then the canonical projections may be components of natural transformations between these functors. This would enable principled cross-domain translation.

**Algebraic equivalence laws.**
What are the precise laws of the composition core? Candidates:
- Associativity: `(a >> b) >> c ≡ a >> (b >> c)`, `(a | b) | c ≡ a | (b | c)`
- Identity: `id >> a ≡ a ≡ a >> id`
- Interchange: `(a >> b) | (c >> d) ≡ (a | c) >> (b | d)` (when types align)
- Feedback absorption: conditions under which `.feedback()` distributes over `>>`

Formalizing these laws enables equational reasoning about system structure — proving that two different compositions compute the same thing without running them.

**Cross-domain semantic embeddings.**
Can a game-theoretic specification be faithfully embedded in the dynamical systems semantics? If an OGS pattern has a `to_system_ir()` projection, and GDS has `project_canonical()`, then composing them gives a path from game to dynamical system. Under what conditions is this faithful? When does it preserve equilibria?

**Formal structural reasoning over SystemIR.**
SystemIR is a directed graph with typed edges. Standard graph-theoretic reasoning (reachability, cuts, flows) already applies — the generic verification checks use it. Can we go further? Model checking over SystemIR, automated invariant generation, compositional refinement proofs?

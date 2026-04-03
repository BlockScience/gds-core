# Verification Check Specifications

This document defines the formal property statement for each of the 15 core
verification checks in `gds-framework`. Every check is stated as a predicate on
the IR or specification model so that `verify()` results can be interpreted
unambiguously and traced to the composition algebra or canonical form.

## Two-Layer Verification Architecture

GDS verification is split across two independent layers that mirror the
framework's two-layer design:

**Layer 0 -- Structural Checks (G-001 through G-006)** operate on `SystemIR`,
the flat intermediate representation produced by `compile_system()`. They validate
properties of the composition algebra: port compatibility, interface completeness,
direction consistency, referential integrity, sequential type safety, and
acyclicity. These checks know nothing about GDS semantics -- they enforce the
well-definedness of the block graph as a mathematical object.

**Layer 1 -- Semantic Checks (SC-001 through SC-009)** operate on `GDSSpec`,
the specification-level registry. They validate properties that require knowledge
of entities, state variables, block roles, parameter declarations, admissibility
constraints, transition signatures, and the canonical decomposition
`h = f . g`. These checks ensure that the specification is internally consistent
and that the canonical form is non-degenerate.

The two layers are independent: you can run structural checks without building a
`GDSSpec`, and you can run semantic checks without compiling to `SystemIR`. In
practice, a well-formed model passes both.

## Notation

Throughout this document:

| Symbol | Meaning |
|--------|---------|
| `B` | Set of blocks in `SystemIR` or `GDSSpec` |
| `W` | Set of wirings |
| `E` | Set of entities |
| `X` | State space (union of all entity variables) |
| `tokens(s)` | Token decomposition of port name string `s` |
| `sig(b)` | 4-tuple signature `(forward_in, forward_out, backward_in, backward_out)` of block `b` |
| `h = f . g` | Canonical GDS decomposition: `g` is the observation/policy map, `f` is the state transition |
| `M` | Set of Mechanism blocks |
| `P` | Set of registered parameters in `ParameterSchema` |

## Summary Table

| Code | Name | Layer | Severity | Operates on | Property |
|------|------|-------|----------|-------------|----------|
| G-001 | Domain/Codomain Matching | 0 | ERROR | `SystemIR` | Covariant wiring labels are token-subsets of source output or target input |
| G-002 | Signature Completeness | 0 | ERROR | `SystemIR` | Every block has non-degenerate interface (input and output) |
| G-003 | Direction Consistency | 0 | ERROR | `SystemIR` | No flag contradictions; contravariant port-slot matching |
| G-004 | Dangling Wirings | 0 | ERROR | `SystemIR` | Wiring endpoints are referentially valid |
| G-005 | Sequential Type Compatibility | 0 | ERROR | `SystemIR` | Stack wiring labels match BOTH source output AND target input |
| G-006 | Covariant Acyclicity | 0 | ERROR | `SystemIR` | Forward flow graph is a DAG |
| SC-001 | Completeness | 1 | WARNING | `GDSSpec` | Every state variable is updated by at least one mechanism |
| SC-002 | Determinism | 1 | ERROR | `GDSSpec` | No variable updated by multiple mechanisms in same wiring |
| SC-003 | Reachability | 1 | WARNING | `GDSSpec` | Signal path exists between two named blocks |
| SC-004 | Type Safety | 1 | ERROR | `GDSSpec` | Wire space references resolve to registered spaces |
| SC-005 | Parameter References | 1 | ERROR | `GDSSpec` | Block `params_used` match registered parameter names |
| SC-006 | Canonical Wellformedness (f) | 1 | WARNING | `GDSSpec` | At least one mechanism exists |
| SC-007 | Canonical Wellformedness (X) | 1 | WARNING | `GDSSpec` | At least one state variable exists |
| SC-008 | Admissibility References | 1 | ERROR | `GDSSpec` | Admissibility constraints reference valid blocks and variables |
| SC-009 | Transition Reads | 1 | ERROR | `GDSSpec` | Transition signatures reference valid mechanisms and variables |

---

## Layer 0 -- Structural Checks (G-001 through G-006)

These checks operate on `SystemIR` and validate the composition algebra's
structural well-definedness. They are run automatically by `verify(system)`.

---

### G-001 -- Domain/Codomain Matching

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
Let `W_cov = {w in W : w.direction = COVARIANT}`. For every `w in W_cov` where
both `w.source` and `w.target` are in `B`:

```
tokens(w.label) <= tokens(sig(w.source).forward_out)
  OR tokens(w.label) <= tokens(sig(w.target).forward_in)
```

where `<=` denotes the token-subset relation. Additionally, both
`sig(w.source).forward_out` and `sig(w.target).forward_in` must be non-empty
(otherwise the wiring cannot be verified).

**Invariant Enforced:**
Type safety in the covariant (forward) channel of the token algebra. In the
composition `A >> B`, signals flowing from A to B must reference ports that
actually exist on at least one side. This is a necessary condition for the
composition `A ; B` to be well-typed in the block algebra.

**Failure Semantics:**
A MISMATCH means the wiring label references tokens that exist on neither the
source's output nor the target's input. The composition is structurally
ill-typed: signals are routed to non-existent ports. An empty-port failure
(source or target has no forward ports) means the block is structurally
incapable of participating in covariant flow.

**Soundness Conditions:**
A pass guarantees that every covariant wiring's label is consistent with at
least one endpoint's port declaration. This is a necessary but not sufficient
condition for composition well-typedness -- G-005 provides the stronger
bilateral condition for sequential composition. G-001 does not check
contravariant wirings (see G-003).

**Algorithm:**
For each covariant wiring, retrieve both endpoint signatures from a
`{block.name: block.signature}` lookup. Apply `tokens_subset(label, port)` to
source `forward_out` and target `forward_in`. Report MISMATCH if neither
subset relation holds.

---

### G-002 -- Signature Completeness

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
For every block `b in B`:

```
has_output(b) = (sig(b).forward_out != "" OR sig(b).backward_out != "")
has_input(b)  = (sig(b).forward_in != "" OR sig(b).backward_in != "")
```

If `b.block_type = "boundary"` (BoundaryAction):

```
has_output(b) = True
```

Otherwise:

```
has_input(b) AND has_output(b) = True
```

**Invariant Enforced:**
Non-degeneracy of block interfaces. A block with no outputs cannot contribute
signals to any downstream composition. A block with no inputs (unless it is a
BoundaryAction, which models exogenous signals) cannot receive signals and is
structurally isolated. This ensures every block participates meaningfully in
the composition graph.

**Failure Semantics:**
A block with empty input and output is completely isolated -- it cannot appear
in any valid composition. The block algebra requires every composable element to
have at least one port on each side (with BoundaryAction exempted from the
input requirement by definition).

**Soundness Conditions:**
A pass guarantees every block has at least a minimal interface. Note that
BoundaryActions legitimately have no inputs (they inject exogenous signals),
and terminal Mechanisms may have no forward outputs (they only write state).
The BoundaryAction exemption is built into the check.

**Algorithm:**
For each block, inspect all four signature slots. Track whether at least one
input slot and one output slot is non-empty. Apply the BoundaryAction exemption
based on `block_type == "boundary"`.

---

### G-003 -- Direction Consistency

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
Two sub-properties:

**(A) Flag Consistency.** For every wiring `w in W`:

```
NOT (w.direction = COVARIANT AND w.is_feedback)
NOT (w.direction = CONTRAVARIANT AND w.is_temporal)
```

The first conjunction is a contradiction because feedback flow is inherently
contravariant (backward within a timestep). The second is a contradiction
because temporal flow is inherently covariant (forward across timesteps).

**(B) Contravariant Port-Slot Matching.** For every `w in W` where
`w.direction = CONTRAVARIANT` and both endpoints are blocks:

```
(sig(w.source).backward_out != "" OR sig(w.target).backward_in != "")
AND
(tokens(w.label) <= tokens(sig(w.source).backward_out)
  OR tokens(w.label) <= tokens(sig(w.target).backward_in))
```

**Invariant Enforced:**
Bidirectional flow discipline. The composition algebra distinguishes covariant
(forward) and contravariant (backward) channels. G-003 ensures that (a) the
direction/feedback/temporal flags are mutually consistent, and (b) contravariant
wirings are token-compatible with the backward ports, completing the type-safety
story that G-001 begins for the covariant side. Together, G-001 and G-003
establish that every wiring is compatible with the appropriate channel of its
endpoint signatures.

**Failure Semantics:**
A flag contradiction means the wiring's metadata is internally inconsistent --
it cannot be both covariant and feedback, or both contravariant and temporal.
A contravariant port mismatch means backward signals are routed to non-existent
backward ports. Both are structural errors that make the composition algebra
ill-defined.

**Soundness Conditions:**
A pass on (A) guarantees no flag contradictions. A pass on (B) guarantees
contravariant wirings match backward port declarations. Together with G-001,
this covers all four directional port-matching cases. Wirings with non-block
endpoints (e.g., InputIR) are skipped -- G-004 handles dangling references.

**Algorithm:**
For each wiring: (A) check the two forbidden flag combinations; (B) if
contravariant and both endpoints are blocks, verify that at least one backward
port is non-empty, then apply `tokens_subset` to backward_out and backward_in.

---

### G-004 -- Dangling Wirings

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
Let `N = {b.name : b in B} UNION {i.name : i in inputs}` be the set of all
recognized endpoint names. For every wiring `w in W`:

```
w.source in N AND w.target in N
```

**Invariant Enforced:**
Referential integrity of the wiring graph. Every wiring must connect two known
endpoints. A dangling reference (source or target not in the block/input set)
means the wiring points to a non-existent component -- either a typo, a missing
block, or an incomplete composition.

**Failure Semantics:**
A dangling wiring makes the system graph structurally incomplete. The
composition cannot be evaluated because at least one endpoint does not exist.
This is a hard structural error.

**Soundness Conditions:**
A pass guarantees all wiring endpoints resolve to known blocks or inputs. This
check does not validate that the connected blocks are type-compatible (G-001
and G-003 handle that) or that the graph is connected (SC-003 handles that).

**Algorithm:**
Build the set of known names from `system.blocks` and `system.inputs`. For
each wiring, check membership of `source` and `target` in this set.

---

### G-005 -- Sequential Type Compatibility

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
Let `W_seq = {w in W : w.direction = COVARIANT, NOT w.is_temporal,
w.source in B, w.target in B}`. For every `w in W_seq` where both
`sig(w.source).forward_out != ""` and `sig(w.target).forward_in != ""`:

```
tokens(w.label) <= tokens(sig(w.source).forward_out)
  AND tokens(w.label) <= tokens(sig(w.target).forward_in)
```

**Invariant Enforced:**
Bilateral type safety for sequential (stack) composition. While G-001 requires
the wiring label to match *at least one* side, G-005 requires it to match
*both* sides. This is the stronger condition needed for sequential composition
`A >> B` to be well-typed: the output of A and the input of B must agree on
the signal being passed. This directly ensures that in the composition
`A ; B`, the codomain of A is compatible with the domain of B.

**Failure Semantics:**
A type mismatch means the sequential composition has a type gap: A produces a
signal that B does not expect (or vice versa). The composition `A ; B` is
ill-typed. Unlike G-001, which permits unilateral matching, G-005 requires
bilateral agreement. This is the key check for ensuring the `>>` operator is
sound.

**Soundness Conditions:**
A pass guarantees bilateral token-subset compatibility for all non-temporal
covariant wirings between blocks. Wirings to InputIR endpoints are excluded
(they represent system-level inputs, not block-to-block compositions). Temporal
wirings are excluded (they are cross-timestep, not within-timestep sequential).
If either endpoint has an empty forward port, the wiring is silently skipped
(G-001 catches this case).

**Algorithm:**
For each qualifying wiring, apply `tokens_subset(label, src_out)` and
`tokens_subset(label, tgt_in)`. Both must hold for compatibility. Report type
mismatch if either fails.

---

### G-006 -- Covariant Acyclicity

**Type:** Structural (Layer 0)
**Severity:** ERROR
**Operates on:** SystemIR

**Property Statement:**
Let `G_cov = (V, E_cov)` where:

```
V = {b.name : b in B}
E_cov = {(w.source, w.target) : w in W,
          w.direction = COVARIANT,
          NOT w.is_temporal}
```

`G_cov` is acyclic (a directed acyclic graph).

**Invariant Enforced:**
Well-definedness of the within-timestep computation order. In the canonical
form `h = f . g`, the composition must define a function, not an implicit
equation. A cycle in the covariant flow graph means Block A depends on Block B
which depends on Block A within the same timestep -- an algebraic loop with no
well-defined evaluation order. Temporal wirings (which introduce delay) and
contravariant wirings (which flow backward by design) are excluded because they
do not create within-timestep algebraic dependencies.

**Failure Semantics:**
A cycle means the system has an algebraic loop: the canonical form `h = f . g`
cannot be evaluated as a function because the computation has circular
dependencies. The system requires a fixed-point solver or the cycle must be
broken by introducing temporal delay (`.loop()`). This is a critical structural
error.

**Soundness Conditions:**
A pass guarantees that the covariant, non-temporal flow graph admits a
topological ordering, which is necessary for `h = f . g` to be evaluated as a
sequential function composition. This does not guarantee that the temporal
dynamics are well-defined (that requires analysis of the full system including
temporal loops).

**Algorithm:**
Build an adjacency list from covariant, non-temporal wirings between blocks.
Run DFS-based cycle detection using three-color marking (WHITE/GRAY/BLACK). A
back edge (encounter of a GRAY node) indicates a cycle. Report the cycle path.

---

## Layer 1 -- Semantic Checks (SC-001 through SC-009)

These checks operate on `GDSSpec` and validate domain properties that require
knowledge of entities, block roles, parameters, and the canonical
decomposition. They are called individually, not through `verify()`.

---

### SC-001 -- Completeness

**Type:** Semantic (Layer 1)
**Severity:** WARNING
**Operates on:** GDSSpec

**Property Statement:**
Let `U = {(e, v) : m in M, (e, v) in m.updates}` be the set of all
(entity, variable) pairs updated by some mechanism. For every entity
`e in E` and every variable `v in e.variables`:

```
(e.name, v) in U
```

In other words: the mechanism update map is surjective onto the state variable
set. Every declared state variable has at least one mechanism that updates it.

**Invariant Enforced:**
Surjectivity of mechanism coverage onto the state space X. In the canonical
form `h = f . g`, the state transition function `f` must be defined on all of
X. An orphan variable (one never updated) means `f` is partial -- part of the
state space is unreachable by the dynamics. This is almost always a
specification error (a declared variable that was forgotten in the mechanism
wiring).

**Failure Semantics:**
An orphan state variable will never change from its initial value. The state
transition `f` does not cover it. If this is intentional (e.g., a constant
parameter encoded as state), the warning can be accepted. Otherwise, the
specification is incomplete.

**Soundness Conditions:**
A pass guarantees every declared state variable has at least one mechanism
listing it in `updates`. This does not verify that the mechanism's logic
actually modifies the variable at runtime -- only that the structural
declaration exists.

**Algorithm:**
Collect all `(entity, variable)` pairs from all Mechanism `.updates` fields
into a set. Iterate all entity variables and check membership.

---

### SC-002 -- Determinism

**Type:** Semantic (Layer 1)
**Severity:** ERROR
**Operates on:** GDSSpec

**Property Statement:**
For every wiring `w` in the spec and every (entity, variable) pair `(e, v)`:

```
|{m in w.block_names : m is Mechanism, (e, v) in m.updates}| <= 1
```

Within any single wiring (composition), at most one mechanism may declare an
update to a given state variable.

**Invariant Enforced:**
Functional determinism of state updates. In the canonical form `h = f . g`,
the state transition `f` must be a function (single-valued), not a
multi-valued relation. If two mechanisms in the same wiring both update the
same variable, the result is ambiguous -- the final state depends on
unspecified execution order. This makes `f` non-deterministic, which violates
the GDS requirement that `f: X -> X` is a well-defined function.

**Failure Semantics:**
A write conflict means the state transition for that variable is ambiguous.
Two mechanisms racing to update the same state variable within the same
composition produce an undefined result. The canonical form `f` is not a
function. This is a hard specification error.

**Soundness Conditions:**
A pass guarantees no write conflicts within any single wiring. This does not
prevent the same variable from being updated by different mechanisms in
different wirings (which is valid -- different compositions can have different
update paths). The check is scoped to individual wirings because each wiring
represents a single composition that executes as a unit.

**Algorithm:**
For each wiring, build a map from `(entity, variable)` to the list of
mechanisms that update it. Report any entry with more than one mechanism.

---

### SC-003 -- Reachability

**Type:** Semantic (Layer 1)
**Severity:** WARNING
**Operates on:** GDSSpec

**Property Statement:**
Given blocks `from_block` and `to_block`, let `G_wire = (V_wire, E_wire)` where:

```
V_wire = UNION({wire.source, wire.target} : wire in w.wires, w in spec.wirings)
E_wire = {(wire.source, wire.target) : wire in w.wires, w in spec.wirings}
```

There exists a directed path in `G_wire` from `from_block` to `to_block`.

**Invariant Enforced:**
Signal reachability in the wiring graph. Maps to the GDS attainability
correspondence: can a boundary input ultimately influence a state update?
Unreachable blocks indicate disconnected subgraphs in the composition, which
means the specification has structurally isolated components.

**Failure Semantics:**
An unreachable pair means signals from `from_block` cannot influence
`to_block` through any chain of wirings. This may indicate a missing wiring,
a disconnected subgraph, or an intentional isolation boundary. WARNING
severity because some disconnection may be by design (independent subsystems).

**Soundness Conditions:**
A pass guarantees the existence of a directed path. This is a structural
reachability property -- it does not guarantee that signals are actually
propagated at runtime (that depends on block behavior). The check uses the
`Wire` declarations in `SpecWiring`, not the compiled `SystemIR` wirings.
Unlike other semantic checks, SC-003 requires explicit `from_block` and
`to_block` arguments and is not called automatically.

**Algorithm:**
Build an adjacency list from all `Wire` declarations across all `SpecWiring`
instances. Run BFS from `from_block`. Report whether `to_block` is visited.

---

### SC-004 -- Type Safety

**Type:** Semantic (Layer 1)
**Severity:** ERROR
**Operates on:** GDSSpec

**Property Statement:**
For every wiring `w` in the spec and every wire `wire in w.wires`:

```
wire.space != "" IMPLIES wire.space in spec.spaces
```

Every non-empty space reference on a wire must resolve to a registered Space
in the specification.

**Invariant Enforced:**
Referential integrity of space declarations on wiring channels. Spaces define
the typed data domains that signals carry between blocks. An unregistered
space means the data channel is undefined -- the system references a type
that does not exist. This is necessary for the spec to be self-consistent and
for downstream tools (simulation, analysis) that rely on space definitions.

**Failure Semantics:**
An unregistered space reference means the wire's data domain is undefined.
Downstream consumers (simulation bridges, OWL export) cannot resolve the
channel type. This is a hard specification error.

**Soundness Conditions:**
A pass guarantees all wire space references resolve to registered Spaces. This
check validates referential integrity only -- it does not verify that the
Space's TypeDef fields are compatible with the connected blocks' port types
(that would require cross-referencing the token-based and TypeDef-based type
systems, which is not currently implemented).

**Algorithm:**
For each wire in each wiring, if `wire.space` is non-empty, check membership
in `spec.spaces`. Report any unregistered reference.

---

### SC-005 -- Parameter References

**Type:** Semantic (Layer 1)
**Severity:** ERROR
**Operates on:** GDSSpec

**Property Statement:**
Let `P_names = spec.parameter_schema.names()` be the set of registered parameter
names. For every block `b in B` that implements `HasParams`:

```
{p : p in b.params_used} <= P_names
```

Every parameter referenced by a block must be registered in the spec's
parameter schema.

**Invariant Enforced:**
Referential integrity of parameter declarations. Parameters (Theta) are
structural metadata that parameterize block behavior. If a block declares
that it uses a parameter but that parameter is not registered, downstream
tools (PSUU, simulation) cannot resolve the reference. In the canonical form,
parameters condition the transition function `f(x; theta)` -- an unresolved
parameter means `theta` is partially undefined.

**Failure Semantics:**
An unresolved parameter reference means the block uses a parameter that does
not exist in the spec. The parameter space Theta is incomplete. This is a hard
specification error that will cause failures in any tool that tries to bind
parameter values.

**Soundness Conditions:**
A pass guarantees all `params_used` entries resolve to registered
`ParameterDef` objects. This does not validate that the parameter's TypeDef
is compatible with how the block uses it (runtime concern, not structural).

**Algorithm:**
Retrieve registered parameter names from `spec.parameter_schema`. For each
block implementing `HasParams`, check that every entry in `params_used` is in
the registered set.

---

### SC-006 -- Canonical Wellformedness (f)

**Type:** Semantic (Layer 1)
**Severity:** WARNING
**Operates on:** GDSSpec

**Property Statement:**
Let `canonical = project_canonical(spec)`. Then:

```
|canonical.mechanism_blocks| >= 1
```

The state transition function `f` in the canonical decomposition
`h = f . g` must contain at least one mechanism.

**Invariant Enforced:**
Non-degeneracy of the state transition. In the canonical form `h = f . g`,
`f: X -> X` is the state transition function implemented by mechanisms. If
there are no mechanisms, `f` is the empty function -- the system has no state
dynamics. The canonical form degenerates to `h = g` (pure observation with no
state update).

**Failure Semantics:**
An empty `f` means the system cannot update state. This may be intentional
for pure policy compositions or game-theoretic specifications that model
strategy selection without state dynamics. WARNING severity reflects this
ambiguity.

**Soundness Conditions:**
A pass guarantees at least one mechanism exists. This does not validate that
the mechanisms form a coherent transition function (SC-001 and SC-002 address
coverage and determinism).

**Algorithm:**
Call `project_canonical(spec)` and check whether `mechanism_blocks` is
non-empty.

---

### SC-007 -- Canonical Wellformedness (X)

**Type:** Semantic (Layer 1)
**Severity:** WARNING
**Operates on:** GDSSpec

**Property Statement:**
Let `canonical = project_canonical(spec)`. Then:

```
|canonical.state_variables| >= 1
```

The state space X must contain at least one variable.

**Invariant Enforced:**
Non-degeneracy of the state space. In the canonical form `h = f . g`, the
domain and codomain of `f` is the state space `X = PRODUCT(e.variables : e in E)`.
If X is empty (no entities with variables), the canonical form has no state to
transition over. The system is stateless.

**Failure Semantics:**
An empty X means there is no state for `f` to act on. Like SC-006, this may
be intentional for stateless compositions. WARNING severity reflects this
ambiguity.

**Soundness Conditions:**
A pass guarantees at least one state variable exists in the canonical
projection. This does not validate that the state space is well-typed (Space
and TypeDef consistency is a separate concern).

**Algorithm:**
Call `project_canonical(spec)` and check whether `state_variables` is
non-empty. Note: SC-006 and SC-007 are both produced by the same function
`check_canonical_wellformedness()`.

---

### SC-008 -- Admissibility References

**Type:** Semantic (Layer 1)
**Severity:** ERROR
**Operates on:** GDSSpec

**Property Statement:**
For every registered `AdmissibleInputConstraint` `ac`:

```
(1) ac.boundary_block in spec.blocks
(2) spec.blocks[ac.boundary_block] is BoundaryAction
(3) For all (e, v) in ac.depends_on:
      e in spec.entities AND v in spec.entities[e].variables
```

Every admissibility constraint must reference an existing BoundaryAction and
valid (entity, variable) pairs.

**Invariant Enforced:**
Referential integrity of admissibility declarations. Admissibility constraints
define the input space restrictions on BoundaryActions -- they specify which
exogenous inputs are admissible given the current state. An invalid reference
(non-existent block, wrong block type, non-existent entity or variable) means
the constraint cannot be evaluated. In the canonical form, admissibility
constrains the domain of `g` (the observation/policy map that includes
boundary inputs).

**Failure Semantics:**
An invalid reference means the admissibility constraint is structurally broken.
It references a block that does not exist, is not a BoundaryAction, or depends
on state variables that are not declared. Downstream tools that evaluate
admissibility (simulation, analysis) will fail.

**Soundness Conditions:**
A pass guarantees all structural references in admissibility constraints are
valid. This does not verify that the constraint predicate is logically
satisfiable or that the referenced BoundaryAction's interface is compatible
with the constraint -- those are runtime concerns.

**Algorithm:**
For each `AdmissibleInputConstraint`, check: (1) `boundary_block` exists in
`spec.blocks`; (2) it is a `BoundaryAction` instance; (3) each `(entity, var)`
in `depends_on` resolves to a registered entity with that variable.

---

### SC-009 -- Transition Reads

**Type:** Semantic (Layer 1)
**Severity:** ERROR
**Operates on:** GDSSpec

**Property Statement:**
For every registered `TransitionSignature` `ts`:

```
(1) ts.mechanism in spec.blocks
(2) spec.blocks[ts.mechanism] is Mechanism
(3) For all (e, v) in ts.reads:
      e in spec.entities AND v in spec.entities[e].variables
(4) For all b in ts.depends_on_blocks:
      b in spec.blocks
```

Every transition signature must reference an existing Mechanism, valid
(entity, variable) read pairs, and valid block dependencies.

**Invariant Enforced:**
Referential integrity of transition signature declarations. Transition
signatures describe the read dependencies of each mechanism -- which state
variables it reads and which blocks it depends on. In the canonical form,
this metadata describes the input dependencies of the state transition
function `f`. An invalid reference means the dependency graph of `f` is
structurally broken.

**Failure Semantics:**
An invalid reference means the transition signature points to non-existent
components. The mechanism may not exist, the read variables may not be
declared, or the dependency blocks may not be registered. Downstream tools
that use transition signatures for dependency analysis (reachability, causal
ordering) will produce incorrect results.

**Soundness Conditions:**
A pass guarantees all structural references in transition signatures are
valid. This does not verify that the declared reads are consistent with the
mechanism's actual runtime behavior or that the dependency graph is complete.

**Algorithm:**
For each `TransitionSignature`, check: (1) `mechanism` exists in
`spec.blocks`; (2) it is a `Mechanism` instance; (3) each `(entity, var)` in
`reads` resolves to a registered entity with that variable; (4) each block in
`depends_on_blocks` exists in `spec.blocks`.

---

## What the Checks Do NOT Prove

The 15 checks above validate *structural well-formedness* of the specification.
They ensure the model is internally consistent, the composition algebra is
well-typed, and the canonical form `h = f . g` is non-degenerate. They do NOT
prove any of the following:

**Behavioral correctness.** The checks do not verify that the system *does the
right thing*. A thermostat model can pass all 15 checks and still have inverted
control logic (heating when it should cool). Correctness requires behavioral
specifications (pre/post conditions, temporal logic) that are outside the scope
of structural verification.

**Safety properties.** The checks do not prove that the system avoids bad
states. "The temperature never exceeds 100C" is a safety property that requires
invariant analysis over the state space, not structural checks on the
specification graph.

**Liveness properties.** The checks do not prove that the system eventually
reaches a desired state. "The system eventually stabilizes" is a liveness
property that requires temporal logic or Lyapunov analysis.

**Stability.** The checks do not analyze the dynamical stability of the system.
Eigenvalue analysis, Lyapunov functions, and bifurcation analysis are the
domain of `gds-continuous` and `gds-symbolic`, not structural verification.

**Completeness of the specification itself.** SC-001 checks that every variable
has a mechanism, but it does not check whether the specification captures all
relevant aspects of the real system. The map is not the territory.

**Semantic equivalence.** The checks do not prove that two specifications are
equivalent, or that a specification correctly implements a higher-level
requirement. Bisimulation and refinement checking are research-level concerns
(see `research/verification-plan.md`).

This aligns with the **verification humility doctrine**: structural verification
establishes necessary conditions for a well-formed specification, but it does
not establish sufficient conditions for correctness. The checks are a foundation
for further analysis (simulation, formal methods, domain review), not a
substitute for it.

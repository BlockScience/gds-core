# gds-core: A Clean Python Package for Typed GDS Specifications

> Design document synthesizing Generalized Dynamical Systems theory, MSML, and BDP-lib into a minimal, composable Python package.

---

## 1. What is a Generalized Dynamical System?

### 1.1 The Core Formalism

A Generalized Dynamical System (GDS), as formalized by Roxin in the 1960s and extended by Zargham & Shorish (2022), is a pair **{h, X}** where:

- **X** is the **state space** — but unlike classical dynamical systems, X can be *any* data structure, not just ℝⁿ. It can be records, graphs, token balances, governance configurations, agent populations — anything.
- **h** is a **transition mapping** X → X, where the space of such mappings is **closed under composition**.

The key extension over classical dynamical systems: GDS doesn't assume vector spaces. The mapping h can incorporate:

- **Admissible inputs U** — what actions are currently allowed given the state
- **Constraints** — invariants that must hold across transitions
- **Multiple agents** with different action sets
- **Policies** that select from feasible actions

From the paper: *"a data structure is mapped to itself and the space of such mappings is closed under composition."*

### 1.2 Why GDS Matters

GDS nests several well-known modeling frameworks into one:

- **Optimal control** — state + control inputs + constraints
- **System dynamics** — stocks, flows, feedback loops
- **Agent-based models** — heterogeneous actors with strategies
- **Network dynamics** — topology-dependent state evolution

The practical power: you can specify a complex socio-technical system — a DAO's treasury management, a bonding curve, an insurance contract — as a single formal object that admits questions about:

- **Reachability** — "Can the system get to state Y from state X?"
- **Admissibility** — "Is this action allowed given the current state?"
- **Controllability** — "Can we steer the system toward desired outcomes?"

### 1.3 Block Diagram Representation

The block diagram representation (from Zargham & Shorish's "Block Diagrams for Categorical Cybernetics") makes GDS implementable as software:

- **Blocks** are typed functions: `domain → codomain`
- **Spaces** are the types flowing between blocks
- **Wiring** is composition: connecting block outputs to inputs

The composed wiring *is* the transition function h. The spaces flowing through wires carry typed data that can be verified at specification time — before any code runs. This is the bridge from math to engineering.

### 1.4 GDS Concept → Software Mapping

| GDS Math | Software Concept | Python Class |
|----------|-----------------|--------------|
| X (state space) | Product of entity states | `Entity` + `StateVariable` |
| U (admissible inputs) | Exogenous signals | `BoundaryAction` |
| h: X → X (transition) | Composed block wiring | `Wiring` |
| Action spaces | Typed data flowing between blocks | `Space` |
| Type structure | Constrained Python type | `TypeDef` |
| Mechanism | State-writing function | `Mechanism` |
| Policy / Decision | Signal-routing logic | `Policy` |
| Constraints | Invariants on blocks | `Block.constraints` |
| Reachability | Transitive wiring closure | `SpecVerifier` |
| Admissibility | Domain satisfaction check | `SpecVerifier` |
| Attainability correspondence | Possible next-states from current state | `SpecVerifier.check_reachability()` |
| Configuration space | State subspace satisfying conservation laws | `SpecVerifier.check_conservation()` |

---

## 2. Prior Art: MSML & BDP-lib

### 2.1 MSML (math-spec-mapping)

*888 commits, 58 Python files, JSON-spec-first approach.*

MSML was designed as an end-to-end specification-to-simulation tool — and in that role it delivered considerable value:

1. JSON-based spec → parse → validate → report pipeline gives trackability via git
2. Block subtypes (BoundaryAction, Policy, Mechanism, ControlAction) map cleanly to GDS roles
3. Transmission channels (action + state update) make data flow explicit
4. Obsidian report generation for stakeholder communication is genuinely useful
5. Parameter crawling — tracing which params affect which blocks — is a killer feature
6. Composite blocks (Stack, Parallel, Split) for wiring composition match GDS composition

**Where our goals diverge:** MSML was built to serve a full pipeline from specification through rendering to cadCAD execution, which led to natural design choices for that use case — JSON-first authoring for language-agnostic specs, integrated Mermaid rendering, a central `MathSpec` coordinator. Our goal is different: a lightweight, composable library focused purely on typed specification and verification. This means we make different trade-offs:

- **Python-native authoring** instead of JSON-first — optimizing for the Python developer workflow
- **Runtime type constraints** instead of metadata labels — catching errors at spec-time
- **Separated concerns** — spec, rendering, and execution as independent packages
- **Formal verification** — completeness, determinism, and reachability checks that go beyond structural validation

### 2.2 BDP-lib (Block Diagram Protocol)

*161 commits, JSON-schema protocol, language-agnostic design.*

BDP introduced an elegant conceptual framework that we build on:

1. **Clean 2×2 conceptual framework** — Abstract/Concrete × Structure/Behavior:

|  | Abstract | Concrete |
|--|----------|----------|
| **Structure** | Space | Wire |
| **Behavior** | Block | Processor |

2. Space (abstract structure) vs Wire (concrete structure) distinction is the right ontology
3. Block (abstract behavior) vs Processor (concrete behavior) — templates vs instances
4. Protocol/client separation — schema is language-agnostic, implementations can vary
5. Validation rules: referential integrity, single-input ports, connectivity checks

**Where our goals diverge:** BDP was designed as a general-purpose block diagram protocol — language-agnostic and domain-neutral. That generality is a strength for its intended purpose, but our needs are more specific. We need domain-aware primitives (state entities, parameters, GDS block roles) and semantic validation (type matching, reachability) that go beyond structural connectivity checks. We also prioritize Python-native ergonomics over protocol-level interoperability.

### 2.3 The Synthesis

`gds-framework` builds on the strengths of both projects: **BDP's layered architecture** (abstract/concrete separation) combined with **MSML's domain knowledge** (GDS block roles, state entities, parameter tracking). We add **Python-native classes** with real type constraints, **bidirectional composition** from categorical cybernetics, and a **formal verification layer** — all in a focused library that separates specification from rendering and execution.

---

## 3. Proposed Design: gds-core

### 3.1 Design Principles

**1. Python-first, JSON-optional**
Users define specs in Python with real types and IDE autocomplete. JSON serialization is an export format, not the authoring format.

**2. Types that bite**
`TypeDef` carries runtime constraints (not just labels). `Space.validate()` actually checks data against its schema. Errors are caught at spec-time, before simulation.

**3. Spec ≠ Rendering ≠ Execution**
gds-core is ONLY types, classes, and verification. No Mermaid. No cadCAD. No Obsidian. Those become separate packages that consume a `GDSSpec` object.

**4. Composition is first-class**
`StackWiring`, `ParallelWiring`, `SplitWiring` are explicit. Domain/codomain compatibility is checked at composition time, not after the fact.

**5. Verification ladder**
Level 1: structural (references exist). Level 2: type-flow (spaces match across wires). Level 3: semantic (conservation, determinism, reachability). Each level builds on the last.

**6. Building on prior art**
Adopt BDP's abstract/concrete × structure/behavior framing. Adopt MSML's GDS-specific block subtypes. Add Python-native authoring with runtime type constraints.

### 3.2 Package Structure

```
gds-core/
├── gds_core/
│   ├── __init__.py          # Public API
│   ├── types.py             # TypeDef, built-in types
│   ├── spaces.py            # Space, EMPTY, TERMINAL
│   ├── blocks.py            # Block, BoundaryAction, Policy,
│   │                        # Mechanism, ControlAction
│   ├── state.py             # Entity, StateVariable
│   ├── wiring.py            # Wire, Wiring, Stack/Parallel/Split
│   ├── spec.py              # GDSSpec (registration + basic validation)
│   ├── verify.py            # SpecVerifier (higher-order checks)
│   ├── query.py             # Dependency graph, reachability, impact analysis
│   └── serialize.py         # to/from JSON, to/from dict
├── tests/
│   ├── test_types.py
│   ├── test_spaces.py
│   ├── test_blocks.py
│   ├── test_wiring.py
│   ├── test_spec.py
│   └── test_verify.py
├── examples/
│   ├── predator_prey.py
│   ├── bonding_curve.py
│   └── insurance_contract.py
└── pyproject.toml
```

### 3.3 Layer Separation

| Layer | Package | Depends on |
|-------|---------|------------|
| **Specification** | **gds-core (this)** | **Nothing (stdlib only)** |
| Visualization | gds-viz (separate) | gds-core |
| Simulation | gds-sim (separate) | gds-core |
| Reports | gds-reports (separate) | gds-core, gds-viz |
| cadCAD bridge | gds-cadcad (separate) | gds-core, cadcad |

The spec layer has **zero dependencies**. This is a hard constraint.

---

## 4. Full Type & Class API

### 4.1 types.py — TypeDef and Built-in Types

```python
from typing import Any, Optional, Callable


class TypeDef:
    """A named, constrained type used in spaces and state.

    A named, constrained type — the atom of the type system.
    Carries runtime-checkable constraints beyond metadata labels.
    """

    def __init__(
        self,
        name: str,
        python_type: type,
        description: str = "",
        constraint: Optional[Callable[[Any], bool]] = None,
        units: Optional[str] = None,
    ):
        self.name = name
        self.python_type = python_type
        self.description = description
        self.constraint = constraint
        self.units = units

    def validate(self, value: Any) -> bool:
        """Check if a value satisfies this type definition."""
        if not isinstance(value, self.python_type):
            return False
        if self.constraint and not self.constraint(value):
            return False
        return True

    def __repr__(self):
        return f"TypeDef({self.name}: {self.python_type.__name__})"

    def __eq__(self, other):
        return isinstance(other, TypeDef) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


# ── Built-in types ──────────────────────────────────────────

Probability = TypeDef(
    "Probability", float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="A value in [0, 1]",
)

NonNegativeFloat = TypeDef(
    "NonNegativeFloat", float,
    constraint=lambda x: x >= 0,
)

PositiveInt = TypeDef(
    "PositiveInt", int,
    constraint=lambda x: x > 0,
)

TokenAmount = TypeDef(
    "TokenAmount", float,
    constraint=lambda x: x >= 0,
    units="tokens",
)

AgentID = TypeDef("AgentID", str)

Timestamp = TypeDef(
    "Timestamp", float,
    constraint=lambda x: x >= 0,
    units="seconds",
)
```

### 4.2 spaces.py — Typed Product Spaces

```python
from typing import Dict
from .types import TypeDef


class Space:
    """A typed product space — defines the shape of signals flowing between blocks.

    In BDP terms: this is Abstract Structure.
    In GDS terms: these are the action spaces / signal spaces.

    Fields are TypeDef instances, so validation is enforced at the
    type level — data flowing through a wire is checked against its schema.
    """

    def __init__(
        self,
        name: str,
        schema: Dict[str, TypeDef],
        description: str = "",
    ):
        self.name = name
        self.schema = schema  # {field_name: TypeDef}
        self.description = description

    def validate(self, data: dict) -> list[str]:
        """Validate a data dict against this space's schema.
        Returns list of error strings (empty = valid).
        """
        errors = []
        for field_name, typedef in self.schema.items():
            if field_name not in data:
                errors.append(f"Missing field: {field_name}")
            elif not typedef.validate(data[field_name]):
                errors.append(
                    f"{field_name}: expected {typedef.name}, "
                    f"got {type(data[field_name]).__name__} "
                    f"with value {data[field_name]!r}"
                )
        extra_fields = set(data.keys()) - set(self.schema.keys())
        if extra_fields:
            errors.append(f"Unexpected fields: {extra_fields}")
        return errors

    def is_compatible(self, other: "Space") -> bool:
        """Check if another space has the same structure (field names and types)."""
        if set(self.schema.keys()) != set(other.schema.keys()):
            return False
        return all(
            self.schema[k] == other.schema[k]
            for k in self.schema
        )

    def __repr__(self):
        fields = ", ".join(f"{k}: {v.name}" for k, v in self.schema.items())
        return f"Space({self.name} {{ {fields} }})"

    def __eq__(self, other):
        return isinstance(other, Space) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


# ── Sentinel spaces ────────────────────────────────────────

EMPTY = Space("∅", {}, "No data flows through this port")
TERMINAL = Space("⊤", {}, "Signal terminates here (state write)")
```

### 4.3 blocks.py — Abstract Behavior with GDS Roles

```python
from typing import Tuple, Optional
from .spaces import Space, TERMINAL


class Block:
    """Abstract behavioral specification — a typed function signature.

    In BDP terms: Abstract Behavior.
    In GDS terms: a component of the transition function h.

    A Block declares what goes in (domain), what comes out (codomain),
    what parameters it reads, and what constraints it must satisfy.
    Blocks do NOT hold implementations — they are pure type-level declarations.
    """

    kind = "generic"

    def __init__(
        self,
        name: str,
        domain: Tuple[Space, ...],
        codomain: Tuple[Space, ...],
        description: str = "",
        params_used: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
    ):
        self.name = name
        self.domain = domain
        self.codomain = codomain
        self.description = description
        self.params_used = params_used or []
        self.constraints = constraints or []

    def signature(self) -> str:
        """Human-readable type signature."""
        d = " × ".join(s.name for s in self.domain)
        c = " × ".join(s.name for s in self.codomain)
        return f"{self.name}: {d} → {c}"

    def __repr__(self):
        return f"<{self.kind}: {self.signature()}>"

    def __eq__(self, other):
        return isinstance(other, Block) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


class BoundaryAction(Block):
    """Exogenous input — enters the system from outside.

    In GDS terms: this is part of the admissible input set U.
    Boundary actions model external agents, oracles, user inputs,
    environmental signals — anything the system doesn't control.
    """

    kind = "boundary"

    def __init__(self, name, domain, codomain, description="",
                 params_used=None, constraints=None,
                 options: Optional[list[str]] = None):
        super().__init__(name, domain, codomain, description,
                         params_used, constraints)
        self.options = options or []  # Named behavioral variants


class ControlAction(Block):
    """Endogenous control — reads state, emits control signals.

    These are internal feedback loops: the system observing itself
    and generating signals that influence downstream policy/mechanism blocks.
    """

    kind = "control"

    def __init__(self, name, domain, codomain, description="",
                 params_used=None, constraints=None,
                 options: Optional[list[str]] = None):
        super().__init__(name, domain, codomain, description,
                         params_used, constraints)
        self.options = options or []


class Policy(Block):
    """Decision logic — maps signals to mechanism inputs.

    Policies select from feasible actions. They may have multiple
    named options for A/B testing or scenario analysis.

    In GDS terms: policies implement the decision mapping
    within the admissibility constraint.
    """

    kind = "policy"

    def __init__(self, name, domain, codomain, description="",
                 params_used=None, constraints=None,
                 options: Optional[list[str]] = None):
        super().__init__(name, domain, codomain, description,
                         params_used, constraints)
        self.options = options or []


class Mechanism(Block):
    """State update — the only block type that writes to state.

    Codomain is always TERMINAL because mechanisms don't pass signals
    forward; they write to entity state variables.

    In GDS terms: mechanisms are the atomic state transitions
    that compose into h.
    """

    kind = "mechanism"

    def __init__(
        self,
        name: str,
        domain: Tuple[Space, ...],
        description: str = "",
        params_used: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        updates: Optional[list[tuple[str, str]]] = None,
    ):
        super().__init__(name, domain, (TERMINAL,), description,
                         params_used, constraints)
        self.updates = updates or []
        # updates is a list of (entity_name, variable_name) pairs
```

### 4.4 state.py — Entities and State Variables

```python
from typing import Optional
from .types import TypeDef


class StateVariable:
    """A single typed variable within an entity's state.

    Each variable has a TypeDef (with runtime constraints),
    a human-readable description, and an optional math symbol.
    """

    def __init__(
        self,
        name: str,
        typedef: TypeDef,
        description: str = "",
        symbol: Optional[str] = None,
    ):
        self.name = name
        self.typedef = typedef
        self.description = description
        self.symbol = symbol or name

    def validate(self, value) -> bool:
        return self.typedef.validate(value)

    def __repr__(self):
        return f"StateVar({self.name}: {self.typedef.name})"


class Entity:
    """A named component of the system state.

    In GDS terms, the full state space X is the product
    of all entity state spaces:
        X = Entity_1.state × Entity_2.state × ... × Entity_n.state

    Entities correspond to actors, resources, registries —
    anything that persists across timesteps and has mutable state.
    """

    def __init__(
        self,
        name: str,
        variables: list[StateVariable],
        description: str = "",
    ):
        self.name = name
        self.variables = {v.name: v for v in variables}
        self.description = description

    def validate_state(self, data: dict) -> list[str]:
        """Validate a state snapshot for this entity."""
        errors = []
        for vname, var in self.variables.items():
            if vname not in data:
                errors.append(f"{self.name}.{vname}: missing")
            elif not var.validate(data[vname]):
                errors.append(f"{self.name}.{vname}: type/constraint violation")
        return errors

    def __repr__(self):
        vars_str = ", ".join(self.variables.keys())
        return f"Entity({self.name} {{ {vars_str} }})"
```

### 4.5 wiring.py — Composition

```python
from typing import Tuple, Optional
from .spaces import Space, EMPTY, TERMINAL
from .blocks import Block


class Wire:
    """Concrete connection between block ports.

    In BDP terms: Concrete Structure.
    A wire carries data of a specific Space type from one block's
    codomain port to another block's domain port.
    """

    def __init__(
        self,
        source: str,
        target: str,
        space: Space,
        optional: bool = False,
    ):
        self.source = source   # block name (codomain side)
        self.target = target   # block name (domain side)
        self.space = space
        self.optional = optional

    def __repr__(self):
        opt = " (optional)" if self.optional else ""
        return f"Wire({self.source} --[{self.space.name}]--> {self.target}{opt})"


class Wiring:
    """A composed system of blocks connected by wires.

    In BDP terms: this combines Processors (block instances)
    and Wires (connections) into a system.
    In GDS terms: this is a particular composition of h.
    """

    def __init__(
        self,
        name: str,
        blocks: list[Block],
        wires: list[Wire],
        description: str = "",
    ):
        self.name = name
        self.blocks = {b.name: b for b in blocks}
        self.wires = wires
        self.description = description

    def validate_wiring(self) -> list[str]:
        """Check that all wires connect valid blocks with matching spaces."""
        errors = []
        for w in self.wires:
            if w.source not in self.blocks:
                errors.append(f"Wire source '{w.source}' not in blocks")
            if w.target not in self.blocks:
                errors.append(f"Wire target '{w.target}' not in blocks")
            if w.source in self.blocks and w.target in self.blocks:
                src = self.blocks[w.source]
                tgt = self.blocks[w.target]
                if w.space not in src.codomain:
                    errors.append(
                        f"Wire space '{w.space.name}' not in "
                        f"{w.source}'s codomain"
                    )
                if w.space not in tgt.domain:
                    errors.append(
                        f"Wire space '{w.space.name}' not in "
                        f"{w.target}'s domain"
                    )
        return errors

    @property
    def external_domain(self) -> Tuple[Space, ...]:
        """Infer unwired inputs (external boundary of this wiring)."""
        wired_targets = set()
        for w in self.wires:
            wired_targets.add((w.target, w.space.name))
        external = []
        for b in self.blocks.values():
            for s in b.domain:
                if s not in (EMPTY, TERMINAL):
                    if (b.name, s.name) not in wired_targets:
                        external.append(s)
        return tuple(external)

    @property
    def external_codomain(self) -> Tuple[Space, ...]:
        """Infer unwired outputs (external boundary of this wiring)."""
        wired_sources = set()
        for w in self.wires:
            wired_sources.add((w.source, w.space.name))
        external = []
        for b in self.blocks.values():
            for s in b.codomain:
                if s not in (EMPTY, TERMINAL):
                    if (b.name, s.name) not in wired_sources:
                        external.append(s)
        return tuple(external)

    def __repr__(self):
        return f"Wiring({self.name}: {len(self.blocks)} blocks, {len(self.wires)} wires)"


class StackWiring(Wiring):
    """Sequential composition: A → B → C.

    Each block's codomain must match the next block's domain.
    Wires are auto-generated from the sequence.
    """

    def __init__(self, name: str, sequence: list[Block],
                 description: str = ""):
        wires = []
        for a, b in zip(sequence[:-1], sequence[1:]):
            # Match codomain of a to domain of b
            for s in a.codomain:
                if s not in (EMPTY, TERMINAL) and s in b.domain:
                    wires.append(Wire(a.name, b.name, s))
        super().__init__(name, sequence, wires, description)
        self.sequence = sequence

    def validate_wiring(self) -> list[str]:
        errors = super().validate_wiring()
        # Additional check: sequential domain/codomain matching
        for a, b in zip(self.sequence[:-1], self.sequence[1:]):
            a_out = [s for s in a.codomain if s not in (EMPTY, TERMINAL)]
            b_in = [s for s in b.domain if s not in (EMPTY, TERMINAL)]
            if a_out != b_in:
                errors.append(
                    f"Stack mismatch: {a.name} outputs {[s.name for s in a_out]} "
                    f"but {b.name} expects {[s.name for s in b_in]}"
                )
        return errors


class ParallelWiring(Wiring):
    """Parallel composition: A ∥ B.

    Independent blocks running simultaneously. Domain is the
    union of all component domains; codomain is the union of
    all component codomains.
    """

    def __init__(self, name: str, components: list[Block],
                 description: str = ""):
        super().__init__(name, components, [], description)
        self.components = components


class SplitWiring(Wiring):
    """Branching composition: one input fans out to multiple paths.

    A single source block's output is consumed by multiple
    downstream blocks.
    """

    def __init__(self, name: str, source: Block,
                 targets: list[Block], description: str = ""):
        wires = []
        for t in targets:
            for s in source.codomain:
                if s not in (EMPTY, TERMINAL) and s in t.domain:
                    wires.append(Wire(source.name, t.name, s))
        all_blocks = [source] + targets
        super().__init__(name, all_blocks, wires, description)
        self.source = source
        self.targets = targets
```

### 4.6 spec.py — The GDS Specification Object

```python
from typing import Dict
from .types import TypeDef
from .spaces import Space
from .blocks import Block, Mechanism
from .state import Entity, StateVariable
from .wiring import Wiring


class GDSSpec:
    """Complete Generalized Dynamical System specification.

    Mathematically: GDS = {h, X} where
        X = state space (product of entity states)
        h = transition map (composed from wirings)

    This class holds the full typed specification and validates
    structural integrity. It does NOT render, simulate, or export.
    That is the job of separate packages.

    GDSSpec handles registration and structural validation only.
    Rendering, simulation, and export are separate concerns.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.types: Dict[str, TypeDef] = {}
        self.spaces: Dict[str, Space] = {}
        self.entities: Dict[str, Entity] = {}
        self.blocks: Dict[str, Block] = {}
        self.wirings: Dict[str, Wiring] = {}
        self.parameters: Dict[str, TypeDef] = {}

    # ── Registration ────────────────────────────────────────

    def register_type(self, t: TypeDef) -> "GDSSpec":
        assert t.name not in self.types, f"Type '{t.name}' already registered"
        self.types[t.name] = t
        return self  # chainable

    def register_space(self, s: Space) -> "GDSSpec":
        assert s.name not in self.spaces, f"Space '{s.name}' already registered"
        self.spaces[s.name] = s
        return self

    def register_entity(self, e: Entity) -> "GDSSpec":
        assert e.name not in self.entities, f"Entity '{e.name}' already registered"
        self.entities[e.name] = e
        return self

    def register_block(self, b: Block) -> "GDSSpec":
        assert b.name not in self.blocks, f"Block '{b.name}' already registered"
        self.blocks[b.name] = b
        return self

    def register_wiring(self, w: Wiring) -> "GDSSpec":
        assert w.name not in self.wirings, f"Wiring '{w.name}' already registered"
        self.wirings[w.name] = w
        return self

    def register_parameter(self, name: str, typedef: TypeDef) -> "GDSSpec":
        assert name not in self.parameters, f"Parameter '{name}' already registered"
        self.parameters[name] = typedef
        return self

    # ── Validation ──────────────────────────────────────────

    def validate(self) -> list[str]:
        """Full structural validation. Returns list of error strings."""
        errors = []
        errors += self._validate_space_types()
        errors += self._validate_block_spaces()
        errors += self._validate_wiring_compatibility()
        errors += self._validate_mechanism_updates()
        errors += self._validate_param_references()
        return errors

    def _validate_space_types(self) -> list[str]:
        """Every TypeDef used in a Space is registered."""
        errors = []
        for space in self.spaces.values():
            for field_name, typedef in space.schema.items():
                if typedef.name not in self.types:
                    errors.append(
                        f"Space '{space.name}' field '{field_name}' uses "
                        f"unregistered type '{typedef.name}'"
                    )
        return errors

    def _validate_block_spaces(self) -> list[str]:
        """Every Space referenced by a block is registered."""
        errors = []
        for block in self.blocks.values():
            for s in list(block.domain) + list(block.codomain):
                if s.name not in self.spaces and s.name not in ("∅", "⊤"):
                    errors.append(
                        f"Block '{block.name}' references "
                        f"unregistered space '{s.name}'"
                    )
        return errors

    def _validate_wiring_compatibility(self) -> list[str]:
        """All wirings have structurally valid connections."""
        errors = []
        for wiring in self.wirings.values():
            errors += wiring.validate_wiring()
        return errors

    def _validate_mechanism_updates(self) -> list[str]:
        """Mechanisms only update existing entity variables."""
        errors = []
        for block in self.blocks.values():
            if isinstance(block, Mechanism):
                for entity_name, var_name in block.updates:
                    if entity_name not in self.entities:
                        errors.append(
                            f"Mechanism '{block.name}' updates "
                            f"unknown entity '{entity_name}'"
                        )
                    elif var_name not in self.entities[entity_name].variables:
                        errors.append(
                            f"Mechanism '{block.name}' updates "
                            f"unknown variable '{entity_name}.{var_name}'"
                        )
        return errors

    def _validate_param_references(self) -> list[str]:
        """All parameter references in blocks are registered."""
        errors = []
        for block in self.blocks.values():
            for param in block.params_used:
                if param not in self.parameters:
                    errors.append(
                        f"Block '{block.name}' references "
                        f"unregistered parameter '{param}'"
                    )
        return errors
```

### 4.7 verify.py — Higher-Order GDS Properties

```python
from .spec import GDSSpec
from .blocks import Mechanism, BoundaryAction, ControlAction, Policy


class SpecVerifier:
    """Verifies higher-order structural properties of a GDSSpec.

    These correspond to GDS-theoretic properties like admissibility,
    reachability, and conservation — checked at the specification level
    (before any simulation runs).

    Formal verification at the specification level, before any simulation.
    """

    def __init__(self, spec: GDSSpec):
        self.spec = spec

    def check_completeness(self) -> list[str]:
        """Every entity variable is updated by at least one mechanism.
        (No orphan state variables that can never change.)
        """
        errors = []
        all_updates = set()
        for block in self.spec.blocks.values():
            if isinstance(block, Mechanism):
                for entity_name, var_name in block.updates:
                    all_updates.add((entity_name, var_name))

        for entity in self.spec.entities.values():
            for var_name in entity.variables:
                if (entity.name, var_name) not in all_updates:
                    errors.append(
                        f"Orphan variable: {entity.name}.{var_name} "
                        f"is never updated by any mechanism"
                    )
        return errors

    def check_determinism(self) -> list[str]:
        """Within each wiring, no two mechanisms update the same variable.
        (Write conflict detection.)
        """
        errors = []
        for wiring in self.spec.wirings.values():
            update_map = {}  # (entity, var) -> list of mechanism names
            for bname, block in wiring.blocks.items():
                if isinstance(block, Mechanism):
                    for entity_name, var_name in block.updates:
                        key = (entity_name, var_name)
                        if key not in update_map:
                            update_map[key] = []
                        update_map[key].append(bname)
            for (ename, vname), mechs in update_map.items():
                if len(mechs) > 1:
                    errors.append(
                        f"Write conflict in wiring '{wiring.name}': "
                        f"{ename}.{vname} updated by {mechs}"
                    )
        return errors

    def check_reachability(self, from_block: str,
                           to_block: str) -> bool:
        """Can signals reach from block A to block B through wiring?
        (Maps to GDS attainability correspondence.)
        """
        # Build adjacency from all wirings
        adj = {}
        for wiring in self.spec.wirings.values():
            for wire in wiring.wires:
                if wire.source not in adj:
                    adj[wire.source] = set()
                adj[wire.source].add(wire.target)

        # BFS
        visited = set()
        queue = [from_block]
        while queue:
            current = queue.pop(0)
            if current == to_block:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(adj.get(current, set()))
        return False

    def check_admissibility(self, wiring_name: str) -> list[str]:
        """All blocks in a wiring have their domain requirements satisfied.
        No dangling inputs — every non-empty domain port is either wired
        or is an external input.
        (Maps to GDS admissible inputs U.)
        """
        errors = []
        wiring = self.spec.wirings[wiring_name]
        wired_inputs = set()
        for w in wiring.wires:
            wired_inputs.add((w.target, w.space.name))

        for bname, block in wiring.blocks.items():
            for space in block.domain:
                if space.name in ("∅", "⊤"):
                    continue
                if (bname, space.name) not in wired_inputs:
                    # This is an external input — that's fine,
                    # but it should be noted
                    pass  # Could flag as "requires external input"
        return errors

    def check_type_safety(self) -> list[str]:
        """Full type-flow analysis through all wirings.
        Every wire's space matches source codomain and target domain
        at the field level (not just by name).
        """
        errors = []
        for wiring in self.spec.wirings.values():
            for wire in wiring.wires:
                src = wiring.blocks.get(wire.source)
                tgt = wiring.blocks.get(wire.target)
                if src and tgt:
                    # Check space compatibility at field level
                    src_spaces = {s.name: s for s in src.codomain}
                    tgt_spaces = {s.name: s for s in tgt.domain}
                    if wire.space.name in src_spaces and wire.space.name in tgt_spaces:
                        s1 = src_spaces[wire.space.name]
                        s2 = tgt_spaces[wire.space.name]
                        if not s1.is_compatible(s2):
                            errors.append(
                                f"Type mismatch on wire {wire}: "
                                f"source space and target space "
                                f"have different schemas"
                            )
        return errors

    def blocks_affecting(self, entity: str,
                         variable: str) -> list[str]:
        """Which blocks can transitively affect this variable?
        Generalized transitive impact analysis.
        """
        # Direct: mechanisms that update this variable
        direct = []
        for bname, block in self.spec.blocks.items():
            if isinstance(block, Mechanism):
                if (entity, variable) in block.updates:
                    direct.append(bname)

        # Transitive: anything that can reach those mechanisms
        all_affecting = set(direct)
        for mech_name in direct:
            for bname in self.spec.blocks:
                if self.check_reachability(bname, mech_name):
                    all_affecting.add(bname)
        return list(all_affecting)

    def report(self) -> dict:
        """Run all structural checks, return a summary."""
        return {
            "completeness": self.check_completeness(),
            "determinism": self.check_determinism(),
            "type_safety": self.check_type_safety(),
            "spec_validation": self.spec.validate(),
        }
```

### 4.8 query.py — Dependency Analysis

```python
from .spec import GDSSpec
from .blocks import Mechanism, BoundaryAction, ControlAction, Policy


class SpecQuery:
    """Query engine for exploring GDSSpec structure.

    A clean query API for exploring spec structure — parameter mapping,
    dependency graphs, and transitive impact analysis.
    """

    def __init__(self, spec: GDSSpec):
        self.spec = spec

    def param_to_blocks(self) -> dict[str, list[str]]:
        """Map each parameter to the blocks that use it."""
        mapping = {p: [] for p in self.spec.parameters}
        for bname, block in self.spec.blocks.items():
            for param in block.params_used:
                if param in mapping:
                    mapping[param].append(bname)
        return mapping

    def block_to_params(self) -> dict[str, list[str]]:
        """Map each block to the parameters it uses."""
        return {
            bname: list(block.params_used)
            for bname, block in self.spec.blocks.items()
        }

    def entity_update_map(self) -> dict[str, dict[str, list[str]]]:
        """Map entity → variable → list of mechanisms that update it."""
        result = {}
        for ename, entity in self.spec.entities.items():
            result[ename] = {vname: [] for vname in entity.variables}

        for bname, block in self.spec.blocks.items():
            if isinstance(block, Mechanism):
                for ename, vname in block.updates:
                    if ename in result and vname in result[ename]:
                        result[ename][vname].append(bname)
        return result

    def dependency_graph(self) -> dict[str, set[str]]:
        """Full block dependency DAG (who feeds whom)."""
        adj = {}
        for wiring in self.spec.wirings.values():
            for wire in wiring.wires:
                if wire.source not in adj:
                    adj[wire.source] = set()
                adj[wire.source].add(wire.target)
        return adj

    def blocks_by_kind(self) -> dict[str, list[str]]:
        """Group blocks by their GDS role."""
        result = {
            "boundary": [], "control": [], "policy": [],
            "mechanism": [], "generic": [],
        }
        for bname, block in self.spec.blocks.items():
            result[block.kind].append(bname)
        return result

    def spaces_used_by(self, block_name: str) -> dict[str, list[str]]:
        """Which spaces does a block consume and produce?"""
        block = self.spec.blocks[block_name]
        return {
            "domain": [s.name for s in block.domain],
            "codomain": [s.name for s in block.codomain],
        }
```

### 4.9 serialize.py — JSON Round-Trip

```python
import json
from .spec import GDSSpec
from .types import TypeDef
from .spaces import Space
from .blocks import Block, BoundaryAction, ControlAction, Policy, Mechanism
from .state import Entity, StateVariable
from .wiring import Wiring, Wire


def spec_to_dict(spec: GDSSpec) -> dict:
    """Serialize a GDSSpec to a plain dict (JSON-compatible)."""
    return {
        "name": spec.name,
        "description": spec.description,
        "types": {
            name: {
                "name": t.name,
                "python_type": t.python_type.__name__,
                "description": t.description,
                "units": t.units,
                # Note: constraint functions are not serializable
            }
            for name, t in spec.types.items()
        },
        "spaces": {
            name: {
                "name": s.name,
                "schema": {
                    fname: tdef.name
                    for fname, tdef in s.schema.items()
                },
                "description": s.description,
            }
            for name, s in spec.spaces.items()
        },
        "entities": {
            name: {
                "name": e.name,
                "description": e.description,
                "variables": {
                    vname: {
                        "name": v.name,
                        "type": v.typedef.name,
                        "description": v.description,
                        "symbol": v.symbol,
                    }
                    for vname, v in e.variables.items()
                },
            }
            for name, e in spec.entities.items()
        },
        "blocks": {
            name: _block_to_dict(b)
            for name, b in spec.blocks.items()
        },
        "wirings": {
            name: {
                "name": w.name,
                "description": w.description,
                "blocks": list(w.blocks.keys()),
                "wires": [
                    {
                        "source": wire.source,
                        "target": wire.target,
                        "space": wire.space.name,
                        "optional": wire.optional,
                    }
                    for wire in w.wires
                ],
            }
            for name, w in spec.wirings.items()
        },
        "parameters": {
            name: {"name": t.name, "type": t.python_type.__name__}
            for name, t in spec.parameters.items()
        },
    }


def _block_to_dict(b: Block) -> dict:
    d = {
        "name": b.name,
        "kind": b.kind,
        "domain": [s.name for s in b.domain],
        "codomain": [s.name for s in b.codomain],
        "description": b.description,
        "params_used": b.params_used,
        "constraints": b.constraints,
    }
    if isinstance(b, Mechanism):
        d["updates"] = b.updates
    if hasattr(b, "options"):
        d["options"] = b.options
    return d


def spec_to_json(spec: GDSSpec, indent: int = 2) -> str:
    """Serialize to JSON string."""
    return json.dumps(spec_to_dict(spec), indent=indent)


# Loading from dict/JSON would reconstruct GDSSpec objects,
# but constraint functions need to be re-attached by the user
# (they aren't serializable). This is by design — JSON is
# an interchange format, not the source of truth.
```

---

## 5. Example Usage: Predator-Prey

```python
from gds_core.types import TypeDef, NonNegativeFloat, PositiveInt
from gds_core.spaces import Space, EMPTY
from gds_core.blocks import BoundaryAction, Policy, Mechanism
from gds_core.state import Entity, StateVariable
from gds_core.wiring import StackWiring
from gds_core.spec import GDSSpec
from gds_core.verify import SpecVerifier

# ── Types ──
Population = TypeDef("Population", int, constraint=lambda x: x >= 0)
Rate = TypeDef("Rate", float, constraint=lambda x: x > 0)

# ── Spaces ──
PreySignal = Space("PreySignal", {"prey_count": Population})
PredatorSignal = Space("PredatorSignal", {"predator_count": Population})
HuntResult = Space("HuntResult", {
    "prey_eaten": Population,
    "predators_fed": Population,
})

# ── State ──
prey = Entity("Prey", [
    StateVariable("population", Population, symbol="N"),
])
predator = Entity("Predator", [
    StateVariable("population", Population, symbol="P"),
])

# ── Blocks ──
observe = Policy(
    "Observe Populations",
    domain=(EMPTY,),
    codomain=(PreySignal, PredatorSignal),
    params_used=["birth_rate", "death_rate"],
)

hunt = Policy(
    "Hunt Prey",
    domain=(PreySignal, PredatorSignal),
    codomain=(HuntResult,),
    params_used=["hunt_efficiency"],
    options=["lotka_volterra", "ratio_dependent"],
)

update_prey = Mechanism(
    "Update Prey Population",
    domain=(HuntResult,),
    params_used=["birth_rate"],
    updates=[("Prey", "population")],
)

update_predator = Mechanism(
    "Update Predator Population",
    domain=(HuntResult,),
    params_used=["death_rate"],
    updates=[("Predator", "population")],
)

# ── Wiring ──
hunt_wiring = StackWiring(
    "Hunt Cycle",
    sequence=[observe, hunt, update_prey],  # simplified
)

# ── Spec ──
spec = GDSSpec("Predator-Prey Model")
for t in [Population, Rate]:
    spec.register_type(t)
for s in [PreySignal, PredatorSignal, HuntResult]:
    spec.register_space(s)
for e in [prey, predator]:
    spec.register_entity(e)
for b in [observe, hunt, update_prey, update_predator]:
    spec.register_block(b)
spec.register_wiring(hunt_wiring)
for p in ["birth_rate", "death_rate", "hunt_efficiency"]:
    spec.register_parameter(p, Rate)

# ── Validate & Verify ──
errors = spec.validate()
print(f"Validation errors: {errors}")

verifier = SpecVerifier(spec)
report = verifier.report()
print(f"Completeness: {report['completeness']}")
print(f"Determinism: {report['determinism']}")
print(f"Type safety: {report['type_safety']}")
```

---

## 6. What gds-core Does NOT Do

These are explicitly out of scope for the core package and should live in separate packages:

| Concern | Why it's separate | Candidate package |
|---------|------------------|-------------------|
| Mermaid diagram rendering | Presentation, not specification | `gds-viz` |
| Obsidian vault generation | Report format, not core logic | `gds-reports` |
| cadCAD model generation | Execution engine coupling | `gds-cadcad` |
| Simulation execution | Runtime, not design-time | `gds-sim` |
| Web UI / React frontend | Client concern (BDP's insight) | `gds-studio` |
| PDF/LaTeX report generation | Output format | `gds-reports` |

The core package should be importable with **zero dependencies** and usable in a Jupyter notebook, a CI pipeline, or as the backbone of any of the above tools.

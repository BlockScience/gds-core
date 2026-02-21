# GDS v0.2 Architecture Design Document

## Parameter Typing, Canonical Projection, and Tag Metadata

---

## 1. Executive Summary

GDS v0.2 extends the foundational dynamical system framework with **structural ontology only** — no execution semantics, no rendering. This preserves GDS as a declarative specification layer while enabling canonical formalization.

| Feature | Purpose | Layer |
|---------|---------|-------|
| **Parameter Typing** | Formal declaration of Θ as distinct from state X | gds-framework (core) |
| **Canonical Projection** | Pure structural derivation of `h: X → X` decomposition | gds-framework (core) |
| **Tag Metadata** | Inert semantic annotations for downstream consumers | gds-framework (core) |

**Key Architectural Decisions:**

1. **GDS is structural ontology, not behavioral engine** — No execution, simulation, optimization, or rendering
2. **Parameters define Θ at specification level only** — GDS does not define how Θ is sampled, assigned, or optimized
3. **Canonical projection is mandatory and pure** — Always derivable from SystemIR; never authoritative
4. **Tags are semantically neutral** — Metadata only; stripped at compile time; never affect verification or composition
5. **Rendering belongs in gds-viz** — All Mermaid, LaTeX, and diagram generation is out of scope for gds-framework

**Boundary Constraint:**
> GDS parameters define configuration space Θ at the specification level only. GDS does not define how Θ is sampled, assigned, or optimized. Execution engines must interpret Θ.

---

## 2. Mathematical Foundation

### 2.1 Core Dynamical System

The canonical GDS object:

```
h : X → X
```

With explicit decomposition:

```
h = f ∘ g
```

Where:
- **X** — State space (from Entities)
- **U** — Input space (from BoundaryActions)
- **D** — Decision space (outputs of Policies)
- **g** — Policy mapping: X × U → D
- **f** — State transition: X × D → X

### 2.2 Parameter Space Extension

Parameters define configuration space Θ structurally:

```
h_θ : X → X  where θ ∈ Θ
```

Θ is metadata at the specification level:
- Typed but not bound to values in GDS
- Referenced by blocks but not interpreted by GDS
- Available for canonical projection and downstream consumers
- Execution semantics delegated to domain engines

### 2.3 Invariants

- **State (X)** is the only mutable component during execution
- **Parameters (Θ)** are typed references, not values — GDS defines their schema, not their binding
- **Canonical projection** derives structure without execution
- **Tags** are inert metadata, never affecting structure, composition, or verification

---

## 3. Parameter System Design (Structural Only)

### 3.1 Core Classes

```python
from typing import Any, Callable
from pydantic import BaseModel, Field, ConfigDict

class ParameterDef(BaseModel):
    """
    Schema definition for a single parameter.

    Defines Θ structurally — types and constraints only.
    No values, no binding, no execution semantics.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    typedef: TypeDef
    description: str = ""
    bounds: tuple[Any, Any] | None = None  # Structural constraint


class ParameterSchema(BaseModel):
    """
    Defines the parameter space Θ at specification level.

    Immutable registry of parameter definitions.
    GDS does not interpret values — only validates structural references.
    """
    model_config = ConfigDict(frozen=True)

    parameters: dict[str, ParameterDef] = Field(default_factory=dict)

    def add(self, param: ParameterDef) -> "ParameterSchema":
        """Return new schema with added parameter (immutable)."""
        if param.name in self.parameters:
            raise ValueError(f"Parameter '{param.name}' already exists")
        new_params = dict(self.parameters)
        new_params[param.name] = param
        return self.model_copy(update={"parameters": new_params})

    def get(self, name: str) -> ParameterDef:
        return self.parameters[name]

    def names(self) -> set[str]:
        return set(self.parameters.keys())

    def validate_references(self, ref_names: set[str]) -> list[str]:
        """Validate that all referenced parameter names exist in schema."""
        errors = []
        for name in ref_names:
            if name not in self.parameters:
                errors.append(f"Referenced parameter '{name}' not defined in schema")
        return errors
```

### 3.2 Integration with Existing Classes

```python
class GDSSpec(BaseModel):
    """Extended to include parameter schema at specification level."""
    # ... existing fields ...

    # NEW: Parameter schema registry (structural only)
    parameter_schema: ParameterSchema = Field(default_factory=ParameterSchema)

    def register_parameter(self, param: ParameterDef) -> "GDSSpec":
        """Register a parameter definition (returns new instance)."""
        new_schema = self.parameter_schema.add(param)
        return self.model_copy(update={"parameter_schema": new_schema})


class Mechanism(Block):
    """Mechanisms can reference parameters from the spec."""
    # ... existing fields ...

    # NEW: Parameter names this mechanism references (structural only)
    parameters: tuple[str, ...] = ()


class SystemIR(BaseModel):
    """Compiled system includes aggregated parameter schema."""
    # ... existing fields ...

    # NEW: All parameters from composed blocks (structural registry)
    parameter_schema: ParameterSchema = Field(default_factory=ParameterSchema)
```

### 3.3 Verification Check: Parameter References

A new verification check validates parameter reference integrity:

```python
def check_parameter_references(system: SystemIR) -> list[Finding]:
    """
    PARAM-001: All parameter references in Mechanisms resolve
    to definitions in the ParameterSchema.

    Plugs into the existing verify() system alongside G-001..G-006
    and SC-001..SC-004.
    """
    findings = []
    for block in system.blocks:
        if isinstance(block, Mechanism):
            for param_name in block.parameters:
                if param_name not in system.parameter_schema.names():
                    findings.append(Finding(
                        severity=Severity.ERROR,
                        code="PARAM-001",
                        message=(
                            f"Mechanism '{block.name}' references unknown "
                            f"parameter '{param_name}'"
                        ),
                    ))
    return findings
```

### 3.4 Use Case Example

```python
# 1. Define parameter schema (structural only)
beta_param = ParameterDef(
    name="infection_rate",
    typedef=TypeDef(float),
    description="Probability of infection per contact",
    bounds=(0.0, 1.0),
)

spec = GDSSpec(
    name="SIR Model",
    blocks=[...],
    parameter_schema=ParameterSchema().add(beta_param),
)

# 2. Mechanism references parameter by name
infection_mech = Mechanism(
    name="Infection",
    interface=Interface(forward_in=(port("contacts"),)),
    updates=[("Population", "infected")],
    parameters=("infection_rate",),  # Structural reference only
)

# 3. Compile validates references
system = compile_system(spec)
# Raises if "infection_rate" not defined in schema

# 4. Canonical projection includes parameter schema
canonical = project_canonical(system)
# canonical.Theta contains the parameter schema

# 5. Domain package interprets parameters for execution
# (GDS does not define execution semantics)
```

---

## 4. Canonical Projection

### 4.1 Purpose

The canonical projection derives the formal GDS structure — X, Θ, U, D, g, f — from compiled SystemIR. It is:

- **Pure:** deterministic, stateless, no side effects
- **Derived:** always computable from SystemIR, never stored separately
- **Not authoritative:** SystemIR is ground truth; the projection is a read-only view
- **Cacheable:** same input always produces same output

### 4.2 Data Model

```python
class CanonicalGDS(BaseModel):
    """
    Canonical projection of SystemIR to formal GDS structure.

    Pure derivation — always computable, never authoritative.
    SystemIR remains ground truth.
    """
    model_config = ConfigDict(frozen=True)

    # Spaces
    X: ProductSpace        # State space (from Entities)
    Theta: ParameterSchema # Parameter space (schema only)
    U: ProductSpace        # Input space (from BoundaryAction outputs)
    D: ProductSpace        # Decision space (from Policy outputs)

    # Structural decomposition
    policy_blocks: tuple[str, ...]      # Block names composing g
    mechanism_blocks: tuple[str, ...]   # Block names composing f
    mechanism_order: tuple[str, ...]    # Topological execution order

    # Structure metadata
    is_temporal: bool  # True if system has temporal loops
```

**Design note:** `CanonicalGDS` holds **references to blocks by name**, not the blocks themselves. The spaces (X, U, D) are derived product spaces. There are no `PolicyMapping` or `StateTransition` wrapper classes — those are unnecessary abstractions over data already in SystemIR.

### 4.3 Derivation Algorithm

```python
def project_canonical(system: SystemIR) -> CanonicalGDS:
    """
    Pure function: SystemIR → CanonicalGDS

    Deterministic, stateless, cached.
    Never mutates SystemIR.
    """

    # 1. X = product of all Entity state variable spaces
    X = _derive_state_space(system)

    # 2. Θ = parameter schema (pass-through)
    Theta = system.parameter_schema

    # 3. U = product of all BoundaryAction forward_out spaces
    U = _derive_input_space(system)

    # 4. D = product of all Policy forward_out spaces
    D = _derive_decision_space(system)

    # 5. Identify policy and mechanism blocks
    policy_blocks = tuple(
        b.name for b in system.blocks
        if isinstance(b, (BoundaryAction, Policy))
    )
    mechanism_blocks = tuple(
        b.name for b in system.blocks
        if isinstance(b, Mechanism)
    )

    # 6. Topological sort of mechanisms by wiring dependencies
    mechanism_order = _topological_sort_mechanisms(
        mechanism_blocks, system.wirings
    )

    # 7. Temporal structure
    is_temporal = any(w.is_temporal for w in system.wirings)

    return CanonicalGDS(
        X=X, Theta=Theta, U=U, D=D,
        policy_blocks=policy_blocks,
        mechanism_blocks=mechanism_blocks,
        mechanism_order=mechanism_order,
        is_temporal=is_temporal,
    )


def _derive_state_space(system: SystemIR) -> ProductSpace:
    """X = product of all Entity state variable spaces."""
    return ProductSpace([
        sv.space
        for entity in system.entities
        for sv in entity.state_variables
    ])


def _derive_input_space(system: SystemIR) -> ProductSpace:
    """U = product of all BoundaryAction forward_out spaces."""
    return ProductSpace([
        block.interface.forward_out_space
        for block in system.blocks
        if isinstance(block, BoundaryAction)
    ])


def _derive_decision_space(system: SystemIR) -> ProductSpace:
    """D = product of all Policy forward_out spaces."""
    return ProductSpace([
        block.interface.forward_out_space
        for block in system.blocks
        if isinstance(block, Policy)
    ])
```

### 4.4 Verification Check: Canonical Well-formedness

```python
def check_canonical_wellformedness(system: SystemIR) -> list[Finding]:
    """
    CANON-001: Canonical projection is structurally valid.

    Validates:
    - At least one mechanism exists (f is non-empty)
    - State space X is non-empty (entities with variables exist)
    - All mechanism parameter references resolve
    """
    findings = []
    canonical = project_canonical(system)

    if not canonical.mechanism_blocks:
        findings.append(Finding(
            severity=Severity.WARNING,
            code="CANON-001",
            message="No mechanisms found — state transition f is empty",
        ))

    if not canonical.X.components:
        findings.append(Finding(
            severity=Severity.WARNING,
            code="CANON-002",
            message="State space X is empty — no entity variables defined",
        ))

    return findings
```

---

## 5. Tag Metadata

### 5.1 Core Design

Tags are a minimal `dict[str, str]` field on spec-layer objects. They carry no semantics within gds-framework — they exist for downstream consumers (visualization, documentation, domain packages).

```python
class Tagged(BaseModel):
    """
    Mixin providing inert semantic tags.

    Tags never affect compilation, verification, or composition.
    They are stripped at compile time and do not appear in SystemIR.
    """
    tags: dict[str, str] = Field(default_factory=dict)

    def with_tag(self, key: str, value: str) -> "Tagged":
        """Return new instance with added tag."""
        new_tags = dict(self.tags)
        new_tags[key] = value
        return self.model_copy(update={"tags": new_tags})

    def with_tags(self, **tags: str) -> "Tagged":
        """Return new instance with multiple tags added."""
        new_tags = dict(self.tags)
        new_tags.update(tags)
        return self.model_copy(update={"tags": new_tags})

    def has_tag(self, key: str, value: str | None = None) -> bool:
        """Check if tag exists (and optionally has specific value)."""
        if key not in self.tags:
            return False
        if value is not None:
            return self.tags[key] == value
        return True

    def get_tag(self, key: str, default: str | None = None) -> str | None:
        """Get tag value or default."""
        return self.tags.get(key, default)
```

Applied to existing classes:
```python
class Block(Tagged):       # Blocks support tagging
class Entity(Tagged):      # Entities support tagging
class GDSSpec(Tagged):     # Specifications support tagging
```

### 5.2 Compile-Time Stripping

Tags are **not preserved** in SystemIR. The compilation pipeline strips them:

```python
def compile_system(spec: GDSSpec, name: str = "system") -> SystemIR:
    """
    Tags stripped during compilation.
    SystemIR has no tags field — semantic neutrality enforced structurally.
    """
    compiled_blocks = [
        block.model_copy(update={"tags": {}})
        for block in spec.blocks
    ]
    compiled_entities = [
        entity.model_copy(update={"tags": {}})
        for entity in spec.entities
    ]
    return SystemIR(
        blocks=compiled_blocks,
        entities=compiled_entities,
        # ... other fields, no tags ...
    )
```

### 5.3 Intended Usage

Tags are consumed by **downstream packages**, not by gds-framework itself:

```python
# Spec author annotates blocks
sensor = AtomicBlock(
    name="Temperature Sensor",
    interface=Interface(forward_out=(port("Temperature"),)),
).with_tags(
    **{"control.role": "sensor", "control.loop": "outer"}
)

controller = AtomicBlock(
    name="PID Controller",
    interface=Interface(
        forward_in=(port("Temperature"),),
        forward_out=(port("Command"),),
    ),
).with_tags(
    **{"control.role": "controller", "control.loop": "outer"}
)

# gds-framework: tags have no effect on composition or verification
system = sensor >> controller  # Works identically with or without tags

# gds-viz (separate package): reads tags for architecture diagrams
# diagram = architecture_view(spec, group_by="control.loop")

# Domain package: reads tags for domain-specific validation
# findings = control_domain.validate_tags(spec)
```

**What gds-framework does NOT provide for tags:**
- No tag styling (`TagStyle`, CSS, colors)
- No tag conventions (`AGENT_CONVENTIONS`, `CONTROL_CONVENTIONS`)
- No tag validation (`DomainPackage.validate_tags()`)
- No tag-based rendering (`spec_to_architecture_mermaid()`)

All of these belong in gds-viz or domain packages.

---

## 6. Strict Boundaries & Invariants

### 6.1 GDS as Structural Ontology

**Invariant:** GDS defines structure, not behavior.

| In scope (gds-framework) | Out of scope (domain/viz packages) |
|--------------------------|-----------------------------------|
| Type definitions and constraints | Parameter value assignment |
| Block interfaces and composition | Execution and simulation |
| Parameter schema (Θ structure) | Parameter binding (θ ∈ Θ) |
| Canonical projection (data model) | Mermaid/LaTeX rendering |
| Tag data field | Tag styling and conventions |
| Structural verification | Domain-specific validation |

### 6.2 Spec ≠ Rendering ≠ Execution

This is the foundational separation from gds_deepdive.md, **strictly enforced** in v0.2:

```
gds-framework (this package)
├── Types, Spaces, Entities, Blocks
├── Composition operators (>>, |, .feedback(), .loop())
├── Compilation → SystemIR
├── Verification (G-001..G-006, SC-001..SC-004, PARAM-001, CANON-001)
├── Canonical projection → CanonicalGDS (data model)
├── Parameter schema (structural typing)
└── Tag metadata (inert dict[str, str])

gds-viz (separate package, consumes GDSSpec and CanonicalGDS)
├── canonical_to_mermaid(canonical: CanonicalGDS) → str
├── spec_to_architecture_mermaid(spec: GDSSpec) → str
├── system_to_mermaid(system: SystemIR) → str
├── TagStyle, tag-based styling
├── LaTeX rendering
└── All diagram generation

Domain packages (consume GDSSpec, SystemIR, CanonicalGDS)
├── Parameter value assignment (ParameterAssignment)
├── Stochastic mechanisms (Ω modeling)
├── Execution engines (simulate())
├── Domain-specific verification
├── Tag conventions and validation
└── Optimization, analysis, etc.
```

### 6.3 Canonical Projection Purity

**Invariant:** `project_canonical` is a pure function.

- Deterministic: same SystemIR → same CanonicalGDS
- Stateless: no side effects
- Read-only: never modifies SystemIR
- Cacheable: `@lru_cache` safe
- Not authoritative: SystemIR is ground truth

### 6.4 Parameter Boundary Rule

**Invariant:** GDS parameters define Θ at specification level only.

- `ParameterDef` contains type and structural constraints only
- No `ParameterAssignment` in gds-framework
- No binding logic in gds-framework
- Domain packages handle value assignment and interpretation
- If a value changes during execution, it is **state**, not a parameter

### 6.5 Tag Isolation

**Invariant:** Tags never affect compilation, verification, or composition.

- Tags stripped at compile time — SystemIR has no tags field
- Verification checks never read tags
- Composition operators ignore tags
- Tag content is opaque to gds-framework (just `dict[str, str]`)

---

## 7. Migration from v0.1

### 7.1 Backward Compatibility

**Guarantees:**
- All existing models work unchanged
- `parameter_schema` defaults to empty `ParameterSchema()`
- `parameters` on Mechanism defaults to `()`
- `tags` defaults to empty `{}`
- All 244 existing tests continue to pass
- No breaking changes to composition algebra, verification, or IR

### 7.2 Incremental Adoption

**Phase 1: No changes required**
```python
# Existing v0.1 code works unchanged
system = (sensor >> controller >> plant).feedback([...])
ir = compile_system("Thermostat", system)
report = verify(ir)
```

**Phase 2: Add parameter schema**
```python
spec = GDSSpec(
    name="My Model",
    blocks=[...],
    parameter_schema=ParameterSchema()
        .add(ParameterDef(name="alpha", typedef=TypeDef(float)))
        .add(ParameterDef(name="beta", typedef=TypeDef(float), bounds=(0, 1))),
)

mechanism = Mechanism(
    ...,
    parameters=("alpha", "beta"),  # Structural references
)
```

**Phase 3: Use canonical projection**
```python
ir = compile_system(spec)
canonical = project_canonical(ir)
# canonical.X, canonical.Theta, canonical.U, canonical.D available
# for downstream consumers (gds-viz, domain packages)
```

**Phase 4: Add tags**
```python
block = AtomicBlock(
    name="Agent A",
    interface=Interface(...),
).with_tags(**{"agent.role": "decision_maker", "agent.id": "alice"})
# Tags available on spec objects, stripped at compile time
```

---

## 8. Monorepo Structure: gds-viz

### 8.1 Why Monorepo

Visual validation is essential for spec development — you need to *see* your model to know if it's correct. But rendering code doesn't belong in the core specification package.

Solution: **gds-viz lives in the same repo as gds-framework**, as a separate package with its own `pyproject.toml`. Both packages share CI, versioning, and development workflow, but have independent install targets and a one-way dependency.

### 8.2 Repository Layout

```
gds-framework/                  # repo root
├── pyproject.toml              # core: gds-framework on PyPI
├── gds/                        # core source (specification layer)
│   ├── __init__.py
│   ├── blocks/
│   ├── compiler/
│   ├── ir/
│   ├── types/
│   ├── verification/
│   ├── spec.py
│   ├── spaces.py
│   ├── state.py
│   ├── query.py
│   └── serialize.py
├── tests/                      # core tests
├── packages/
│   └── gds-viz/                # viz: gds-viz on PyPI
│       ├── pyproject.toml      # depends on gds-framework
│       ├── gds_viz/
│       │   ├── __init__.py
│       │   ├── mermaid.py      # system_to_mermaid, block_to_mermaid (migrated from gds/visualization.py)
│       │   ├── canonical.py    # canonical_to_mermaid (new: canonical GDS diagrams)
│       │   ├── architecture.py # spec_to_architecture_mermaid (new: tag-based views)
│       │   └── styles.py       # TagStyle, DEFAULT_TAG_STYLES, domain conventions
│       └── tests/
├── examples/                   # shared examples (use both packages)
└── docs/
```

### 8.3 Workspace Configuration

Root `pyproject.toml` adds:

```toml
[tool.uv.workspace]
members = ["packages/*"]
```

`packages/gds-viz/pyproject.toml`:

```toml
[project]
name = "gds-viz"
version = "0.1.0"
description = "Visualization utilities for GDS specifications"
requires-python = ">=3.12"
dependencies = [
    "gds-framework>=0.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["gds_viz"]
```

### 8.4 Dependency Direction (Enforced)

```
gds-framework  ←──depends──  gds-viz
     │                          │
     │  NEVER imports from      │  imports from gds.*
     │  gds_viz.*               │
     ▼                          ▼
  SystemIR, CanonicalGDS  →  Mermaid strings, LaTeX, diagrams
  GDSSpec (with tags)     →  Architecture-aware views
```

**Rule:** `gds/` never imports from `gds_viz/`. This is enforced by the package boundary — gds-framework has no dependency on gds-viz.

### 8.5 What Lives Where

| Function | Current location | v0.2 location | Notes |
|----------|-----------------|---------------|-------|
| `system_to_mermaid()` | `gds/visualization.py` | `gds_viz/mermaid.py` | Migrated from core |
| `block_to_mermaid()` | `gds/visualization.py` | `gds_viz/mermaid.py` | Migrated from core |
| `canonical_to_mermaid()` | (doesn't exist) | `gds_viz/canonical.py` | New: renders CanonicalGDS |
| `spec_to_architecture_mermaid()` | (doesn't exist) | `gds_viz/architecture.py` | New: tag-based grouping |
| `TagStyle`, styling | (doesn't exist) | `gds_viz/styles.py` | New: tag visual conventions |
| Domain tag conventions | (doesn't exist) | `gds_viz/styles.py` | New: AGENT/CONTROL/GAME conventions |

### 8.6 Migration of Existing Visualization Code

The existing `gds/visualization.py` (200 lines, tested) moves to gds-viz with a deprecation shim:

```python
# gds/visualization.py (v0.2 — deprecation shim)
"""Deprecated: use gds_viz instead.

This module will be removed in v0.3.
"""
import warnings

def system_to_mermaid(*args, **kwargs):
    warnings.warn(
        "gds.visualization is deprecated. Install gds-viz and use "
        "gds_viz.system_to_mermaid instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from gds_viz.mermaid import system_to_mermaid as _impl
    return _impl(*args, **kwargs)

def block_to_mermaid(*args, **kwargs):
    warnings.warn(
        "gds.visualization is deprecated. Install gds-viz and use "
        "gds_viz.block_to_mermaid instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from gds_viz.mermaid import block_to_mermaid as _impl
    return _impl(*args, **kwargs)
```

This preserves backward compatibility while guiding users to the new package.

### 8.7 Developer Workflow

```bash
# Install both packages in development mode
uv sync                              # installs gds-framework
cd packages/gds-viz && uv sync       # installs gds-viz (with editable gds-framework)

# Or from repo root with workspace
uv sync --all-packages               # installs everything

# Run core tests
uv run pytest tests/ -v

# Run viz tests
uv run pytest packages/gds-viz/tests/ -v

# Validate a model visually
uv run python -c "
from examples.sir_epidemic.model import build_system
from gds_viz import system_to_mermaid
print(system_to_mermaid(build_system()))
"
```

### 8.8 gds-viz Scope

gds-viz consumes data models from gds-framework and produces visual output:

**Inputs (from gds-framework):**
- `SystemIR` — compiled block graph
- `CanonicalGDS` — formal GDS projection
- `GDSSpec` — specification with tags
- `Block` — composition tree (pre-compilation)

**Outputs (rendering):**
- Mermaid flowchart strings
- LaTeX mathematical notation (future)
- Architecture-aware diagrams grouped by tags
- Canonical GDS diagrams (X, Θ, U, D, g, f)

**gds-viz owns:**
- All Mermaid generation code
- Tag styling (`TagStyle`, CSS, colors, shapes)
- Domain tag conventions (`AGENT_CONVENTIONS`, `CONTROL_CONVENTIONS`, etc.)
- Tag validation against conventions
- Architecture view logic (grouping by tag, subgraph layout)
- Hierarchy rendering

---

## 9. New Verification Checks

v0.2 adds verification checks to the existing pluggable system:

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| PARAM-001 | Parameter reference integrity | ERROR | All `Mechanism.parameters` entries resolve to `ParameterSchema` definitions |
| CANON-001 | Empty state transition | WARNING | No mechanisms found — f is trivially empty |
| CANON-002 | Empty state space | WARNING | No entity variables — X is trivially empty |

These plug into the existing `verify(system, checks=None)` infrastructure alongside G-001..G-006 and SC-001..SC-004.

---

## 10. Summary

| Component | What gds-framework provides | What gds-viz provides |
|-----------|---------------------------|---------------------|
| **Parameters** | `ParameterDef`, `ParameterSchema` — structural typing of Θ | (n/a) |
| **Canonical Projection** | `CanonicalGDS` data model, `project_canonical()` pure function | `canonical_to_mermaid()` rendering |
| **Tags** | `dict[str, str]` on Block/Entity/GDSSpec, stripped at compile | Tag styling, conventions, architecture views |
| **Structural viz** | (n/a — migrated out) | `system_to_mermaid()`, `block_to_mermaid()` |

**Explicitly NOT in gds-framework v0.2:**
- Parameter value assignment / binding (domain package concern)
- Execution / simulation semantics (domain package concern)
- Stochastic mechanisms / Ω modeling (domain package concern)
- Mermaid / LaTeX / diagram generation (gds-viz concern)
- Tag styling, conventions, validation (gds-viz / domain package concern)

**Implementation order:**

Phase 1 — Core features (gds-framework):
1. `ParameterDef` and `ParameterSchema` classes
2. `parameters: tuple[str, ...]` field on `Mechanism`
3. `parameter_schema` field on `GDSSpec` and `SystemIR`
4. `PARAM-001` verification check
5. `ProductSpace` class (for canonical projection)
6. `CanonicalGDS` data model
7. `project_canonical()` derivation function
8. `CANON-001`, `CANON-002` verification checks
9. `Tagged` mixin on Block, Entity, GDSSpec
10. Compile-time tag stripping in compilation pipeline
11. Tests for all of the above

Phase 2 — Visualization package (gds-viz):
12. Set up `packages/gds-viz/` with pyproject.toml and uv workspace
13. Migrate `gds/visualization.py` → `gds_viz/mermaid.py`
14. Add deprecation shim in `gds/visualization.py`
15. Implement `gds_viz/canonical.py` — canonical GDS diagrams
16. Implement `gds_viz/architecture.py` — tag-based architecture views
17. Implement `gds_viz/styles.py` — TagStyle, domain conventions
18. Migrate and update visualization tests
19. Update examples to import from `gds_viz`

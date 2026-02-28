# CLAUDE.md — gds-framework

## Package Identity

**This is NOT Neo4j GDS (Graph Data Science). This is NOT GDSFactory (photonics).**

`gds-framework` is a Python library for typed compositional specifications of complex systems, grounded in Generalized Dynamical Systems (GDS) theory. It provides a composition algebra for blocks with bidirectional typed interfaces, a specification registry, and formal verification.

- **PyPI**: `pip install gds-framework` (or `uv add gds-framework`)
- **Import**: `import gds` (not `gds_framework`)
- **Repository**: `packages/gds-framework/` in the `gds-core` monorepo
- **Theory**: [GDS (Roxin; Zargham & Shorish)](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc)

## Quick API Reference

Every public symbol is importable from `gds`:

```python
from gds import (
    # Composition algebra (Layer 0)
    Block, AtomicBlock,                          # base block types
    StackComposition, ParallelComposition,        # >> and | operators
    FeedbackLoop, TemporalLoop,                   # .feedback() and .loop()
    Wiring,                                       # explicit wiring between blocks
    Interface, Port, port,                        # bidirectional typed interfaces

    # Block roles
    BoundaryAction,     # exogenous input (forward_in must be empty)
    Policy,             # decision logic (maps signals to mechanism inputs)
    Mechanism,          # state update (only block that writes state, no backward ports)
    ControlAction,      # endogenous control (reads state, emits signals)
    HasParams, HasConstraints, HasOptions,  # structural protocols

    # Specification framework (Layer 1)
    GDSSpec, SpecWiring, Wire,              # spec registry + wiring declarations
    TypeDef,                                 # runtime-constrained type definition
    Space, EMPTY, TERMINAL,                  # typed product spaces
    Entity, StateVariable,                   # state model
    ParameterDef, ParameterSchema,           # parameter space (Theta)
    CanonicalGDS, project_canonical,         # h = f . g decomposition
    Tagged,                                  # inert tag mixin

    # Convenience helpers (preferred for new code)
    typedef, space, entity, state_var,       # factory functions
    interface,                               # Interface from port name strings

    # Compiler (Layer 0 -> IR)
    compile_system,                          # Block tree -> SystemIR
    flatten_blocks, extract_wirings, extract_hierarchy,  # individual stages
    StructuralWiring, WiringOrigin,          # compiler intermediates

    # IR models
    SystemIR, BlockIR, WiringIR,             # flat intermediate representation
    HierarchyNodeIR, InputIR,                # hierarchy + inputs
    CompositionType, FlowDirection,          # enums
    sanitize_id,                             # name -> safe ID

    # Serialization
    IRDocument, IRMetadata, save_ir, load_ir,  # IR JSON persistence
    spec_to_dict, spec_to_json,                # spec serialization

    # Verification
    verify,                                  # verify(system: SystemIR) -> VerificationReport
    Finding, Severity, VerificationReport,   # verification results

    # Semantic checks — these take GDSSpec, NOT SystemIR:
    check_completeness,                      # (spec) -> list[Finding]  SC-001
    check_determinism,                       # (spec) -> list[Finding]  SC-002
    check_reachability,                      # (spec, from_block, to_block) -> list[Finding]  SC-003
    check_type_safety,                       # (spec) -> list[Finding]  SC-004
    check_parameter_references,              # (spec) -> list[Finding]  SC-005
    check_canonical_wellformedness,          # (spec) -> list[Finding]  SC-006/SC-007

    # Custom checks
    gds_check, get_custom_checks, all_checks,  # decorator + registries

    # Built-in TypeDefs
    Probability, NonNegativeFloat, PositiveInt,  # constrained numeric types
    TokenAmount, AgentID, Timestamp,

    # Token system
    tokenize, tokens_overlap, tokens_subset,  # port name matching

    # Query engine
    SpecQuery,                               # dependency analysis on GDSSpec

    # Errors
    GDSError, GDSTypeError, GDSCompositionError,
)
```

## Constructor Signatures

### Convenience helpers (recommended)

```python
def typedef(name: str, python_type: type, *, constraint: Callable | None = None,
            description: str = "", units: str | None = None) -> TypeDef

def space(name: str, *, description: str = "", **fields: TypeDef) -> Space

def state_var(td: TypeDef, *, symbol: str = "", description: str = "") -> StateVariable

def entity(name: str, *, description: str = "", **variables: StateVariable) -> Entity

def interface(*, forward_in: list[str] | None = None, forward_out: list[str] | None = None,
              backward_in: list[str] | None = None, backward_out: list[str] | None = None) -> Interface

def compile_system(name: str, root: Block,
                   block_compiler: Callable | None = None,
                   wiring_emitter: Callable | None = None,
                   composition_type: CompositionType = CompositionType.SEQUENTIAL,
                   source: str = "", inputs: list[InputIR] | None = None) -> SystemIR

def verify(system: SystemIR, checks: list[Callable] | None = None) -> VerificationReport
```

### Direct constructors

```python
TypeDef(name: str, python_type: type, description: str = "",
        constraint: Callable | None = None, units: str | None = None)  # frozen

Space(name: str, fields: dict[str, TypeDef] = {}, description: str = "")  # frozen

StateVariable(name: str, typedef: TypeDef, description: str = "", symbol: str = "")  # frozen

Entity(name: str, variables: dict[str, StateVariable] = {}, description: str = "")  # frozen

GDSSpec(name: str, description: str = "")  # mutable registry
# Methods: .register_type(t), .register_space(s), .register_entity(e),
#          .register_block(b), .register_wiring(w), .register_parameter(p)
#          .collect(*objects)  — bulk register TypeDef|Space|Entity|Block|ParameterDef
#          .validate_spec() -> list[str]

Wire(source: str, target: str, space: str = "", optional: bool = False)  # frozen
SpecWiring(name: str, block_names: list[str] = [], wires: list[Wire] = [],
           description: str = "")  # frozen

ParameterDef(name: str, typedef: TypeDef, description: str = "",
             bounds: tuple[Any, Any] | None = None)  # frozen
```

### Block roles

```python
# All roles take: name: str, interface: Interface, kind: str (auto-set)
BoundaryAction(name=..., interface=interface(forward_out=["Signal"]))
# Constraint: forward_in must be empty

Policy(name=..., interface=interface(forward_in=["Signal"], forward_out=["Command"]))
# No extra constraints

Mechanism(name=..., interface=interface(forward_in=["Command"]),
          updates=[("entity_name", "variable_name")])
# Constraint: backward_in and backward_out must be empty

ControlAction(name=..., interface=interface(forward_in=["State"], forward_out=["Control"]))
# No extra constraints

# All roles support: params_used: list[str], constraints: list[str]
# BoundaryAction, Policy, ControlAction also support: options: list[str]
```

## Minimal Complete Example

```python
import gds

# 1. Define types
Temperature = gds.typedef("Temperature", float, units="celsius")
HeaterCommand = gds.typedef("HeaterCommand", float)

# 2. Define state
temp_entity = gds.entity("Room", temperature=gds.state_var(Temperature))

# 3. Define blocks
sensor = gds.BoundaryAction(
    name="Sensor",
    interface=gds.interface(forward_out=["Temperature"]),
)
controller = gds.Policy(
    name="Controller",
    interface=gds.interface(forward_in=["Temperature"], forward_out=["Heater Command"]),
)
heater = gds.Mechanism(
    name="Heater",
    interface=gds.interface(forward_in=["Heater Command"]),
    updates=[("Room", "temperature")],
)

# 4. Compose (>> auto-wires by token overlap)
system = sensor >> controller >> heater

# 5. Compile to IR
system_ir = gds.compile_system("thermostat", system)

# 6. Verify
report = gds.verify(system_ir)
assert report.errors == 0

# 7. Build spec (optional — for semantic analysis)
spec = gds.GDSSpec(name="thermostat")
spec.collect(Temperature, HeaterCommand, temp_entity, sensor, controller, heater)
canonical = gds.project_canonical(spec)  # derives h = f . g
```

## Architecture

### Two-Layer Design

**Layer 0 — Composition Algebra** (`blocks/`, `compiler/`, `ir/`, `verification/generic_checks.py`):
Domain-neutral engine. Blocks with bidirectional typed interfaces, composed via `>>`, `|`, `.feedback()`, `.loop()`. A 3-stage compiler flattens composition trees into flat IR. Six generic checks (G-001..G-006) validate structural properties.

**Layer 1 — Specification Framework** (`spec.py`, `canonical.py`, `state.py`, `spaces.py`, `types/`):
GDS theory layer. `GDSSpec` registry for types, spaces, entities, blocks, wirings, parameters. `project_canonical()` derives formal `h = f . g` decomposition. Seven semantic checks (SC-001..SC-007) validate domain properties.

Layers are loosely coupled: use the composition algebra without `GDSSpec`, or use `GDSSpec` without the compiler.

### Two Type Systems

1. **Token-based** (`types/tokens.py`) — structural set matching at composition time. Port names auto-tokenize by splitting on ` + ` and `, ` then lowercasing: `"Temperature + Setpoint"` -> `{"temperature", "setpoint"}`. Plain spaces are NOT delimiters: `"Heater Command"` -> `{"heater command"}` (one token). The `>>` operator auto-wires by token overlap.

2. **TypeDef-based** (`types/typedef.py`) — runtime validation at the data level. Wraps Python type + optional constraint predicate. Used by Spaces and Entities. Never called during compilation.

### Compilation Pipeline

```
Block tree -> flatten() -> list[AtomicBlock] -> block_compiler() -> list[BlockIR]
           -> _walk_wirings() -> list[WiringIR] (explicit + auto-wired)
           -> _extract_hierarchy() -> HierarchyNodeIR tree
           = SystemIR(blocks, wirings, hierarchy)
```

### Block Hierarchy (Sealed)

5 concrete Block types. Domain packages subclass `AtomicBlock` only:
- `AtomicBlock` — leaf node
- `StackComposition` (`>>`) — sequential, validates token overlap
- `ParallelComposition` (`|`) — independent
- `FeedbackLoop` (`.feedback()`) — backward within timestep, CONTRAVARIANT
- `TemporalLoop` (`.loop()`) — forward across timesteps, COVARIANT only

### Verification

```python
# Generic checks on SystemIR (structural topology)
report = gds.verify(system_ir)  # runs G-001..G-006

# Semantic checks on GDSSpec (domain properties)
from gds import check_completeness, check_type_safety
# SC-001..SC-007: completeness, determinism, reachability, type safety,
#                 parameter references, canonical wellformedness

# Custom checks via decorator
@gds.gds_check("CUSTOM-001", gds.Severity.WARNING)
def my_check(system: gds.SystemIR) -> list[gds.Finding]: ...
```

## Key Conventions

- All data models are Pydantic v2 `BaseModel` — frozen for value objects, mutable for registries
- `@model_validator(mode="after")` returning `Self` for construction-time invariant enforcement
- Absolute imports only (`from gds.blocks.base import ...`)
- Tags (`Tagged` mixin) are inert — stripped at compile time, never affect verification
- Parameters (Theta) are structural metadata — GDS never assigns values or binds them
- `GDSSpec.collect()` type-dispatches TypeDef/Space/Entity/Block/ParameterDef
- PyPI name is `gds-framework`, import name is `gds` (mapped via `[tool.hatch.build.targets.wheel]`)

## Commands

```bash
uv sync                                    # Install dependencies
uv run --package gds-framework pytest packages/gds-framework/tests -v  # Run all tests
uv run --package gds-framework pytest packages/gds-framework/tests/test_blocks.py -v  # Single file
uv build --package gds-framework           # Build wheel
uv run python -c "import gds; print(gds.__version__)"  # Verify install
```

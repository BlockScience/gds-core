# API Quick Reference

A compact cheatsheet of every public constructor and helper in `gds-framework`. For full docstrings and source, see the [API Reference](api/init.md) pages.

---

## Imports

Everything below is importable directly from the top-level `gds` package:

```python
from gds import (
    # Types
    TypeDef, typedef,
    Probability, NonNegativeFloat, PositiveInt, TokenAmount, AgentID, Timestamp,
    # State
    Entity, StateVariable, entity, state_var,
    # Spaces
    Space, space, EMPTY, TERMINAL,
    # Blocks & Roles
    AtomicBlock, Block,
    BoundaryAction, Policy, Mechanism, ControlAction,
    Interface, Port, port, interface,
    # Composition
    StackComposition, ParallelComposition, FeedbackLoop, TemporalLoop, Wiring,
    # Specification
    GDSSpec, SpecWiring, Wire,
    # Parameters
    ParameterDef, ParameterSchema,
    # Canonical projection
    CanonicalGDS, project_canonical,
    # Compilation
    compile_system, SystemIR, BlockIR, WiringIR, HierarchyNodeIR,
    flatten_blocks, extract_wirings, extract_hierarchy,
    StructuralWiring, WiringOrigin,
    # Verification
    verify, Finding, Severity, VerificationReport,
    all_checks, gds_check, get_custom_checks,
    # Serialization
    spec_to_dict, spec_to_json, save_ir, load_ir, IRDocument, IRMetadata,
    # Query
    SpecQuery,
    # Tokens
    tokenize, tokens_overlap, tokens_subset,
)
```

---

## Types

### `typedef(name, python_type, *, constraint=None, description="", units=None)`

Factory for `TypeDef`. Wraps a Python type with an optional runtime constraint predicate.

```python
from gds import typedef

Rate = typedef("Rate", float, constraint=lambda x: x >= 0, units="1/time")
Name = typedef("Name", str, description="Human-readable label")
```

### `TypeDef`

Direct Pydantic constructor (frozen model).

```python
from gds import TypeDef

Rate = TypeDef(
    name="Rate",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Non-negative rate",
    units="1/time",
)
Rate.check_value(0.5)   # True
Rate.check_value(-1.0)  # False
```

### Built-in types

| Name | Python type | Constraint |
|------|-------------|------------|
| `Probability` | `float` | `0.0 <= x <= 1.0` |
| `NonNegativeFloat` | `float` | `x >= 0` |
| `PositiveInt` | `int` | `x > 0` |
| `TokenAmount` | `float` | `x >= 0` (units: tokens) |
| `AgentID` | `str` | none |
| `Timestamp` | `float` | `x >= 0` (units: seconds) |

---

## State

### `state_var(td, *, symbol="", description="")`

Create a `StateVariable` from a `TypeDef`. The name is resolved by `entity()` from its keyword argument key.

```python
from gds import typedef, state_var

Population = typedef("Population", float, constraint=lambda x: x >= 0)
pop = state_var(Population, symbol="S", description="Susceptible count")
```

### `entity(name, *, description="", **variables)`

Create an `Entity` with `StateVariable` keyword arguments. Each kwarg key becomes the variable name.

```python
from gds import typedef, state_var, entity

Pop = typedef("Population", float, constraint=lambda x: x >= 0)

population = entity(
    "Population",
    description="SIR compartments",
    susceptible=state_var(Pop, symbol="S"),
    infected=state_var(Pop, symbol="I"),
    recovered=state_var(Pop, symbol="R"),
)
```

### `StateVariable`

Direct constructor (frozen model).

```python
from gds import StateVariable, TypeDef

Pop = TypeDef(name="Population", python_type=float)
sv = StateVariable(name="susceptible", typedef=Pop, symbol="S")
```

### `Entity`

Direct constructor (frozen model, supports tags).

```python
from gds import Entity

e = Entity(name="Population", variables={"susceptible": sv, "infected": sv2})
e.validate_state({"susceptible": 100.0, "infected": 10.0})  # [] (no errors)
```

---

## Spaces

### `space(name, *, description="", **fields)`

Create a `Space` with `TypeDef` keyword arguments.

```python
from gds import typedef, space

Rate = typedef("Rate", float, constraint=lambda x: x >= 0)

infection_space = space(
    "Infection Signal",
    description="Carries the infection rate",
    rate=Rate,
)
```

### `Space`

Direct constructor (frozen model).

```python
from gds import Space, TypeDef

Rate = TypeDef(name="Rate", python_type=float)
s = Space(name="Infection Signal", fields={"rate": Rate})
s.validate_data({"rate": 0.1})  # [] (no errors)
```

### Sentinel spaces

| Name | Purpose |
|------|---------|
| `EMPTY` | No data flows through this port |
| `TERMINAL` | Signal terminates here (state write) |

---

## Blocks and Roles

### `interface(*, forward_in=None, forward_out=None, backward_in=None, backward_out=None)`

Create an `Interface` from lists of port name strings. Each string is auto-tokenized into a `Port`.

```python
from gds import interface

iface = interface(
    forward_in=["Infection Rate"],
    forward_out=["New Infections"],
)
```

### `port(name)`

Create a single `Port` with auto-tokenized type tokens.

```python
from gds import port

p = port("Infection Rate")
# p.type_tokens == frozenset({"infection", "rate"})
```

### `BoundaryAction(name, interface, *, options=[], params_used=[], constraints=[])`

Exogenous input block. Enforces `forward_in = ()` (no internal forward inputs).

```python
from gds import BoundaryAction, interface

exo = BoundaryAction(
    name="Environment",
    interface=interface(forward_out=["Temperature"]),
    params_used=["ambient_temp"],
)
```

### `Policy(name, interface, *, options=[], params_used=[], constraints=[])`

Decision logic block. Maps signals to mechanism inputs.

```python
from gds import Policy, interface

decide = Policy(
    name="Infection Policy",
    interface=interface(
        forward_in=["Contact Rate", "Population State"],
        forward_out=["Infection Rate"],
    ),
    options=["frequency_dependent", "density_dependent"],
    params_used=["beta"],
)
```

### `Mechanism(name, interface, *, updates=[], params_used=[], constraints=[])`

State update block. The only block type that writes to state. Enforces no backward ports.

```python
from gds import Mechanism, interface

update = Mechanism(
    name="Update Infected",
    interface=interface(
        forward_in=["New Infections"],
    ),
    updates=[("Population", "infected"), ("Population", "susceptible")],
)
```

### `ControlAction(name, interface, *, options=[], params_used=[], constraints=[])`

Endogenous control block. Reads state, emits control signals.

```python
from gds import ControlAction, interface

ctrl = ControlAction(
    name="Observer",
    interface=interface(
        forward_in=["Population State"],
        forward_out=["Control Signal"],
    ),
)
```

---

## Composition Operators

All operators are methods on `Block` and return composite blocks.

### `a >> b` -- Stack (sequential) composition

Chains blocks so the first's `forward_out` feeds the second's `forward_in`. Auto-wires by token overlap when no explicit wiring is provided.

```python
system = boundary >> policy >> mechanism
```

### `a | b` -- Parallel composition

Runs blocks side-by-side with no shared wires.

```python
inputs = boundary_a | boundary_b
```

### `block.feedback(wiring)` -- Feedback loop

Backward feedback within a single timestep. Wiring connects `backward_out` to `backward_in`.

```python
from gds import Wiring
from gds.ir.models import FlowDirection

system = (policy >> mechanism).feedback([
    Wiring(
        source_block="Update Infected",
        source_port="State Feedback",
        target_block="Infection Policy",
        target_port="Population State",
        direction=FlowDirection.CONTRAVARIANT,
    ),
])
```

### `block.loop(wiring, exit_condition="")` -- Temporal loop

Forward iteration across timesteps. All temporal wiring must be `COVARIANT`.

```python
system = (boundary >> policy >> mechanism).loop(
    wiring=[
        Wiring(
            source_block="Update Infected",
            source_port="Population State",
            target_block="Infection Policy",
            target_port="Population State",
        ),
    ],
    exit_condition="t >= 100",
)
```

### `Wiring(source_block, source_port, target_block, target_port, direction=COVARIANT)`

Explicit connection between two blocks (frozen model).

```python
from gds import Wiring
from gds.ir.models import FlowDirection

w = Wiring(
    source_block="A",
    source_port="Output",
    target_block="B",
    target_port="Input",
    direction=FlowDirection.COVARIANT,
)
```

### `StackComposition(name, first, second, wiring=[])`

Explicit constructor for `>>`. Use when you need custom wiring between stages.

```python
from gds import StackComposition, Wiring

composed = StackComposition(
    name="Custom Stack",
    first=policy,
    second=mechanism,
    wiring=[
        Wiring(
            source_block="Policy",
            source_port="Rate",
            target_block="Mechanism",
            target_port="Delta",
        ),
    ],
)
```

---

## Specification

### `GDSSpec(name, description="")`

Central registry that ties types, spaces, entities, blocks, wirings, and parameters into a validated specification. All `register_*` methods are chainable.

```python
from gds import GDSSpec

spec = GDSSpec(name="SIR Model", description="Susceptible-Infected-Recovered")
```

### `.collect(*objects)`

Bulk-register `TypeDef`, `Space`, `Entity`, `Block`, and `ParameterDef` instances by type dispatch.

```python
spec.collect(Rate, Pop, infection_space, population, boundary, policy, mechanism)
```

### `.register_type(t)` / `.register_space(s)` / `.register_entity(e)` / `.register_block(b)`

Individual registration methods. Raise `ValueError` on duplicate names.

```python
spec.register_type(Rate).register_space(infection_space).register_entity(population)
```

### `.register_wiring(w)`

Register a `SpecWiring` (not handled by `.collect()`).

```python
from gds import SpecWiring, Wire

spec.register_wiring(SpecWiring(
    name="Main Wiring",
    block_names=["Environment", "Infection Policy", "Update Infected"],
    wires=[
        Wire(source="Environment", target="Infection Policy"),
        Wire(source="Infection Policy", target="Update Infected"),
    ],
))
```

### `.register_parameter(param_or_name, typedef=None)`

Register a `ParameterDef` or use the `(name, typedef)` shorthand.

```python
from gds import ParameterDef

spec.register_parameter(ParameterDef(name="beta", typedef=Rate))
# or shorthand:
spec.register_parameter("beta", Rate)
```

### `.validate_spec()`

Run structural validation. Returns a list of error strings (empty means valid).

```python
errors = spec.validate_spec()
assert errors == []
```

### `Wire(source, target, space="", optional=False)`

A connection between two blocks in a `SpecWiring` (frozen model).

### `SpecWiring(name, block_names=[], wires=[], description="")`

A named composition of blocks connected by wires (frozen model).

---

## Parameters

### `ParameterDef(name, typedef, *, description="", bounds=None)`

Schema definition for a single parameter dimension (frozen model).

```python
from gds import ParameterDef, typedef

Rate = typedef("Rate", float, constraint=lambda x: x >= 0)
beta = ParameterDef(name="beta", typedef=Rate, bounds=(0.0, 1.0))
beta.check_value(0.5)  # True
```

### `ParameterSchema`

Immutable registry of `ParameterDef` instances. Usually accessed through `GDSSpec.parameter_schema`.

```python
from gds import ParameterSchema, ParameterDef

schema = ParameterSchema()
schema = schema.add(beta)  # returns new schema (immutable)
"beta" in schema  # True
```

---

## Canonical Projection

### `project_canonical(spec)`

Pure function: `GDSSpec` to `CanonicalGDS`. Derives the formal `h = f . g` decomposition.

```python
from gds import project_canonical

canonical = project_canonical(spec)
print(canonical.formula())       # "h_theta : X -> X  (h = f_theta o g_theta, theta in Theta)"
print(canonical.state_variables)  # (("Population", "susceptible"), ...)
print(canonical.boundary_blocks)  # ("Environment",)
print(canonical.policy_blocks)    # ("Infection Policy",)
print(canonical.mechanism_blocks) # ("Update Infected",)
```

### `CanonicalGDS`

Frozen model with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `state_variables` | `tuple[tuple[str, str], ...]` | `(entity, variable)` pairs forming X |
| `parameter_schema` | `ParameterSchema` | Parameter space Theta |
| `input_ports` | `tuple[tuple[str, str], ...]` | `(block, port)` from BoundaryAction outputs |
| `decision_ports` | `tuple[tuple[str, str], ...]` | `(block, port)` from Policy outputs |
| `boundary_blocks` | `tuple[str, ...]` | BoundaryAction block names |
| `control_blocks` | `tuple[str, ...]` | ControlAction block names |
| `policy_blocks` | `tuple[str, ...]` | Policy block names |
| `mechanism_blocks` | `tuple[str, ...]` | Mechanism block names |
| `update_map` | `tuple[tuple[str, tuple[...]], ...]` | Mechanism update targets |

---

## Compilation

### `compile_system(name, root, *, block_compiler=None, wiring_emitter=None, composition_type=SEQUENTIAL, source="", inputs=None)`

Compile a `Block` composition tree into a flat `SystemIR`.

```python
from gds import compile_system

system_ir = compile_system("SIR", root=boundary >> policy >> mechanism)
print(system_ir.blocks)    # list[BlockIR]
print(system_ir.wirings)   # list[WiringIR]
print(system_ir.hierarchy) # HierarchyNodeIR tree
```

### `flatten_blocks(root, block_compiler)`

Stage 1: walk the composition tree and map each leaf through a callback.

### `extract_wirings(root, wiring_emitter=None)`

Stage 2: walk the tree and emit all wirings (explicit, auto-wired, feedback, temporal).

### `extract_hierarchy(root)`

Stage 3: build a `HierarchyNodeIR` tree with flattened sequential/parallel chains.

---

## Verification

### `verify(system, checks=None)`

Run verification checks against a `SystemIR`. Returns a `VerificationReport`.

```python
from gds import compile_system, verify

system_ir = compile_system("SIR", root=composed)
report = verify(system_ir)

print(report.errors)         # count of failed ERROR-level checks
print(report.warnings)       # count of failed WARNING-level checks
print(report.checks_passed)  # count of passed checks
print(report.checks_total)   # total checks run
```

### Built-in generic checks (G-001 to G-006)

| Check | ID | What it validates |
|-------|----|-------------------|
| `check_g001_domain_codomain_matching` | G-001 | Domain/codomain port matching |
| `check_g002_signature_completeness` | G-002 | All ports have signatures |
| `check_g003_direction_consistency` | G-003 | Wiring direction consistency |
| `check_g004_dangling_wirings` | G-004 | No wirings reference missing blocks |
| `check_g005_sequential_type_compatibility` | G-005 | Sequential type token compatibility |
| `check_g006_covariant_acyclicity` | G-006 | No cycles in covariant wirings |

### `@gds_check(check_id, severity=Severity.ERROR)`

Decorator to register custom verification checks.

```python
from gds import gds_check, Finding, Severity
from gds.ir.models import SystemIR

@gds_check("CUSTOM-001", Severity.WARNING)
def check_no_orphan_blocks(system: SystemIR) -> list[Finding]:
    ...
```

### `all_checks()`

Returns built-in generic checks + all custom-registered checks.

### `get_custom_checks()`

Returns only checks registered via `@gds_check`.

---

## Common Patterns

### Minimal complete model

```python
from gds import (
    typedef, state_var, entity, space, interface,
    BoundaryAction, Policy, Mechanism,
    GDSSpec, ParameterDef,
    compile_system, verify, project_canonical,
)

# 1. Define types
Pop = typedef("Population", float, constraint=lambda x: x >= 0)
Rate = typedef("Rate", float, constraint=lambda x: x >= 0)

# 2. Define entities (state space X)
population = entity(
    "Population",
    susceptible=state_var(Pop, symbol="S"),
    infected=state_var(Pop, symbol="I"),
    recovered=state_var(Pop, symbol="R"),
)

# 3. Define spaces (signal shapes)
infection_signal = space("Infection Signal", rate=Rate)

# 4. Define blocks
env = BoundaryAction(
    name="Environment",
    interface=interface(forward_out=["Contact Rate"]),
)
policy = Policy(
    name="Infection Policy",
    interface=interface(
        forward_in=["Contact Rate"],
        forward_out=["Infection Rate"],
    ),
    params_used=["beta"],
)
update = Mechanism(
    name="Update SIR",
    interface=interface(forward_in=["Infection Rate"]),
    updates=[("Population", "susceptible"), ("Population", "infected")],
)

# 5. Compose (>> auto-wires by token overlap)
composed = env >> policy >> update

# 6. Build specification
spec = GDSSpec(name="SIR Model")
spec.collect(Pop, Rate, population, infection_signal, env, policy, update)
spec.register_parameter("beta", Rate)

errors = spec.validate_spec()
assert errors == [], errors

# 7. Compile to IR
system_ir = compile_system("SIR", root=composed)

# 8. Verify structural properties
report = verify(system_ir)
print(f"Passed: {report.checks_passed}/{report.checks_total}")

# 9. Canonical projection
canonical = project_canonical(spec)
print(canonical.formula())
# h_theta : X -> X  (h = f_theta o g_theta, theta in Theta)
```

### Composition with explicit wiring

When token overlap does not hold between stages, use `StackComposition` with explicit `Wiring`:

```python
from gds import StackComposition, Wiring

tier_1_to_2 = StackComposition(
    name="Inputs >> Decisions",
    first=inputs_tier,
    second=decisions_tier,
    wiring=[
        Wiring(
            source_block="Sensor",
            source_port="Raw Reading",
            target_block="Controller",
            target_port="Measurement",
        ),
    ],
)
```

### Feedback pattern

```python
from gds import Wiring
from gds.ir.models import FlowDirection

system_with_feedback = (env >> policy >> mechanism).feedback([
    Wiring(
        source_block="Update SIR",
        source_port="State",
        target_block="Infection Policy",
        target_port="Population State",
        direction=FlowDirection.CONTRAVARIANT,
    ),
])
```

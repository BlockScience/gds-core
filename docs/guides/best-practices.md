# Best Practices: Composition Patterns & Anti-Patterns

Practical guidance for building clean, verifiable GDS specifications. Covers naming, composition patterns, type system tips, verification workflow, and common mistakes to avoid.

---

## Naming Conventions

### Port Names and Token-Based Auto-Wiring

The `>>` operator auto-wires blocks by **token overlap**. Port names are tokenized by splitting on ` + ` (space-plus-space) and `, ` (comma-space), then lowercasing each part. Plain spaces are **not** delimiters.

```python
from gds import interface

# "Heater Command" is ONE token: "heater command"
interface(forward_out=["Heater Command"])

# "Temperature + Setpoint" is TWO tokens: "temperature", "setpoint"
interface(forward_out=["Temperature + Setpoint"])

# This auto-wires to "Temperature" because they share the "temperature" token
interface(forward_in=["Temperature"])
```

!!! tip "Naming rules for auto-wiring"
    - Use **plain spaces** for multi-word names that should stay as one token: `"Heat Signal"`, `"Order Status"`
    - Use **` + `** to combine independent signals into a compound port: `"Temperature + Pressure"`
    - Use **`, `** as an alternative compound delimiter: `"Agent 1, Agent 2"`
    - Token matching is **case-insensitive**: `"Heat Signal"` matches `"heat signal"`

### Block Names

Choose block names that read well in verification reports and diagrams:

```python
# Good: descriptive, verb-noun for actions
BoundaryAction(name="Data Ingest", ...)
Policy(name="Validate Transform", ...)
Mechanism(name="Update Temperature", ...)

# Bad: generic, unclear role
AtomicBlock(name="Block1", ...)
Policy(name="Process", ...)
```

!!! note
    Block names appear in verification findings, Mermaid diagrams, and `SpecQuery` results. Clear names make debugging significantly easier.

---

## Composition Patterns

### The Three-Tier Pipeline

The canonical GDS composition follows a tiered structure that maps directly to the `h = f . g` decomposition:

```python
from gds import BoundaryAction, Mechanism, Policy, interface

# Tier 1: Exogenous inputs (boundary) and observers
ingest = BoundaryAction(
    name="Data Ingest",
    interface=interface(forward_out=["Raw Signal"]),
)

sensor = Policy(
    name="Sensor",
    interface=interface(
        forward_in=["State Reading"],
        forward_out=["Observation"],
    ),
)

# Tier 2: Decision logic (policies)
controller = Policy(
    name="Controller",
    interface=interface(
        forward_in=["Raw Signal + Observation"],
        forward_out=["Command"],
    ),
)

# Tier 3: State dynamics (mechanisms)
update = Mechanism(
    name="Update State",
    interface=interface(
        forward_in=["Command"],
        forward_out=["State Reading"],
    ),
    updates=[("Plant", "value")],
)

# Compose the tiers
input_tier = ingest | sensor           # parallel: independent inputs
forward = input_tier >> controller >> update  # sequential: data flows forward
system = forward.loop(...)             # temporal: state feeds back to observers
```

This pattern recurs across all five DSLs:

```
(exogenous inputs | observers) >> (decision logic) >> (state dynamics)
    .loop(state dynamics -> observers)
```

### When to Use Auto-Wiring vs Explicit Wiring

**Auto-wiring** (`>>`) works when output and input ports share tokens:

```python
# Auto-wires because "Heat Signal" tokens overlap
heater = BoundaryAction(
    name="Heater",
    interface=interface(forward_out=["Heat Signal"]),
)
update = Mechanism(
    name="Update Temperature",
    interface=interface(forward_in=["Heat Signal"]),
    updates=[("Room", "temperature")],
)
pipeline = heater >> update  # auto-wired via token overlap
```

**Explicit wiring** is needed when port names do not share tokens, or when you need precise control:

```python
from gds.blocks.composition import StackComposition, Wiring
from gds.ir.models import FlowDirection

# Ports don't share tokens -- explicit wiring required
tier_transition = StackComposition(
    name="Cross-Tier",
    left=policy_tier,
    right=mechanism_tier,
    wiring=[
        Wiring(
            source_block="Controller",
            source_port="Control Output",
            target_block="Plant Dynamics",
            target_port="Actuator Input",
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

!!! tip
    Start with auto-wiring and only switch to explicit wiring when the compiler raises a token overlap error. This keeps compositions readable.

### Feedback vs Temporal Loop

Two loop operators serve different purposes:

| Operator | Direction | Timing | Use Case |
|----------|-----------|--------|----------|
| `.feedback()` | CONTRAVARIANT | Within timestep | Backward utility/reward signals |
| `.loop()` | COVARIANT | Across timesteps | State fed back to observers |

```python
from gds.blocks.composition import Wiring
from gds.ir.models import FlowDirection

# Temporal loop: state at time t feeds into observer at time t+1
system_with_loop = forward_pipeline.loop(
    [
        Wiring(
            source_block="Update State",
            source_port="State Reading",
            target_block="Sensor",
            target_port="State Reading",
            direction=FlowDirection.COVARIANT,
        )
    ],
)

# Feedback loop: backward signal within a single timestep
# Used in game theory for utility/payoff channels
system_with_feedback = game_pipeline.feedback(
    [
        Wiring(
            source_block="Payoff",
            source_port="Agent Utility",
            target_block="Decision",
            target_port="Agent Utility",
            direction=FlowDirection.CONTRAVARIANT,
        )
    ],
)
```

!!! warning
    `.feedback()` is **contravariant** -- it flows backward. `.loop()` is **covariant** -- it flows forward across time. Mixing these up will cause G-003 direction consistency failures.

### Parallel Composition for Independent Subsystems

Use `|` to compose blocks that operate independently at the same tier:

```python
# Two boundary actions providing independent inputs
heater_input = BoundaryAction(
    name="Heater",
    interface=interface(forward_out=["Heat Signal"]),
)
setpoint_input = BoundaryAction(
    name="Setpoint",
    interface=interface(forward_out=["Target Temperature"]),
)

# Parallel: no validation needed, ports are independent
input_tier = heater_input | setpoint_input
```

Parallel composition does not validate any port relationships -- it simply places blocks side by side. The downstream `>>` composition handles the wiring.

---

## Anti-Patterns

### Don't Use ControlAction

`ControlAction` exists in the type system but is **unused across all five DSLs**. Every DSL maps observation and decision logic to `Policy` instead.

```python
# Bad: ControlAction is unused and will confuse readers
from gds import ControlAction
controller = ControlAction(name="Controller", ...)

# Good: Use Policy for all decision/observation logic
from gds import Policy
controller = Policy(name="Controller", ...)
```

### Don't Put State Updates in Policy

Policy blocks compute decisions. Only Mechanism blocks write state.

```python
# Bad: Policy should not claim to update state
controller = Policy(
    name="Controller",
    interface=interface(forward_in=["Signal"], forward_out=["Command"]),
    # Don't try to work around this -- Mechanism is the only writer
)

# Good: Separate decision from state mutation
controller = Policy(
    name="Controller",
    interface=interface(forward_in=["Signal"], forward_out=["Command"]),
)
update = Mechanism(
    name="Apply Command",
    interface=interface(forward_in=["Command"]),
    updates=[("Plant", "value")],  # only Mechanism has updates
)
```

### Don't Skip Verification

Even models that compile successfully benefit from verification. The checks catch subtle structural issues that compilation alone does not.

```python
from gds import compile_system, verify

system_ir = compile_system("My Model", root=pipeline)

# Always verify -- even for "simple" models
report = verify(system_ir)
for finding in report.findings:
    if not finding.passed:
        print(f"[{finding.check_id}] {finding.message}")
```

### Don't Create Circular Sequential Composition

The `>>` operator builds a DAG. Cycles in covariant flow are caught by G-006:

```python
# Bad: creates a cycle in the covariant flow graph
a >> b >> c >> a  # G-006 will flag this

# Good: use .loop() for cross-timestep feedback
forward = a >> b >> c
system = forward.loop([...])  # temporal loop, not a cycle
```

### Don't Mix Domain Concerns in a Single Block

Each block should have a single responsibility aligned with its GDS role:

```python
# Bad: one block doing both validation and state update
mega_block = AtomicBlock(
    name="Do Everything",
    interface=interface(
        forward_in=["Raw Data"],
        forward_out=["Clean Data"],
    ),
)

# Good: separate concerns by role
validate = Policy(
    name="Validate Data",
    interface=interface(forward_in=["Raw Data"], forward_out=["Clean Data"]),
)
persist = Mechanism(
    name="Persist Data",
    interface=interface(forward_in=["Clean Data"]),
    updates=[("Dataset", "count")],
)
```

---

## Type System Tips

### Token Overlap for Auto-Wiring

Understanding token splitting is essential for `>>` composition:

```python
from gds.types.tokens import tokenize

# Plain spaces are NOT delimiters
tokenize("Heater Command")      # -> {"heater command"}

# " + " splits into separate tokens
tokenize("Temperature + Setpoint")  # -> {"temperature", "setpoint"}

# ", " also splits
tokenize("Agent 1, Agent 2")    # -> {"agent 1", "agent 2"}
```

Two ports auto-wire when their token sets **overlap** (share at least one token):

```python
from gds.types.tokens import tokens_overlap

# These overlap on "temperature"
tokens_overlap("Temperature + Setpoint", "Temperature")  # True

# These do NOT overlap
tokens_overlap("Heat Signal", "Temperature Reading")  # False
```

### TypeDef Constraints Are Runtime Only

TypeDef constraints validate data values, not compilation structure. They are never called during `>>` composition or `compile_system()`:

```python
from gds import typedef

# The constraint is checked only when you call check_value()
Temperature = typedef("Temperature", float, constraint=lambda x: -273.15 <= x <= 1000)

Temperature.check_value(20.0)    # True
Temperature.check_value(-300.0)  # False -- below absolute zero

# This does NOT affect compilation or wiring
```

### Use Spaces to Define Valid Domains

Spaces define the shape of data flowing between blocks. Use them to document the semantic contract:

```python
from gds import space, typedef

Voltage = typedef("Voltage", float, units="V")
Current = typedef("Current", float, units="A")

# The space documents what flows through the wire
electrical_signal = space("ElectricalSignal", voltage=Voltage, current=Current)
```

---

## Verification Workflow

Run checks in order from fastest/cheapest to most comprehensive:

### Step 1: Domain Checks (DSL-Level)

If using a DSL, run its domain-specific checks first. These are the fastest and catch DSL-level errors in domain-native terms:

```python
from stockflow.verification.engine import verify as sf_verify

report = sf_verify(model)  # runs SF-001..SF-005
```

### Step 2: Generic Checks on SystemIR

After compilation, run the six structural topology checks:

```python
from gds import compile_system, verify

system_ir = compile_system("My Model", root=pipeline)
report = verify(system_ir)  # runs G-001..G-006
```

### Step 3: Semantic Checks on GDSSpec

For full domain property validation:

```python
from gds import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
    check_parameter_references,
    check_type_safety,
)

for check in [
    check_completeness,
    check_determinism,
    check_type_safety,
    check_parameter_references,
    check_canonical_wellformedness,
]:
    findings = check(spec)
    for f in findings:
        if not f.passed:
            print(f"[{f.check_id}] {f.message}")
```

!!! note "G-002 and BoundaryAction"
    G-002 (signature completeness) requires every block to have both inputs and outputs. BoundaryAction blocks have no inputs by design -- they are exogenous. G-002 failures on BoundaryAction blocks are **expected and not a bug**. When running `include_gds_checks=True` in DSL verification, filter G-002 findings for BoundaryAction blocks.

---

## Parameters

Parameters (Theta) are **structural metadata**. GDS never assigns values or binds parameters to concrete data. They document what is tunable:

```python
from gds import GDSSpec, Policy, interface, typedef

spec = GDSSpec(name="Thermostat")

# Declare the parameter
Setpoint = typedef("Setpoint", float, units="celsius")
spec.register_parameter("setpoint", Setpoint)

# Reference it from a block
controller = Policy(
    name="Controller",
    interface=interface(forward_in=["Temperature"], forward_out=["Command"]),
    params_used=["setpoint"],  # structural reference, not a binding
)
spec.register_block(controller)
```

Use `SpecQuery.param_to_blocks()` to trace which blocks depend on which parameters:

```python
from gds import SpecQuery

query = SpecQuery(spec)
query.param_to_blocks()
# -> {"setpoint": ["Controller"]}
```

!!! tip
    Parameters are for documenting tunable constants (learning rate, setpoint, threshold). Don't use them for runtime configuration -- GDS has no execution engine. Parameters exist so that structural queries like "which blocks are affected by this parameter?" can be answered without simulation.

---

## Summary

| Do | Don't |
|----|-------|
| Use the three-tier pattern: boundary >> policy >> mechanism | Create circular sequential compositions |
| Name ports for clear token overlap | Use generic names like "Signal" everywhere |
| Start with auto-wiring, fall back to explicit | Use explicit wiring when auto-wiring works |
| Use `.loop()` for cross-timestep state feedback | Use `.feedback()` for temporal state (it is contravariant) |
| Use Policy for all decision/observation logic | Use ControlAction (unused across all DSLs) |
| Run verification even on passing models | Skip verification -- subtle issues hide in structure |
| Separate state mutation (Mechanism) from decisions (Policy) | Put state-updating logic in Policy blocks |
| Use parameters for tunable constants | Use parameters for runtime configuration |

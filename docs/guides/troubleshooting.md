# Troubleshooting

Common errors, verification failures, and debugging strategies. Organized by where you encounter the problem: compilation, verification, or runtime.

---

## Compilation Errors

### Token Overlap Required

**Error:** Sequential composition `>>` fails because output and input ports share no tokens.

**Cause:** The `>>` operator auto-wires by token overlap. Port names are tokenized by splitting on ` + ` and `, `, then lowercasing. If no tokens overlap between the left block's `forward_out` and the right block's `forward_in`, composition fails.

```python
# This FAILS: "Temperature" and "Pressure" share no tokens
sensor = BoundaryAction(
    name="Sensor",
    interface=interface(forward_out=["Temperature"]),
)
actuator = Mechanism(
    name="Actuator",
    interface=interface(forward_in=["Pressure"]),
    updates=[("Plant", "value")],
)
pipeline = sensor >> actuator  # ERROR: no token overlap
```

**Fix options:**

1. **Rename ports** so they share at least one token:

    ```python
    sensor = BoundaryAction(
        name="Sensor",
        interface=interface(forward_out=["Pressure Reading"]),
    )
    actuator = Mechanism(
        name="Actuator",
        interface=interface(forward_in=["Pressure Reading"]),
        updates=[("Plant", "value")],
    )
    pipeline = sensor >> actuator  # OK: tokens overlap on "pressure reading"
    ```

2. **Use explicit wiring** when renaming is not appropriate:

    ```python
    from gds.blocks.composition import StackComposition, Wiring
    from gds.ir.models import FlowDirection

    pipeline = StackComposition(
        name="Sensor to Actuator",
        left=sensor,
        right=actuator,
        wiring=[
            Wiring(
                source_block="Sensor",
                source_port="Temperature",
                target_block="Actuator",
                target_port="Pressure",
                direction=FlowDirection.COVARIANT,
            ),
        ],
    )
    ```

### Port Not Found

**Error:** A wiring references a port name that does not exist on the specified block.

**Cause:** Typo in the port name, or the port was defined on a different block than expected.

**Fix:** Check the exact port names on both blocks. Port names in `Wiring` must match the strings used in `interface()`:

```python
# Check what ports a block actually has
print(sensor.interface.forward_out)  # inspect the actual port names
```

### Duplicate Block Name

**Error:** Two blocks in the same composition tree have the same name.

**Cause:** Block names must be unique within a composition. The compiler flattens the tree and uses names as identifiers.

**Fix:** Give each block a unique, descriptive name:

```python
# Bad: duplicate names
sensor_a = Policy(name="Sensor", ...)
sensor_b = Policy(name="Sensor", ...)  # name collision

# Good: unique names
sensor_a = Policy(name="Temperature Sensor", ...)
sensor_b = Policy(name="Pressure Sensor", ...)
```

---

## Generic Check Failures (G-Series)

Generic checks operate on the compiled `SystemIR` and verify structural topology.

### G-001: Domain/Codomain Matching

**What it checks:** For every covariant wiring, the wiring label must be consistent with the source block's `forward_out` or the target block's `forward_in` (token subset).

**When it fails:** A wiring label does not match either the source output ports or the target input ports.

**Fix:** Ensure the wiring label shares tokens with the connected ports. If using auto-wiring, this is handled automatically. If using explicit wiring, check that your `Wiring.label` (or the port names it derives from) match the block interfaces.

### G-002: Signature Completeness

**What it checks:** Every block must have at least one non-empty input slot and at least one non-empty output slot.

**When it fails:** A block has no inputs, no outputs, or neither.

!!! warning "BoundaryAction blocks will always fail G-002"
    BoundaryAction has no `forward_in` ports by design -- it represents exogenous input. This is **expected behavior**, not a bug. When running verification with `include_gds_checks=True` in DSL engines, filter G-002 findings for BoundaryAction blocks:

    ```python
    # Filter out expected G-002 failures on BoundaryAction blocks
    real_failures = [
        f for f in report.findings
        if not f.passed and not (
            f.check_id == "G-002"
            and any("BoundaryAction" in elem or "no inputs" in f.message
                    for elem in f.source_elements)
        )
    ]
    ```

### G-003: Direction Consistency

**What it checks:** Two validations:

- Flag consistency: COVARIANT + `is_feedback` is a contradiction (feedback implies contravariant). CONTRAVARIANT + `is_temporal` is also a contradiction (temporal implies covariant).
- Contravariant port-slot matching: for contravariant wirings, the label must match backward ports.

**When it fails:** Direction flags contradict each other, or contravariant wiring labels do not match backward ports.

**Fix:** Ensure `.feedback()` wirings use `FlowDirection.CONTRAVARIANT` and `.loop()` wirings use `FlowDirection.COVARIANT`.

### G-004: Dangling Wirings

**What it checks:** Every wiring's source and target must reference a block that exists in the system.

**When it fails:** A wiring references a block name that is not in the compiled system -- typically a typo or a block that was removed from the composition.

```python
# This will fail G-004: "Ghost" does not exist
WiringIR(source="Ghost", target="B", label="signal", ...)
# -> G-004 FAIL: source 'Ghost' unknown
```

**Fix:** Check that all block names in wirings match actual block names in the composition tree.

### G-005: Sequential Type Compatibility

**What it checks:** In stack composition (non-temporal, covariant wirings), the wiring label must be a token subset of **both** the source's `forward_out` and the target's `forward_in`.

**When it fails:** A wiring connects blocks with incompatible port types in sequential composition.

**Fix:** Rename ports so they share tokens, or use explicit wiring with correct labels.

### G-006: Covariant Acyclicity

**What it checks:** The covariant (non-temporal, non-contravariant) flow graph must be a DAG -- no cycles within a single timestep.

**When it fails:** Three or more blocks form a cycle via covariant wirings, creating an algebraic loop that cannot be resolved within one timestep.

```
A -> B -> C -> A  # cycle detected!
```

**Fix:** Break the cycle by using `.loop()` (temporal, across timesteps) for one of the edges instead of `>>` (sequential, within timestep).

---

## Semantic Check Failures (SC-Series)

Semantic checks operate on `GDSSpec` and verify domain properties.

### SC-001: Completeness (Orphan State Variables)

**What it checks:** Every entity variable is updated by at least one mechanism.

**When it fails:** An entity has a state variable but no mechanism's `updates` list references it. The variable can never change -- likely a specification error.

**Fix:** Add a Mechanism that updates the orphan variable, or remove the variable if it is not needed.

### SC-002: Determinism (Write Conflicts)

**What it checks:** Within each wiring, no two mechanisms update the same entity variable.

**When it fails:** Two mechanisms both claim to update `Counter.value` -- non-deterministic state transition.

**Fix:** Consolidate the updates into a single mechanism, or separate them into different wirings that execute at different times.

### SC-003: Reachability

**What it checks:** Can signals reach from one block to another through wiring connections?

**When it fails:** A block is isolated -- no path connects it to the rest of the system.

**Fix:** Add wiring connections or check that the block is included in the correct composition.

### SC-004: Type Safety

**What it checks:** Wire spaces match source and target block expectations. Space references on wires correspond to registered spaces.

**When it fails:** A wire references a space that is not registered, or source/target blocks are connected to incompatible spaces.

**Fix:** Register all spaces with `spec.register_space()` or `spec.collect()` before referencing them in wirings.

### SC-005: Parameter References

**What it checks:** Every `params_used` entry on blocks corresponds to a registered parameter in the spec's `parameter_schema`.

**When it fails:** A block claims to use parameter `"learning_rate"` but no such parameter is registered.

**Fix:** Register the parameter:

```python
LearningRate = typedef("LearningRate", float, constraint=lambda x: 0 < x < 1)
spec.register_parameter("learning_rate", LearningRate)
```

### SC-006: Canonical f (No Mechanisms)

**What it checks:** At least one mechanism exists in the spec, so the state transition function f is non-empty.

**When it fails:** The spec has no Mechanism blocks. The canonical `h = f . g` degenerates to `h = g`.

!!! note
    This is a **warning**, not necessarily an error. Game-theoretic models (OGS) are intentionally stateless -- `h = g` is their correct canonical form. If you expect state dynamics, add Mechanism blocks.

### SC-007: Canonical X (No State Space)

**What it checks:** The state space X is non-empty -- at least one entity with variables exists.

**When it fails:** No entities are registered, so there is no state to transition.

**Fix:** Register entities with state variables if your model has state. If the model is intentionally stateless, this warning can be ignored.

---

## Common Gotchas

### Token Matching Rules

Token splitting only happens on ` + ` (space-plus-space) and `, ` (comma-space). Plain spaces within a name are **not** delimiters:

```python
from gds.types.tokens import tokenize

tokenize("Heater Command")           # {"heater command"} -- ONE token
tokenize("Heater + Command")         # {"heater", "command"} -- TWO tokens
tokenize("Temperature + Setpoint")   # {"temperature", "setpoint"}
tokenize("Agent 1, Agent 2")         # {"agent 1", "agent 2"}
```

### Feedback is Contravariant, Loop is Covariant

These are not interchangeable:

| Operator | Direction | Timing | Purpose |
|----------|-----------|--------|---------|
| `.feedback()` | CONTRAVARIANT | Within timestep | Backward utility/reward signals |
| `.loop()` | COVARIANT | Across timesteps | State feedback to observers |

Using `.feedback()` for temporal state feedback will cause G-003 failures.

### Frozen Pydantic Models

DSL elements (Stock, Flow, Sensor, etc.) and GDS value objects (TypeDef, Space, Entity, StateVariable) are **frozen** Pydantic models. You cannot mutate them after creation:

```python
from gds import typedef

t = typedef("Temperature", float)
t.name = "Pressure"  # ERROR: frozen model, cannot assign

# Instead, create a new instance
p = typedef("Pressure", float)
```

### collect() vs register_wiring()

`GDSSpec.collect()` type-dispatches objects by their Python type: TypeDef, Space, Entity, Block, ParameterDef. It does **not** handle SpecWiring:

```python
spec = GDSSpec(name="My Spec")

# These go through collect()
spec.collect(Temperature, HeaterCommand, room, sensor, controller)

# SpecWiring must use register_wiring() explicitly
spec.register_wiring(SpecWiring(
    name="Main Pipeline",
    block_names=["Sensor", "Controller"],
    wires=[Wire(source="Sensor", target="Controller", space="SignalSpace")],
))
```

### Spec Validation vs System Verification

These are different operations on different objects:

```python
# Spec validation: checks registration consistency (missing types, blocks, etc.)
errors = spec.validate_spec()  # returns list[str]

# System verification: runs G-001..G-006 on compiled IR
report = verify(system_ir)  # returns VerificationReport

# Semantic checks: runs SC-001..SC-007 on the spec
findings = check_completeness(spec)  # returns list[Finding]
```

---

## Debug Workflow

### Step 1: Inspect the Compiled IR

After compilation, print the blocks and wirings to see what the compiler produced:

```python
from gds import compile_system

system_ir = compile_system("Debug Model", root=pipeline)

print("=== Blocks ===")
for block in system_ir.blocks:
    print(f"  {block.name}: {block.signature}")

print("\n=== Wirings ===")
for wiring in system_ir.wirings:
    print(f"  {wiring.source} --{wiring.label}--> {wiring.target} ({wiring.direction})")
```

### Step 2: Visualize with gds-viz

Generate Mermaid diagrams for visual inspection:

```python
from gds_viz.mermaid import system_to_mermaid

mermaid_str = system_to_mermaid(system_ir)
print(mermaid_str)
# Paste into any Mermaid renderer (mkdocs, GitHub, mermaid.live)
```

### Step 3: Run Verification with Individual Checks

Run checks one at a time to isolate the issue:

```python
from gds.verification.engine import verify
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g004_dangling_wirings,
    check_g006_covariant_acyclicity,
)

# Run one check at a time
for check in [
    check_g001_domain_codomain_matching,
    check_g004_dangling_wirings,
    check_g006_covariant_acyclicity,
]:
    report = verify(system_ir, checks=[check])
    failures = [f for f in report.findings if not f.passed]
    if failures:
        print(f"\n{check.__name__}:")
        for f in failures:
            print(f"  [{f.check_id}] {f.message}")
```

### Step 4: Use SpecQuery for Structural Analysis

`SpecQuery` answers questions about information flow without running the model:

```python
from gds import SpecQuery

query = SpecQuery(spec)

# What blocks affect a specific entity variable?
query.blocks_affecting("Room", "temperature")
# -> ['Update Temperature', 'Controller', 'Sensor']

# What parameters influence which blocks?
query.param_to_blocks()
# -> {'setpoint': ['Controller']}

# Full block dependency graph
query.dependency_graph()
```

---

## Quick Reference: Error to Fix

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| Token overlap required | `>>` ports share no tokens | Rename ports or use explicit wiring |
| Port not found | Typo in wiring port name | Check `block.interface` for exact names |
| Duplicate block name | Two blocks with same name | Use unique descriptive names |
| G-001 FAIL | Wiring label mismatches ports | Align wiring labels with port tokens |
| G-002 FAIL on BoundaryAction | Expected -- no inputs by design | Filter or ignore for boundary blocks |
| G-003 FAIL | Direction flag contradiction | Match `.feedback()` with CONTRAVARIANT, `.loop()` with COVARIANT |
| G-004 FAIL | Wiring references missing block | Fix block name typo |
| G-005 FAIL | Sequential port type mismatch | Ensure `>>` ports share tokens on both sides |
| G-006 FAIL | Cycle in covariant flow | Break cycle with `.loop()` for temporal edge |
| SC-001 WARNING | Orphan state variable | Add a Mechanism that updates it |
| SC-002 ERROR | Two mechanisms update same variable | Consolidate into one Mechanism |
| SC-005 FAIL | Unregistered parameter | Call `spec.register_parameter()` |
| SC-006/007 WARNING | No mechanisms or entities | Add state if expected, or ignore for stateless models |
| Cannot mutate frozen model | Pydantic frozen=True | Create a new instance instead |

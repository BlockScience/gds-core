# Composition

The composition algebra is the core of Layer 0. Four operators build complex systems from simple blocks.

## Operators

### Sequential Composition (`>>`)

Chains blocks so the output of one feeds the input of the next. Auto-wiring matches ports by token overlap.

```python
from gds import BoundaryAction, Policy, Mechanism, interface

sensor = BoundaryAction(
    name="Sensor",
    interface=interface(forward_out=["Temperature"]),
)
controller = Policy(
    name="Controller",
    interface=interface(
        forward_in=["Temperature"],
        forward_out=["Heater Command"],
    ),
)
actuator = Mechanism(
    name="Actuator",
    interface=interface(forward_in=["Command"]),
)

pipeline = sensor >> controller >> actuator
```

Token overlap: `"Heater Command"` auto-wires to `"Command"` because they share the token `"command"`.

### Parallel Composition (`|`)

Runs blocks side-by-side with no interaction. No type validation between them.

```python
from gds import BoundaryAction, interface

temp_sensor = BoundaryAction(
    name="Temperature Sensor",
    interface=interface(forward_out=["Temperature"]),
)
pressure_sensor = BoundaryAction(
    name="Pressure Sensor",
    interface=interface(forward_out=["Pressure"]),
)

sensors = temp_sensor | pressure_sensor
```

### Feedback Loop (`.feedback()`)

Creates a backward signal path within a single timestep. The backward channel is **contravariant** — it flows in the opposite direction to the forward path.

```python
plant = sensor >> controller >> actuator
system = plant.feedback(
    backward_from=actuator,
    backward_to=sensor,
)
```

### Temporal Loop (`.loop()`)

Feeds state from the current timestep to the next. **Covariant only** — the loop signal flows forward in time.

```python
system_with_memory = system.loop(
    loop_from=actuator,
    loop_to=sensor,
)
```

## Composition Tree

Domain DSLs build systems using a convergent tiered pattern:

```
(exogenous inputs | observers) >> (decision logic) >> (state dynamics)
    .loop(state dynamics -> observers)
```

## Explicit Wiring

When token overlap doesn't hold, use `StackComposition` with explicit wiring:

```python
from gds import StackComposition, Wiring

pipeline = StackComposition(
    children=[block_a, block_b],
    wiring=[
        Wiring(source="block_a.output_x", target="block_b.input_y"),
    ],
)
```

## Compilation

The compiler flattens the composition tree into a flat IR:

```
Block tree -> flatten() -> list[AtomicBlock]
           -> block_compiler() -> list[BlockIR]
           -> _walk_wirings() -> list[WiringIR]
           -> _extract_hierarchy() -> HierarchyNodeIR
           = SystemIR(blocks, wirings, hierarchy)
```

See [Verification](verification.md) for the structural checks (G-001..G-006) that validate the compiled result.

## See Also

- [Blocks & Roles](blocks.md) — the leaf nodes that get composed
- [Type System](types.md) — token-based matching used by auto-wiring
- [Architecture](architecture.md) — Layer 0 design overview
- [API Reference](../api/compiler.md) — `gds.compiler` module

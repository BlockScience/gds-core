# Execution Semantics

## The Three-Layer Temporal Stack

GDS separates temporal concerns into three layers:

| Layer | Responsibility | Where |
|-------|---------------|-------|
| **Core algebra** | Temporally agnostic composition operators | `gds-framework` blocks, compiler, IR |
| **DSL declaration** | Declares what "time" means for the domain | `ExecutionContract` on `GDSSpec` |
| **Simulation runtime** | Advances state through time | `gds-sim`, `gds-continuous` |

The core algebra (Layer 0) carries no intrinsic notion of time. `TemporalLoop`
names a structural boundary between evaluation steps, but the algebra does not
define what "step" means -- that is the DSL's job.

## ExecutionContract

`ExecutionContract` is a frozen dataclass attached to `GDSSpec` as an optional
field. It declares the time model that the DSL commits to:

```python
from gds.execution import ExecutionContract

contract = ExecutionContract(
    time_domain="discrete",        # discrete | continuous | event | atemporal
    synchrony="synchronous",       # synchronous | asynchronous (discrete only)
    observation_delay=0,           # 0 = Moore, 1 = one-step delay (discrete only)
    update_ordering="Moore",       # Moore | Mealy (discrete only)
)
```

### Fields

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `time_domain` | Literal | *required* | What kind of temporal boundary the DSL declares |
| `synchrony` | Literal | `"synchronous"` | For discrete only: sync or async state updates |
| `observation_delay` | int | `0` | For discrete only: observation delay in steps |
| `update_ordering` | Literal | `"Moore"` | For discrete only: Moore or Mealy semantics |

**Validation:** Fields `synchrony`, `observation_delay`, and `update_ordering`
are only meaningful for `time_domain="discrete"`. Setting non-default values
with any other time domain raises `ValueError`.

### Compatibility

Two contracts are compatible (can be composed) when:

- They share the same `time_domain`, **or**
- At least one is `atemporal` (universal donor -- composes with anything)

```python
discrete = ExecutionContract(time_domain="discrete")
atemporal = ExecutionContract(time_domain="atemporal")

assert discrete.is_compatible_with(atemporal)  # True
assert atemporal.is_compatible_with(discrete)  # True
```

### Optional Attachment

A `GDSSpec` without an `ExecutionContract` is valid for all structural and
semantic verification. The contract is required only when connecting a spec
to a simulation engine.

```python
spec = GDSSpec(name="my-system")
# ... register types, blocks, wirings ...
spec.execution_contract = ExecutionContract(time_domain="discrete")
```

## Moore Discrete-Time Semantics

The default discrete contract (`synchronous / 0 / Moore`) corresponds to the
classical Moore machine:

- **Synchronous:** All state variables update simultaneously at each step
- **Observation delay = 0:** Output depends on current state only (not inputs)
- **Moore ordering:** Observation happens before decision within each step

This is the natural semantics for stock-flow models, control systems, and
state machines -- all DSLs that use `.loop()` for temporal recurrence.

## DSL Contract Mapping

| DSL | time_domain | synchrony | update_ordering | Notes |
|-----|------------|-----------|----------------|-------|
| gds-stockflow | discrete | synchronous | Moore | Accumulation semantics |
| gds-control | discrete | synchronous | Moore | Sensor-controller-plant |
| gds-games | atemporal | -- | -- | Round iteration, no time model |
| gds-software (state machine) | discrete | synchronous | Moore | State transitions |
| gds-software (DFD, C4, component, ERD, dependency) | atemporal | -- | -- | Structural diagrams |
| gds-business (CLD) | discrete | synchronous | Moore | Causal feedback |
| gds-business (SCN) | discrete | synchronous | Moore | Supply chain flows |
| gds-business (VSM) | atemporal | -- | -- | Value stream mapping |

## Verification

`SC-011` (`check_execution_contract_compatibility`) validates the contract:

- **No contract:** INFO -- spec is valid for structural verification only
- **Valid contract:** INFO -- reports the declared time model
- **Invalid contract:** ERROR -- inconsistent field values (defensive, normally
  caught by `__post_init__`)

## What Is Not Covered

- **Continuous-time (ODE):** `time_domain="continuous"` is defined but no DSL
  emits it yet. This will connect to `gds-continuous` when the spec-to-sim
  bridge is extended (T2-4).
- **Event-driven:** `time_domain="event"` is reserved for future event-based
  DSLs.
- **Asynchronous updates:** `synchrony="asynchronous"` is defined but no DSL
  emits it yet. This enables agent-based models where entities update at
  different rates.
- **Mealy semantics:** `update_ordering="Mealy"` is defined for systems where
  output depends on both state and current input.

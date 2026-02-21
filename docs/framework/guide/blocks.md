# Blocks & Roles

## Block Hierarchy

The composition algebra is **sealed** — only 5 concrete Block types exist:

- `AtomicBlock` — leaf node (domain packages subclass this)
- `StackComposition` (`>>`) — sequential, validates token overlap
- `ParallelComposition` (`|`) — independent, no type validation
- `FeedbackLoop` (`.feedback()`) — backward within timestep
- `TemporalLoop` (`.loop()`) — forward across timesteps, enforces COVARIANT only

## GDS Roles

Block roles subclass `AtomicBlock` and add interface constraints:

| Role | `forward_in` | `forward_out` | `backward_in` | `backward_out` | Purpose |
|---|:---:|:---:|:---:|:---:|---|
| **BoundaryAction** | MUST be `()` | any | any | any | Exogenous observation |
| **Policy** | any | any | any | any | Decision logic |
| **ControlAction** | any | any | any | any | Admissibility constraint |
| **Mechanism** | any | any | MUST be `()` | MUST be `()` | State update |

Violating the MUST constraints raises `GDSCompositionError` immediately at construction time.

### BoundaryAction

Models exogenous observations — the system boundary. Has no forward inputs.

```python
from gds import BoundaryAction, interface

sensor = BoundaryAction(
    name="Temperature Sensor",
    interface=interface(forward_out=["Temperature"]),
)
```

### Policy

Core decision logic — maps observations to actions. No port restrictions.

```python
from gds import Policy, interface

controller = Policy(
    name="PID Controller",
    interface=interface(
        forward_in=["Temperature", "Setpoint"],
        forward_out=["Heater Command"],
        backward_in=["Energy Cost"],
    ),
    params_used=["Kp", "Ki", "Kd", "setpoint"],
)
```

### ControlAction

Admissibility constraints — limits what actions are allowed.

```python
from gds import ControlAction, interface

plant = ControlAction(
    name="Room Plant",
    interface=interface(
        forward_in=["Heater Command"],
        forward_out=["Room State"],
        backward_out=["Energy Cost"],
    ),
)
```

### Mechanism

State update — the only blocks that write to state. Cannot have backward ports.

```python
from gds import Mechanism, interface

update = Mechanism(
    name="Update Room",
    interface=interface(forward_in=["Room State"]),
    updates=[("Room", "temperature"), ("Room", "energy_consumed")],
)
```

## Composition Operators

### Sequential (`>>`)

```python
pipeline = sensor >> controller >> plant
```

Auto-wires by token overlap between `forward_out` and `forward_in` ports. Raises `GDSTypeError` if no overlap.

### Parallel (`|`)

```python
updates = update_s | update_i | update_r
```

Independent blocks — no type validation.

### Feedback (`.feedback()`)

```python
from gds import Wiring
from gds.ir.models import FlowDirection

system = pipeline.feedback([
    Wiring(
        source_block="Room Plant", source_port="Energy Cost",
        target_block="PID Controller", target_port="Energy Cost",
        direction=FlowDirection.CONTRAVARIANT,
    )
])
```

Within-timestep backward flow. Requires CONTRAVARIANT direction.

### Temporal Loop (`.loop()`)

```python
system = pipeline.loop([
    Wiring(
        source_block="Update Prey", source_port="Population",
        target_block="Observe", target_port="Population",
        direction=FlowDirection.COVARIANT,
    )
])
```

Cross-timestep forward flow. COVARIANT is mandatory — CONTRAVARIANT raises `GDSTypeError`.

## Tagged Mixin

All blocks inherit from `Tagged`, providing semantic annotations:

```python
sensor = BoundaryAction(
    name="Sensor",
    interface=interface(forward_out=["Temperature"]),
    tags={"domain": "Observation"},
)

sensor.has_tag("domain")       # True
sensor.get_tag("domain")       # "Observation"
```

Tags are inert — stripped at compile time, never affect verification or composition.

# Controller-Plant Duality and Perspective Inversion

> Design note documenting the formal duality between the controller and plant perspectives at every `>>` composition boundary, and the role of `ControlAction` as the output map `y = C(x, d)`.

---

## The Duality Statement

At every `>>` (sequential composition) boundary, one system's **ControlAction output** is isomorphic to the next system's **BoundaryAction input**:

```
System A                          System B
┌─────────────────────┐           ┌─────────────────────┐
│  BoundaryAction (z) │           │  BoundaryAction (z) │
│  Policy d = g(x,z)  │           │  Policy d = g(x,z)  │
│  Mechanism x'=f(x,d)│           │  Mechanism x'=f(x,d)│
│  ControlAction y=C  │ ──(y)──> │                      │
└─────────────────────┘           └─────────────────────┘
        output y                     receives y as z
```

What System A calls its **output** (`ControlAction.forward_out`), System B receives as its **exogenous input** (`BoundaryAction.forward_out` into the system). The signal is the same; only the perspective changes.

This duality is fundamental to compositional modeling: every system boundary is simultaneously an output boundary (from inside) and an input boundary (from outside).

---

## Role Naming: Two Perspectives

| Role | Inside (plant) perspective | Outside (controller) perspective |
|------|---------------------------|----------------------------------|
| **BoundaryAction** | Exogenous input z the system conditions on | Output from a previous system acting on this one |
| **Policy** | Decision d = g(x, z) | Internal -- opaque to outside |
| **Mechanism** | State update x' = f(x, d) | Internal dynamics -- opaque to outside |
| **ControlAction** | Output map y = C(x, d) | Action this system exerts on the next system |

The inside perspective sees `BoundaryAction` as "things that happen to me" and `ControlAction` as "what I emit." The outside perspective sees the same pair as "what I do to the next system" and "what the previous system did to me."

---

## Port Direction: Two Perspectives

| Port direction | Inside perspective | Outside perspective |
|---------------|-------------------|---------------------|
| `forward_out` | What this system emits (y) | Control action on the next block |
| `forward_in` | What this system receives (z) | Output from the previous block |
| `backward_out` | Cost/utility this system produces | Constraint signal to previous block |
| `backward_in` | Cost/utility this system receives | Constraint signal from next block |

The forward channel carries state-dependent signals. The backward channel carries evaluative or constraint signals (costs, utilities, feasibility). Both channels exhibit the same duality at `>>` boundaries.

---

## Canonical Form with Output Map

The full canonical form with the output map is:

```
d = g(x, z)           -- input map (Policy)
x' = f(x, d)          -- state transition (Mechanism)
y = C(x, d)           -- output map (ControlAction)
```

Where:

- **X** = state space (Entity variables)
- **Z** = exogenous signal space (BoundaryAction outputs)
- **D** = decision space (Policy outputs)
- **Y** = output space (ControlAction outputs)
- **h = f . g** produces the state transition `x' = f(x, g(x, z))`
- **C** produces the observable output `y` that crosses the system boundary

The state transition `h` and the output map `C` are independent: `h` determines what the system *becomes*, while `C` determines what the system *emits*. Both depend on the current state and decision, but they produce different things (next state vs. output signal).

---

## Example: Thermostat from Both Perspectives

### Inside (plant) perspective -- "I am the room"

```python
# What happens TO the room
sensor = BoundaryAction("Sensor", forward_out=["Temperature"])       # z: sensed temperature
setpoint = BoundaryAction("Setpoint", forward_out=["Target Temp"])   # z: desired temperature

# Room's internal logic
controller = Policy("PID Controller",
    forward_in=["Temperature", "Target Temp"],
    forward_out=["Heater Command"])                                  # d = g(x, z)

heater = Mechanism("Heater Dynamics",
    forward_in=["Heater Command"],
    updates=[("Room", "temperature")])                               # x' = f(x, d)

# What the room EMITS to the next system
output = ControlAction("Temperature Output",
    forward_in=["Temperature"],
    forward_out=["Room Temperature"])                                # y = C(x, d)
```

### Outside (controller) perspective -- "I am the building manager"

From outside, the room is a single compositional unit:
- It receives `Sensor` and `Setpoint` signals (I provide these)
- It emits `Room Temperature` (I observe this)
- Its internal PID controller and heater dynamics are opaque to me

When I compose the room with an HVAC optimizer via `>>`, the room's `ControlAction` output (`Room Temperature`) becomes the optimizer's `BoundaryAction` input.

---

## Connection to SC-010: Why C Must Not Feed g

SC-010 enforces that ControlAction outputs do not route back to Policy or BoundaryAction blocks within the same system. The formal reason:

1. **g** (the input map) transforms `(x, z)` into decisions `d`
2. **C** (the output map) transforms `(x, d)` into observable output `y`
3. If `y` feeds back into `g`, then `g` depends on `C` which depends on `g` -- creating an algebraic loop within a single timestep

This conflates the output map with the input map, breaking the canonical separation `h = f . g`. The output map C is meant to produce signals that cross the system boundary at `>>` composition points, not signals that circulate internally.

ControlAction outputs **may** feed Mechanism blocks (the state dynamics `f` can legitimately depend on output observations). They **must not** feed Policy or BoundaryAction blocks (the input map `g`).

If internal feedback is needed, use Policy-to-Policy wiring within the `g` pathway, or use `.loop()` / `.feedback()` for temporal/backward recurrence.

---

## Connection to Future Work

- **T0-4 (Temporal agnosticism)**: The duality holds regardless of whether composition is discrete-time, continuous-time, or event-driven. The `>>` boundary is a structural fact, not a temporal one.
- **T1-3 (Disturbance inputs)**: A future extension may distinguish between controllable exogenous inputs (reference signals) and uncontrollable exogenous inputs (disturbances). Both enter through BoundaryAction, but their controllability status differs. This refinement would add metadata to BoundaryAction without changing the duality structure.

---

## Summary

The controller-plant duality is not a design choice -- it is an emergent property of compositional systems. Any system that can be composed with `>>` necessarily has an inside (what it does to itself) and an outside (what it does to its neighbors). The four GDS roles map cleanly to both perspectives, and the `ControlAction` role is the formal carrier of the output map that bridges them.

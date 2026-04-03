# Disturbance Formalization: The U_c / W Partition

## Motivation

The standard GDS canonical form treats all BoundaryAction outputs as a
single exogenous signal space Z:

```
g : X x Z -> D       (policy / input map)
f : X x D -> X       (state transition)
h = f . g            (composition)
```

In practice, not all exogenous inputs pass through the decision layer g.
Some inputs -- wind gusts, sensor noise, market shocks -- enter the state
dynamics f directly, bypassing any policy or control logic. These are
**disturbances**.

## The Partition

We split Z into two disjoint subspaces:

| Space | Name | Description |
|-------|------|-------------|
| **U_c** | Controlled inputs | Exogenous signals that feed the policy map g |
| **W** | Disturbances | Exogenous signals that bypass g and enter f directly |

The extended canonical form becomes:

```
g : X x U_c -> D          (policy / input map)
f : X x D x W -> X        (state transition with disturbances)
h = f(-, g(-, -), -)       (composition)
```

When W is empty, this reduces to the standard form.

## Tagging Convention

Disturbance inputs are declared by tagging a `BoundaryAction` block with
`role="disturbance"`:

```python
import gds

wind = gds.BoundaryAction(
    name="Wind Gust",
    interface=gds.interface(forward_out=["Force"]),
    tags={"role": "disturbance"},
)
```

The tag is semantic metadata -- it does not change block construction,
composition, or compilation. It only affects:

1. **Canonical projection**: `project_canonical()` partitions BoundaryAction
   ports into `input_ports` (U_c) and `disturbance_ports` (W).
2. **DST-001 verification**: checks that disturbance-tagged blocks are not
   wired to Policy blocks.

## DST-001: Disturbance Routing Check

**Invariant**: No component of W appears in the domain of g.

A disturbance-tagged BoundaryAction must route to Mechanism blocks (the f
pathway), never to Policy blocks (the g pathway). Routing a disturbance
through Policy would mean the controller can observe and act on it, which
contradicts its classification as a disturbance.

| Wiring target | Allowed? | Rationale |
|---------------|----------|-----------|
| Mechanism | Yes | Disturbance enters f directly |
| Policy | No (DST-001 ERROR) | Would place W in domain of g |
| ControlAction | Yes | Output map C may depend on disturbances |
| BoundaryAction | N/A | BoundaryActions have no forward_in |

## Modeling Guidelines

### When to tag as disturbance

Tag a BoundaryAction as a disturbance when:

- The input represents noise, perturbation, or environmental forcing
- No controller in the system observes or reacts to this specific input
- The input affects state dynamics directly (e.g., wind on a drone, noise
  on a sensor reading, demand shock on inventory)

### When NOT to tag as disturbance

Do not tag as disturbance when:

- The input is observed by a sensor and fed to a controller
- The input represents a setpoint, reference signal, or user command
- A policy block explicitly takes this input as part of its decision

### Example: Thermostat with Wind Disturbance

```python
import gds

# Controlled input -- feeds the policy
setpoint = gds.BoundaryAction(
    name="Setpoint",
    interface=gds.interface(forward_out=["Target Temperature"]),
)

# Disturbance -- bypasses policy, enters mechanism directly
wind = gds.BoundaryAction(
    name="Wind",
    interface=gds.interface(forward_out=["Heat Loss"]),
    tags={"role": "disturbance"},
)

controller = gds.Policy(
    name="PID Controller",
    interface=gds.interface(
        forward_in=["Target Temperature"],
        forward_out=["Heater Command"],
    ),
)

heater = gds.Mechanism(
    name="Room Dynamics",
    interface=gds.interface(forward_in=["Heater Command + Heat Loss"]),
    updates=[("Room", "temperature")],
)
```

The canonical projection will show:

- `input_ports`: `[("Setpoint", "Target Temperature")]` (U_c)
- `disturbance_ports`: `[("Wind", "Heat Loss")]` (W)
- `formula()`: `h : X -> X  (h = f . g); f : X x D x W -> X`

## Relationship to Existing Theory

The U_c / W partition is a **semantic layer extension** -- it does not change
the underlying composition algebra or compilation pipeline. The partition is
derived purely from tags at canonical projection time.

This aligns with control theory's standard plant model:

```
x_{t+1} = f(x_t, u_t, w_t)
```

where u_t is the control input and w_t is the disturbance. The GDS
framework makes this distinction explicit and verifiable through DST-001.

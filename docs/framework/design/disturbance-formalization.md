# Disturbance Input Formalization

## Motivation

Exogenous inputs to a GDS system are not homogeneous.  Some inputs are
*observed* by the decision layer (Policy blocks) and condition its output;
others *bypass* the decision layer entirely and act directly on the state
dynamics (Mechanism blocks).  Prior to this formalization, both kinds were
represented uniformly as `BoundaryAction` blocks, conflating controlled
inputs with disturbances.

This document formalizes the **U_c / W partition** of the BoundaryAction
input space, using the existing `Tagged` mixin to annotate disturbance
inputs and a new `DST-001` check to enforce routing topology.

No change to the canonical algebra is required -- the partition lives in
the semantic layer only.

## The Input Partition

Let Z denote the full set of BoundaryAction forward-out ports.  We
partition Z into:

| Symbol | Name | Description |
|--------|------|-------------|
| **U_c** | Controlled inputs | Observable by Policy; condition the decision mapping g |
| **W** | Disturbances | Bypass Policy; act directly on state dynamics f |

The invariant:

> No component of **W** appears in the domain of **g**.
> No component of **U_c** appears in **f** except through **d** (the decision vector).

## Extended Canonical Form

With the partition, the canonical GDS decomposition becomes:

```
d  = g(x, u_c)          -- decision mapping (Policy)
x' = f(x, d, w)         -- state transition (Mechanism)
y  = C(x, d)            -- observation / output
```

Where:

- **x** is the state vector (Entity variables)
- **u_c** is the controlled input vector (non-disturbance BoundaryAction outputs)
- **w** is the disturbance vector (disturbance-tagged BoundaryAction outputs)
- **d** is the decision vector (Policy outputs)
- **Theta** (parameters) are elided for clarity but remain available throughout

## Tagging Convention

Disturbance inputs are annotated using the existing `Tagged` mixin on
`BoundaryAction`:

```python
wind = BoundaryAction(
    name="Wind",
    interface=Interface(forward_out=(port("Force"),)),
    tags={"role": "disturbance"},
)
```

Any `BoundaryAction` whose `tags` dict contains `{"role": "disturbance"}`
is classified as a disturbance input.  All other BoundaryActions remain
controlled inputs.

This design reuses the existing tagging infrastructure without adding new
block types or constructor parameters.

## DST-001 Check Semantics

**DST-001** is a semantic verification check that enforces the disturbance
routing invariant at the wiring topology level.

**What it enforces:**

- No `SpecWiring.Wire` may connect a disturbance-tagged `BoundaryAction`
  (source) to a `Policy` block (target).
- Disturbance inputs must route to `Mechanism` blocks or other non-Policy
  blocks.

**What it does NOT enforce:**

- It does not verify that the disturbance designation is *physically correct*.
  Whether "wind" is truly a disturbance or an observable signal is a
  **modeling judgment** -- DST-001 only enforces that the declared topology
  is consistent with the declared tags.
- It does not enforce that controlled inputs wire *only* to Policy.  A
  controlled input may wire to both Policy and Mechanism if the modeler
  intends direct feedthrough.

## Canonical Projection

`project_canonical()` now partitions BoundaryAction ports into two fields
on `CanonicalGDS`:

- `input_ports` -- controlled inputs (U_c)
- `disturbance_ports` -- disturbance inputs (W)

The `formula()` method renders the extended form when disturbance ports
are present:

```
h : X -> X  (h = f . g); f : X x D x W -> X
```

## When to Use Disturbance vs Controlled Input

The distinction is a modeling judgment.  Guidelines:

| Scenario | Classification | Rationale |
|----------|---------------|-----------|
| Wind force on a building | **Disturbance** | Cannot control, cannot observe before it acts on structure |
| Market price signal | **Controlled input** | Observable, Policy can condition on it |
| Sensor noise | **Disturbance** | Bypasses decision layer, directly corrupts state measurement |
| User button press | **Controlled input** | Observable event that triggers policy logic |
| Background radiation | **Disturbance** | Uncontrollable environmental factor |
| Thermostat setpoint | **Controlled input** | Deliberate reference signal for the controller |

The key question: **Can the decision layer observe this input and condition
its output on it?**  If yes, it is a controlled input.  If no, it is a
disturbance.

## Cross-References

- [Controller-Plant Duality](proposals/entity-redesign.md) (T0-3) --
  ControlAction resolution and the observer/actuator pattern
- GDS theory: Zargham & Shorish (2022), Section 3 -- admissible input
  decomposition

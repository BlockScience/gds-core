# Controller-Plant Duality and Perspective Inversion

> Mathematical proposition and design reference for the ControlAction role
> in the GDS canonical form. Implements T0-3 of the
> [Improvement Roadmap](improvement-roadmap.md).

---

## The Duality Proposition

**At every `>>` composition boundary, one system's ControlAction output is
isomorphic to the next system's BoundaryAction input.**

The same signal `y` is simultaneously:
- The **plant's output** (inside perspective) — what this system emits
- A **control action** (outside perspective) — what this system exerts on the next

This perspective inversion is not a convention; it is a structural property of
the `>>` operator. The composition algebra enforces it: the `forward_out` ports
of the left block become the `forward_in` ports of the right block via token
overlap matching.

---

## Role Naming from Both Perspectives

| Role | Inside (plant) perspective | Outside (controller) perspective |
|------|---------------------------|----------------------------------|
| **BoundaryAction** | Exogenous input `u` the system conditions on | Output from a previous system acting on this one |
| **Policy** | Decision `d = g(x, u)` | Internal policy — opaque to outside |
| **Mechanism** | State update `x' = f(x, d)` | Internal dynamics — opaque to outside |
| **ControlAction** | Output map `y = C(x, d)` | Action this system exerts on the next system |

## Port Directions and the Duality

| Port direction | Inside perspective | Outside perspective |
|----------------|--------------------|--------------------|
| `forward_out` | What this system emits (y) | Control action on the next block |
| `forward_in` | What this system receives (u) | Output from the previous block |
| `backward_out` | Cost/utility this system produces | Constraint signal to the previous block |
| `backward_in` | Cost/utility this system receives | Constraint signal from the next block |

---

## Extended Canonical Form

With the output map, the full canonical decomposition is:

```
Given: (X, U, D, Y, Θ, g, f, C)

d    = g(x, u)          g: X × U → D     policy map
x'   = f(x, d)          f: X × D → X     state update
y    = C(x, d)          C: X × D → Y     output map
```

`CanonicalGDS` captures this as:
- `input_ports` — (block, port) from BoundaryAction `forward_out` → U
- `decision_ports` — (block, port) from Policy `forward_out` → D
- `output_ports` — (block, port) from ControlAction `forward_out` → Y
- `output_map` — (block, ((entity, var), ...)) from ControlAction `.observes` → C's read dependencies

The `formula()` method renders: `h = f ∘ g,  y = C(x, d)` (or `C_θ(x, d)` when parameterized).

---

## Observability Connection

The output map `C` is what makes observability questions answerable:

- **Structural distinguishability** (T2-1): Is there a wiring path from a state
  variable to a ControlAction output port? If not, that state is structurally
  unobservable — no output map reads it.
- **Observability analysis** (DSL-level): For linear systems in `gds-control`,
  the rank condition on the observability Gramian becomes computable once `C` is
  extracted.

Without ControlAction, the canonical form has no output equation, and these
questions are unanswerable.

---

## SC-010: Forward-Path Routing Check

**Property:** In the forward wiring topology (SpecWiring), ControlAction outputs
must not wire to Policy or BoundaryAction blocks.

**Rationale:** The output map produces the system's observable signal `y`. In the
forward path, `y` should feed downstream state updates (Mechanisms) or exit the
system boundary. If `y` feeds back into the decision layer, it creates a
within-timestep algebraic dependency that blurs the `h = f ∘ g` decomposition.

**Feedback is allowed:** The `.feedback()` composition operator correctly routes
observations back to policies across the backward channel (contravariant). This
is the standard observer pattern. SC-010 only checks SpecWiring (forward-path
wires), so feedback routing is not flagged.

**Severity:** WARNING — a structural smell, not a hard error.

---

## Worked Example: Fishery Regulator

The Gordon-Schaefer fishery (V2 regulated) demonstrates the duality:

```python
# Output map: regulator observes total catch
catch_observation = ControlAction(
    name="Catch Observation",
    interface=Interface(
        forward_in=(port("Total Harvest"), port("Population Level")),
        forward_out=(port("Observed Total Catch"),),
    ),
    observes=[("Fish Population", "level")],
)
```

**Inside perspective (fishery system):**
- `Catch Observation` is the output map `y = C(N, H)` — it produces the
  observable signal "Observed Total Catch" from the fish stock level and
  harvest rate.

**Outside perspective (regulator):**
- `Observed Total Catch` is the input signal the regulator acts on.
  The regulator cannot observe individual fisher profits (no wiring path
  from profit entities to `Catch Observation`) — this is a structural
  limitation discoverable via distinguishability analysis.

**Canonical result:**
```
h = f ∘ g,  y = C(x, d)

control_blocks = ("Catch Observation",)
output_ports = (("Catch Observation", "Observed Total Catch"),)
output_map = (("Catch Observation", (("Fish Population", "level"),)),)
```

---

## Canonical Spectrum with Output Map

| Domain | |X| | |f| | |C| | Form |
|--------|-----|-----|-----|------|
| OGS (games) | 0 | 0 | 0 | h = g |
| Control | n | n | m | h = f ∘ g, y = C(x, d) |
| StockFlow | n | n | 0 | h = f ∘ g |
| Insurance | 2 | 2 | 1 | h = f ∘ g, y = C(x, d) |
| Fishery (V2) | n+2 | n+2 | 1 | h = f ∘ g, y = C(x, d) |

Domains where `|C| > 0` support observability analysis. Domains where `|C| = 0`
have no output map — all state is internal.

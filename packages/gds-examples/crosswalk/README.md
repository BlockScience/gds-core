# Crosswalk Problem

Discrete Markov state transitions with mechanism design — the canonical GDS example from BlockScience.

A pedestrian on one side of a one-way street wants to reach a destination on the other side. They decide whether to cross and where. Traffic evolves as a discrete Markov chain. A governance body chooses where to place the crosswalk to minimize accident probability — **mechanism design** in its simplest form.

## Source Material

This example is based on the Generalized Dynamical Systems lectures and papers by Michael Zargham and Jamsheed Shorish at BlockScience:

- [GDS Lecture 1 — Foundations](https://www.youtube.com/watch?v=8t-FKDzrnmA)
- [GDS Lecture 2 — Crosswalk Problem](https://www.youtube.com/watch?v=F3BsilIxgbY)
- [GDS Lecture 3 — Reachability & Controllability](https://www.youtube.com/watch?v=ZRkYH9JY_Xo)
- [Generalized Dynamical Systems Part I: Foundations (blog)](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/)

## GDS Decomposition

```
X  = traffic_state ∈ {-1, 0, +1}  — accident, stopped, flowing
U  = (luck, crossing_position)      — binary randomness + pedestrian location
s  = cross ∈ {0, 1}                 — pedestrian's binary crossing decision
g  = pedestrian_decision             — policy: observe → (s, p)
d  = safety_check                    — admissibility given crosswalk location k
f  = traffic_transition              — Markov state update
Θ  = {crosswalk_location}            — design parameter k ∈ [0, 1]
```

**Composition:** `observe >> decide >> check >> transition`

## Element Coverage

Every element from the BlockScience lectures is mapped to a GDS component:

| Lecture Element | GDS Component | Code |
|---|---|---|
| **State Space X** — Flowing(+1), Stopped(0), Accident(-1) | `TrafficState` typedef, `x ∈ {-1, 0, 1}` | `street` entity |
| **Decision s** — binary cross/not | `BinaryChoice` in `CrossingDecisionSpace.cross` | `pedestrian_decision` Policy |
| **Location p** — where to cross | `StreetPosition` in `CrossingDecisionSpace.position` | `pedestrian_decision` Policy |
| **Luck l** — binary exogenous (l=0 bad, l=1 good) | `BinaryChoice` in `ObservationSpace.luck` | `observe_traffic` BoundaryAction |
| **Parameter k** — crosswalk location | `crosswalk_location` registered as `StreetPosition` | `safety_check` ControlAction |
| **Transition f** — Markov matrix | `Traffic Transition` Mechanism | updates `("Street", "traffic_state")` |
| **Reachability** — is Accident reachable? | `check_reachability(spec, "Observe Traffic", "Traffic Transition")` | `test_model.py` |
| **Controllability** — k controls probabilities | param → ControlAction → Mechanism chain | Parameter influence view |

### What's intentionally NOT modeled

The **"modified crosswalk"** variant (where a driver stops mid-road and becomes a pedestrian) violates GDS sufficiency conditions — the state transition depends on the decision function itself, breaking the separation between procedural and decision automation. This is documented in the module docstring as a GDS limitation.

## Transition Rules

The Markov transition matrix entries encode three scenarios:

| Condition | Next State |
|---|---|
| Cross at crosswalk (`p = k`) | Stopped (0) — safely |
| Jaywalk (`p ≠ k`) with bad luck (`l = 0`) | Accident (-1) |
| Don't cross (`s = 0`) | Flowing (+1) — continues |

The optimal placement: **k at the median** of the pedestrian crossing distribution minimizes accident probability.

## Files

| File | Description |
|---|---|
| [model.py](model.py) | Types, entities, spaces, blocks, `build_spec()`, `build_system()` |
| [test_model.py](test_model.py) | 28 tests across 7 classes |
| [generate_views.py](generate_views.py) | 6 visualization views |
| [VIEWS.md](VIEWS.md) | Generated Mermaid diagrams |

## Running

```bash
uv run pytest examples/crosswalk/test_model.py -v         # run tests
uv run python examples/crosswalk/generate_views.py --save  # generate diagrams
```

## Prerequisites

Read these examples first:
1. [SIR Epidemic](../sir_epidemic/) — fundamentals (TypeDef, Entity, Space, roles)
2. [Insurance Contract](../insurance/) — ControlAction role, 4-role taxonomy

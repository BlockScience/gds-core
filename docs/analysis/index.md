# gds-analysis

[![PyPI](https://img.shields.io/pypi/v/gds-analysis)](https://pypi.org/project/gds-analysis/)
[![Python](https://img.shields.io/pypi/pyversions/gds-analysis)](https://pypi.org/project/gds-analysis/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Bridge from GDS structural specifications to runtime simulation and analysis.**

## What is this?

`gds-analysis` closes the gap between `gds-framework`'s structural annotations (AdmissibleInputConstraint, TransitionSignature) and `gds-sim`'s runtime engine. It provides the behavioral layer that turns verified specifications into executable models.

- **`spec_to_model()`** -- adapter that converts a `GDSSpec` + behavioral functions into a `gds_sim.Model`
- **`guarded_policy()`** -- wraps a policy function with `AdmissibleInputConstraint` enforcement at runtime
- **`reachable_set()`** -- computes the reachable set R(x) from an initial state by exploring the transition graph (Paper Def 4.1)
- **`reachable_graph()`** -- returns the full state transition graph as an adjacency structure
- **`configuration_space()`** -- finds the largest SCC of the reachability graph (Paper Def 4.2)
- **`trajectory_distances()`** -- computes metric distances along a trajectory for convergence analysis

## Architecture

```
gds-framework            gds-sim
|                        |
|  GDSSpec, entities,    |  Model, StateUpdateBlock,
|  blocks, constraints   |  Simulation, Results
|                        |
+-------+  gds-analysis  +-------+
        |                |
        |  spec_to_model(), guarded_policy(),
        |  reachable_set(), trajectory_distances()
        |
        +-- Your application
            |
            |  Verified specs -> executable simulations,
            |  reachability analysis, convergence proofs.
```

## Key Functions

| Function | Input | Output |
|----------|-------|--------|
| `spec_to_model(spec, policies, sufs, ...)` | `GDSSpec` + dict of callables | `gds_sim.Model` |
| `guarded_policy(policy_fn, constraint, fallback)` | callable + predicate + fallback | guarded callable |
| `reachable_set(spec, model, state, input_samples)` | spec + model + state + inputs | `list[dict]` |
| `reachable_graph(spec, model, states, input_samples)` | spec + model + states + inputs | adjacency dict |
| `configuration_space(graph)` | adjacency dict | largest SCC |
| `trajectory_distances(results, metric)` | `Results` + distance fn | `list[float]` |

## The Behavioral Gap

GDS specifications are structural -- they declare *what* blocks exist, how they wire together, and what constraints hold. But they do not contain *behavioral* functions (policies, state update functions). The adapter pattern separates structural (R1) from behavioral (R3):

- **Structural (from GDSSpec)**: block topology, wiring, role assignments, entity/variable declarations
- **Behavioral (from user)**: policy functions, state update functions, initial conditions
- **Bridge**: `spec_to_model()` wires user-supplied callables into the structural skeleton

## Constraint Enforcement

`guarded_policy()` wraps a policy function so that `AdmissibleInputConstraint` predicates are checked at every timestep. If a constraint is violated, the guard invokes the fallback function or raises `ConstraintViolationError` with the failing constraint's name and the offending input values.

## Quick Start

```bash
uv add gds-analysis
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on [gds-framework](../framework/index.md) and [gds-sim](https://pypi.org/project/gds-sim/) by [BlockScience](https://block.science).

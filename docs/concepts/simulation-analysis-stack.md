# Simulation and Analysis Stack

The simulation and analysis packages form a pipeline around the framework. The
framework provides structure; the runtime packages provide behavior; the
analysis packages evaluate many behaviors.

```text
Domain DSLs
  stockflow / control / games / software / business / symbolic
        |
        v
gds-framework
  typed specification + structural verification
        |
        v
gds-analysis
  bridge selected specifications to executable runtime models
        |
        v
gds-sim / gds-continuous
  run discrete or continuous trajectories
        |
        v
gds_analysis.psuu
  sweep, optimize, score, and analyze sensitivity
```

## Choosing an Entry Point

| You have | Start with |
|----------|------------|
| A structural model or DSL model | [`gds-framework`](../framework/index.md), then a domain package or `gds-analysis` |
| Plain Python timestep update functions | [`gds-sim`](../sim/index.md) |
| ODE equations | [`gds-continuous`](../continuous/index.md) |
| A runnable simulation and parameters to test | [PSUU](../psuu/index.md) |
| Invariants to prove symbolically | [`gds-proof`](../proof/index.md) |
| RDF/OWL interchange needs | [`gds-interchange`](../owl/index.md) |

## Package Roles

### `gds-analysis`

`gds-analysis` is the bridge package. It sits between structural GDS models and
runtime analysis workflows. Use it when you want to convert supported
`GDSSpec` annotations into simulation components or when you want analysis
utilities that understand GDS structures.

### `gds-sim`

`gds-sim` is the discrete-time runtime. It runs models made from an
`initial_state`, policy functions, state update functions, and parameter sets.
It is a direct dependency for PSUU workflows.

### `gds-continuous`

`gds-continuous` is the continuous-time runtime. Use it when the model is an ODE
system and should be integrated with a numerical solver.

### PSUU

PSUU is the parameter-space analysis layer under `gds_analysis.psuu`. It runs a
simulation model at many parameter points, computes KPIs, and compares results
with grid, random, or Bayesian search.

## Typical Workflows

| Workflow | Path |
|----------|------|
| First simulation | `gds-sim` -> inspect `Results` |
| Parameter search | `gds-sim` -> PSUU `ParameterSpace` -> `Sweep` |
| Spec-first analysis | `gds-framework` -> `gds-analysis` -> `gds-sim` |
| Continuous model | symbolic/control model -> `gds-continuous` |
| Robustness study | simulation model -> PSUU KPIs -> sensitivity analyzer |

## Documentation Map

- [Simulation package guide](../sim/index.md) explains the runtime.
- [Simulation how-to](../guides/simulation.md) walks through the shortest
  practical flow.
- [PSUU package guide](../psuu/index.md) explains parameter search concepts.
- [Parameter-sweep how-to](../guides/parameter-sweep.md) shows a complete sweep.
- [Package stack overview](../packages/simulation-analysis.md) summarizes the
  same relationships from a package-selection perspective.


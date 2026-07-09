# Simulation & Analysis

GDS separates structural specification from execution. `gds-framework` defines
typed systems and verifies their structure; simulation and analysis packages run
or evaluate behavior once executable semantics are available.

## The Stack

```text
Domain DSLs
  stockflow / control / games / software / business
        |
        v
gds-framework
  typed specification + verification
        |
        v
gds-analysis
  bridge selected GDSSpec structures to runtime models
        |
        v
gds-sim / gds-continuous
  execute trajectories
        |
        v
gds_analysis.psuu
  sweep, optimize, score, and analyze sensitivity
```

## Package Roles

| Package | Use It For | Import |
|---|---|---|
| [gds-framework](../framework/index.md) | Defining typed specifications, compiling to IR, and structural verification | `gds` |
| [gds-analysis](../analysis/index.md) | Bridging `GDSSpec` annotations into simulation workflows and reachability analysis | `gds_analysis` |
| [gds-sim](../sim/index.md) | Running standalone discrete-time models with plain Python policy and state update functions | `gds_sim` |
| [gds-continuous](../continuous/index.md) | Running continuous-time ODE simulations | `gds_continuous` |
| [PSUU](../psuu/index.md) | Running parameter sweeps, KPI scoring, optimization, and sensitivity analysis | `gds_analysis.psuu` |

## When To Use Each Runtime

Use `gds-sim` when your model advances in discrete timesteps and can be
expressed as policy functions plus state update functions.

Use `gds-continuous` when your model is an ODE system and should be solved with
continuous-time numerical integration.

Use `gds-analysis` when you start from a verified `GDSSpec` and need a bridge
from structural annotations to executable model components.

Use `gds_analysis.psuu` when you already have a simulation model and want to
evaluate many parameter points, optimize KPI scores, or estimate parameter
sensitivity.

## Specification Is Not Execution

`gds-framework` intentionally focuses on typed structure, canonical GDS roles,
composition, and verification. It can say whether a specification is well formed,
but it does not directly run trajectories.

This split keeps the core framework domain-neutral:

- structural correctness belongs in `gds-framework`
- executable runtime semantics belong in `gds-sim` or `gds-continuous`
- translation from specification to runtime belongs in `gds-analysis`
- parameter-space exploration belongs in `gds_analysis.psuu`

For a fuller explanation, see
[Specification vs Execution](../concepts/specification-vs-execution.md).

## Common Paths

| Starting Point | Path |
|---|---|
| Plain Python state update functions | `gds-sim` -> `gds_analysis.psuu` |
| Verified `GDSSpec` | `gds-framework` -> `gds-analysis` -> `gds-sim` |
| ODE equations | `gds-continuous` |
| Control model with symbolic equations | `gds_domains.control` -> `gds_domains.symbolic` -> `gds-continuous` |
| Parameter calibration or robustness screening | simulation model -> `gds_analysis.psuu` |

## Next Steps

- Run a first discrete-time model with [gds-sim](../sim/getting-started.md).
- Follow the [simulation how-to](../guides/simulation.md).
- Convert a spec to a runnable model with [gds-analysis](../analysis/getting-started.md).
- Explore parameter search with [PSUU](../psuu/getting-started.md) or the
  [parameter-sweep how-to](../guides/parameter-sweep.md).

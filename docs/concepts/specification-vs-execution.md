# Specification vs Execution

GDS separates the question "is this system well-formed?" from the question
"what happens when this system runs?"

`gds-framework` owns typed specification. It describes blocks, roles, spaces,
entities, state variables, composition, and verification checks. It can compile
a model into an intermediate representation and report structural problems.

Execution packages own runtime behavior. They advance state through time,
evaluate policy functions, integrate ODE systems, or score simulation results
under parameter variation.

## Why the Split Exists

A GDS specification is domain-neutral. It can express a stock-flow model, a
control model, a game, a software diagram, or a business process using the same
structural vocabulary. That neutrality is useful because the framework can
verify common properties without knowing a package-specific runtime.

A simulation runtime is domain-specific in a different way. It must know how
time advances, how update functions are called, how random runs are repeated,
and how results are stored. Those decisions do not belong in the framework core.

## Responsibilities

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Specification | [`gds-framework`](../framework/index.md) | Typed model structure, composition algebra, compiler, structural verification |
| Domain modeling | DSL packages | User-facing model language for games, stock-flow, control, software, business, and symbolic math |
| Runtime bridge | [`gds-analysis`](../analysis/index.md) | Convert selected structural annotations into executable simulation components |
| Discrete execution | [`gds-sim`](../sim/index.md) | Run timestep-based state update models |
| Continuous execution | [`gds-continuous`](../continuous/index.md) | Integrate ODE systems with SciPy solvers |
| Parameter analysis | [PSUU](../psuu/index.md) | Sweep, optimize, and score simulation models under uncertainty |

## What Verification Means

Framework verification checks whether the specification is coherent:

- entities and state variables are declared consistently
- roles and spaces line up with block interfaces
- composition wiring is structurally valid
- domain packages satisfy their compile-time contracts

It does not imply that a trajectory has been executed, that every numerical
case has been explored, or that a KPI has been optimized. Those are analysis
tasks.

## What Simulation Means

Simulation starts once executable semantics are available. In `gds-sim`, that
means a `Model` with an `initial_state`, `StateUpdateBlock` objects, optional
policies, update functions, and parameters. In `gds-continuous`, it means an ODE
right-hand side and solver settings.

The output is runtime data: trajectories, runs, parameter subsets, and derived
metrics. This data can then feed PSUU for parameter sweeps, KPI scoring,
optimization, and sensitivity analysis.

## Common Confusions

| Question | Short answer |
|----------|--------------|
| Can `gds-framework` run my model? | No. It verifies and compiles structure; execution belongs to runtime packages. |
| Is `gds-sim` part of the API reference? | It has API pages, but the conceptual entry point is the package documentation under Packages. |
| Do I need `gds-analysis` for every simulation? | No. Use `gds-sim` directly for plain Python runtime models. Use `gds-analysis` when starting from `GDSSpec` annotations. |
| Is PSUU a separate package? | It is provided under `gds_analysis.psuu` and installed through `gds-analysis`. |

## Next Steps

- See the [simulation and analysis stack](simulation-analysis-stack.md) for the
  package flow.
- Run a first discrete model with the [simulation guide](../guides/simulation.md).
- Sweep parameters with the [parameter-sweep guide](../guides/parameter-sweep.md).


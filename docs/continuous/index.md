# gds-continuous

[![PyPI](https://img.shields.io/pypi/v/gds-continuous)](https://pypi.org/project/gds-continuous/)
[![Python](https://img.shields.io/pypi/pyversions/gds-continuous)](https://pypi.org/project/gds-continuous/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Continuous-time ODE integration engine** -- the continuous-time counterpart to `gds-sim`.

## What is this?

`gds-continuous` provides an ODE simulation engine for continuous-time dynamical systems. It follows the same standalone architectural pattern as `gds-sim` -- minimal dependencies, Pydantic models, columnar results -- but integrates SciPy's ODE solvers instead of discrete timestep iteration.

- **`ODEModel`** -- declares state variables, initial conditions, and a right-hand side function `dx/dt = f(t, x, params)`
- **`ODESimulation`** -- configures time span, solver method, tolerances, and evaluation points
- **`ODEResults`** -- columnar storage of time series with named state access
- **6 solver methods** -- `RK45`, `RK23`, `DOP853`, `Radau`, `BDF`, `LSODA` (all via `scipy.integrate.solve_ivp`)
- **Zero GDS dependency** -- standalone package, same as `gds-sim`

## Architecture

```
scipy + numpy (optional deps)
|
+-- gds-continuous (uv add gds-continuous[scipy])
    |
    |  ODE engine: ODEModel, ODESimulation, ODEResults.
    |  6 solver backends via scipy.integrate.solve_ivp.
    |
    +-- Your application
        |
        |  Concrete ODE models, parameter studies,
        |  phase portraits, trajectory analysis.
```

## Relationship to gds-sim

| | gds-sim | gds-continuous |
|---|---|---|
| **Time** | Discrete timesteps | Continuous `t_span` |
| **Update rule** | `f(state, params) -> state` | `dx/dt = f(t, x, params)` |
| **Solver** | Direct iteration | SciPy `solve_ivp` |
| **Results** | `Results` (timestep-indexed) | `ODEResults` (time-indexed) |
| **Dependencies** | pydantic only | pydantic + scipy + numpy |

Both are standalone engines with no `gds-framework` dependency. They can be used independently or bridged via `gds-analysis`.

## Solver Methods

| Method | Type | Best for |
|--------|------|----------|
| `RK45` | Explicit Runge-Kutta (default) | General non-stiff problems |
| `RK23` | Explicit Runge-Kutta | Low-accuracy requirements |
| `DOP853` | Explicit Runge-Kutta | High-accuracy non-stiff problems |
| `Radau` | Implicit Runge-Kutta | Stiff problems |
| `BDF` | Implicit multi-step | Stiff problems |
| `LSODA` | Automatic stiff/non-stiff | Unknown stiffness |

## Quick Start

```bash
uv add "gds-continuous[scipy]"
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built by [BlockScience](https://block.science).

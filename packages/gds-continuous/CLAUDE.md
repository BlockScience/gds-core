# CLAUDE.md -- gds-continuous

## Package Identity

`gds-continuous` is a continuous-time ODE integration engine for the GDS
ecosystem. It wraps `scipy.integrate.solve_ivp` with a Pydantic-validated
model layer and columnar result storage.

- **PyPI**: `gds-continuous` (install with `uv add gds-continuous[scipy]`)
- **Import**: `import gds_continuous`
- **Standalone**: pydantic-only runtime dep (like gds-sim). No gds-framework dependency.

## Architecture

Mirrors `gds-sim` but for continuous-time:

| gds-sim (discrete) | gds-continuous | Difference |
|---------------------|----------------|------------|
| `Model` | `ODEModel` | State as `dict[str, float]`, not `dict[str, Any]` |
| `Simulation` | `ODESimulation` | `t_span` + solver config instead of `timesteps` |
| `Results` | `ODEResults` | `time` (float) instead of `timestep`/`substep` |
| `StateUpdateBlock` | `ODEFunction` | Single RHS callable, not policy+SUF split |

## Known Limitations

### GDSSpec-to-ODEModel bridge gap

There is no `spec_to_ode_model()` adapter (unlike `gds-analysis.spec_to_model()`
for discrete-time). The intended workflow for verified continuous-time simulation:

```
SymbolicControlModel
  .compile()          --> GDSSpec   (structural verification via SC-001..SC-009)
  .to_ode_function()  --> ODEFunction (behavioral, R3)

ODEModel(state_names=..., initial_state=..., rhs=ode_fn)
  --> ODESimulation.run() --> ODEResults
```

Initial conditions are a user concern -- GDSSpec carries structural metadata
(entities, variables, types), not simulation state. This is by design:
GDS separates specification (what the system IS) from execution (what it DOES).

A future `gds-analysis` continuous adapter could bridge this gap.

### Time-varying inputs

`ODEModel.params` are run-constant (fixed for the entire trajectory).
GDS `BoundaryAction` / `Input` elements represent per-timestep exogenous
signals, but `compile_to_ode()` in gds-symbolic resolves them from `params`
at each RHS evaluation. This means inputs are constant, not time-varying.

For time-varying inputs, construct the `ODEFunction` manually with a
closure over a time-dependent input function:

```python
def my_rhs(t, y, params):
    u = sin(t)  # time-varying input
    return [-params["k"] * y[0] + u]
```

### No parallelism

Unlike gds-sim (which has `parallel.py` with `ProcessPoolExecutor`),
gds-continuous executes parameter sweeps sequentially. For isochrone
computation (many separate initial conditions), each trajectory is
integrated in a loop. This is adequate for interactive notebooks but
may be slow for large sweeps.

## Commands

```bash
uv run --package gds-continuous pytest packages/gds-continuous/tests -v
```

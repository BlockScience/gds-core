# CLAUDE.md -- gds-analysis

## Package Identity

`gds-analysis` bridges `gds-framework` structural annotations to `gds-sim` runtime, enabling constraint enforcement, metric computation, and reachability analysis on concrete trajectories.

- **Import**: `import gds_analysis`
- **Dependencies**: `gds-framework>=0.2.3`, `gds-sim>=0.1.0`
- **Optional**: `[continuous]` for `gds-continuous[scipy]` + numpy (backward reachability)

## Architecture

Seven modules bridging structural specification to runtime analysis:

| Module | Function | Paper reference |
|--------|----------|-----------------|
| `adapter.py` | `spec_to_model(spec, policies, sufs, ...)` → `gds_sim.Model` | — |
| `constraints.py` | `guarded_policy(policy_fn, constraint)` → wrapped policy | Def 2.5 |
| `metrics.py` | `trajectory_distances(results, spec)` → distance matrix | Assumption 3.2 |
| `reachability.py` | `reachable_set(model, state, inputs)` → R(x) | Def 4.1, 4.2 |
| `backward_reachability.py` | `backward_reachable_set(dynamics, ...)` → B(T) | Def 4.1 (backward) |
| `linear.py` | Eigenvalue stability, frequency response, margins, discretization, LQR, Kalman | `[continuous]` |
| `response.py` | Step/impulse response computation + time-domain metrics (StepMetrics) | `[continuous]` |

### spec_to_model adapter

Maps GDS block roles to gds-sim execution primitives:
- `BoundaryAction` / `Policy` / `ControlAction` → policies dict
- `Mechanism` → SUFs dict (state update functions)
- Users supply the behavioral callables (R3); the adapter wires them using the structural skeleton (R1)

If `enforce_constraints=True`, wraps BoundaryAction policies with `guarded_policy()` using any registered `AdmissibleInputConstraint`.

### Reachability

- `reachable_set(spec, model, state, input_samples)` — computes R(x) by running one timestep per input sample
- `reachable_graph(spec, model, states, input_samples)` — builds full reachability graph across multiple states
- `configuration_space(reachability_graph)` — extracts largest SCC (the configuration space X_C)

### Linear systems analysis (`linear.py`, requires `[continuous]`)

All functions accept `list[list[float]]` matrices (matching `LinearizedSystem` fields):
- `eigenvalues(A)`, `is_stable(A)`, `is_marginally_stable(A)` — stability checks
- `frequency_response(A, B, C, D, omega)` → `(omega, mag_db, phase_deg)`
- `gain_margin(num, den)`, `phase_margin(num, den)` — stability margins
- `discretize(A, B, C, D, dt, method)` → `(Ad, Bd, Cd, Dd)` via scipy.signal
- `lqr(A, B, Q, R)`, `dlqr(Ad, Bd, Q, R)` → `(K, P, E)` gain + Riccati + eigenvalues
- `kalman(A, C, Q, R)` → `(L, P)` observer gain + covariance
- `gain_schedule(linearize_fn, points, Q, R)` → gains at multiple operating points

### Response metrics (`response.py`)

- `step_response_metrics(times, values, setpoint)` → `StepMetrics` (no scipy needed)
- `step_response(A, B, C, D)`, `impulse_response(A, B, C, D)` — scipy-based simulation

## Commands

```bash
uv run --package gds-analysis pytest packages/gds-analysis/tests -v
```

# CLAUDE.md -- gds-analysis

## Package Identity

`gds-analysis` bridges `gds-framework` structural annotations to `gds-sim` runtime, enabling constraint enforcement, metric computation, and reachability analysis on concrete trajectories.

- **Import**: `import gds_analysis`
- **Dependencies**: `gds-framework>=0.2.3`, `gds-sim>=0.1.0`

## Architecture

Four modules, each bridging one aspect of structural specification to runtime:

| Module | Function | Paper reference |
|--------|----------|-----------------|
| `adapter.py` | `spec_to_model(spec, policies, sufs, ...)` → `gds_sim.Model` | — |
| `constraints.py` | `guarded_policy(policy_fn, constraint)` → wrapped policy | Def 2.5 |
| `metrics.py` | `trajectory_distances(results, spec)` → distance matrix | — |
| `reachability.py` | `reachable_set(spec, model, state, inputs)` → R(x) | Def 4.1, 4.2 |

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

## Commands

```bash
uv run --package gds-analysis pytest packages/gds-analysis/tests -v
```

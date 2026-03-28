# CLAUDE.md -- gds-viz

## Package Identity

`gds-viz` provides visualization for GDS specifications: Mermaid diagram renderers (structural, canonical, architecture, traceability) and phase portrait plotting for continuous-time systems.

- **Import**: `import gds_viz`
- **Dependencies**: `gds-framework>=0.2.3`
- **Optional**: `[phase]` for matplotlib + numpy + gds-continuous (phase portraits)

## Architecture

### Mermaid renderers (no optional deps)

| Function | Input | Output |
|----------|-------|--------|
| `system_to_mermaid(ir)` | SystemIR | Structural block diagram |
| `block_to_mermaid(block)` | Block | Single block diagram |
| `spec_to_mermaid(spec)` | GDSSpec | Architecture by role/domain |
| `canonical_to_mermaid(can)` | CanonicalGDS | h = f . g decomposition |
| `trace_to_mermaid(spec, entity, var)` | GDSSpec | Backward traceability |
| `params_to_mermaid(spec)` | GDSSpec | Parameter influence graph |

### Phase portraits (`gds_viz.phase`, requires `[phase]`)

| Function | Purpose |
|----------|---------|
| `phase_portrait(model, x_var, y_var, ...)` | Full portrait: vector field + trajectories + nullclines |
| `vector_field_plot(model, config)` | Quiver plot only |
| `trajectory_plot(results, x_var, y_var)` | Trajectories in phase space |
| `compute_vector_field(model, config)` | Raw (X, Y, dX, dY) arrays |
| `compute_trajectories(model, ics, ...)` | Integrate multiple ICs → list[ODEResults] |

Supports >2D systems via `fixed_states` projection (e.g., Lorenz z=25 slice).

## Commands

```bash
uv run --package gds-viz pytest packages/gds-viz/tests -v
```

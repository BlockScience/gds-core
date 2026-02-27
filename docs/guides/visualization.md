# Visualization Guide

A feature showcase for `gds-viz`, demonstrating all 6 view types, 5 built-in Mermaid themes, and cross-DSL visualization. Every diagram renders in GitHub, GitLab, VS Code, Obsidian, and mermaid.live.

## The 6 GDS Views

Every GDS model can be visualized from 6 complementary perspectives. Each view answers a different question about the system's structure.

| # | View | Input | Question Answered |
|:-:|------|-------|-------------------|
| 1 | Structural | `SystemIR` | What is the compiled block topology? |
| 2 | Canonical | `CanonicalGDS` | What is the formal h = f . g decomposition? |
| 3 | Architecture by Role | `GDSSpec` | How are blocks organized by GDS role? |
| 4 | Architecture by Domain | `GDSSpec` | How are blocks organized by domain ownership? |
| 5 | Parameter Influence | `GDSSpec` | If I change a parameter, what is affected? |
| 6 | Traceability | `GDSSpec` | What could cause this state variable to change? |

### View 1: Structural

The compiled block graph from `SystemIR`. Shows composition topology with role-based shapes and wiring types.

**Shape conventions:**

- Stadium `([...])` = BoundaryAction (exogenous input, no forward_in)
- Double-bracket `[[...]]` = terminal Mechanism (state sink, no forward_out)
- Rectangle `[...]` = Policy or other block with both inputs and outputs

**Arrow conventions:**

- Solid arrow `-->` = covariant forward flow
- Dashed arrow `-.->` = temporal loop (cross-timestep)
- Thick arrow `==>` = feedback (within-timestep, contravariant)

**API:** `system_to_mermaid(system)`

### View 2: Canonical GDS

The mathematical decomposition: X_t --> U --> g --> f --> X_{t+1}. Shows the abstract dynamical system with state (X), input (U), policy (g), mechanism (f), and parameter space (Theta).

**API:** `canonical_to_mermaid(canonical)`

### View 3: Architecture by Role

Blocks grouped by GDS role: Boundary (U), Policy (g), Mechanism (f). Entity cylinders show which state variables each mechanism writes.

**API:** `spec_to_mermaid(spec)`

### View 4: Architecture by Domain

Blocks grouped by domain tag. Shows organizational ownership of blocks. Blocks without the tag go into "Ungrouped".

**API:** `spec_to_mermaid(spec, group_by="domain")`

### View 5: Parameter Influence

Theta --> blocks --> entities causal map. Answers: "if I change parameter X, which state variables are affected?" Shows parameter hexagons, the blocks they feed, and the entities those blocks transitively update.

**API:** `params_to_mermaid(spec)`

### View 6: Traceability

Backwards trace from one state variable. Answers: "what blocks and parameters could cause this variable to change?" Direct mechanisms get thick arrows, transitive dependencies get normal arrows, and parameter connections get dashed arrows.

**API:** `trace_to_mermaid(spec, entity, variable)`

### Generating All Views

```python
from gds.canonical import project_canonical
from gds_viz import (
    canonical_to_mermaid,
    params_to_mermaid,
    spec_to_mermaid,
    system_to_mermaid,
    trace_to_mermaid,
)

# From any model's build functions:
spec = build_spec()
system = build_system()
canonical = project_canonical(spec)

views = {
    "structural": system_to_mermaid(system),
    "canonical": canonical_to_mermaid(canonical),
    "architecture_by_role": spec_to_mermaid(spec),
    "architecture_by_domain": spec_to_mermaid(spec, group_by="domain"),
    "parameter_influence": params_to_mermaid(spec),
    "traceability": trace_to_mermaid(spec, "Susceptible", "count"),
}
```

---

## Theme Customization

Every `gds-viz` view function accepts a `theme=` parameter. There are **5 built-in Mermaid themes** that adjust node fills, strokes, text colors, and subgraph backgrounds.

| Theme | Best for |
|-------|----------|
| `neutral` | Light backgrounds (GitHub, docs) -- **default** |
| `default` | Mermaid's blue-toned Material style |
| `dark` | Dark-mode renderers |
| `forest` | Green-tinted, earthy |
| `base` | Minimal chrome, very light |

### Usage

```python
from gds_viz import system_to_mermaid

# Apply any theme to any view
mermaid_str = system_to_mermaid(system, theme="dark")
```

### All Views Support Themes

Themes work with every view function:

```python
from gds_viz import (
    system_to_mermaid,
    canonical_to_mermaid,
    spec_to_mermaid,
    params_to_mermaid,
    trace_to_mermaid,
)

system_to_mermaid(system, theme="forest")
canonical_to_mermaid(canonical, theme="dark")
spec_to_mermaid(spec, theme="base")
params_to_mermaid(spec, theme="default")
trace_to_mermaid(spec, "Entity", "variable", theme="neutral")
```

### Neutral vs Dark Comparison

The two most common choices:

- **Neutral** (default): muted gray canvas with saturated node fills. Best for light-background rendering (GitHub, VS Code light mode, documentation sites).
- **Dark**: dark canvas with saturated fills and light text. Optimized for dark-mode renderers.

---

## Cross-DSL Views

The `gds-viz` API is **DSL-neutral** -- it operates on `GDSSpec` and `SystemIR`, which every compilation path produces. Regardless of how a model is built (raw GDS blocks, stockflow DSL, control DSL, or games DSL), the same view functions work unchanged.

### Example: Hand-Built vs DSL-Compiled

```python
# Hand-built model (SIR Epidemic)
from sir_epidemic.model import build_spec, build_system
sir_spec = build_spec()
sir_system = build_system()
sir_structural = system_to_mermaid(sir_system)

# DSL-compiled model (Double Integrator via gds-control)
from double_integrator.model import build_spec, build_system
di_spec = build_spec()
di_system = build_system()
di_structural = system_to_mermaid(di_system)

# Same API, same function, different models -- works identically
```

Both models decompose into the same `h = f . g` structure, but with different dimensionalities. The SIR model has parameters (Theta); the double integrator may not. The visualization layer does not care about the construction path -- it only sees the compiled IR.

### Supported DSL Sources

| Source | Path to GDSSpec | Path to SystemIR |
|--------|----------------|------------------|
| Raw GDS | Manual `build_spec()` | `compile_system(name, root)` |
| gds-stockflow | `stockflow.dsl.compile.compile_model()` | `stockflow.dsl.compile.compile_to_system()` |
| gds-control | `gds_control.dsl.compile.compile_model()` | `gds_control.dsl.compile.compile_to_system()` |
| gds-games | `ogs.dsl.spec_bridge.compile_pattern_to_spec()` | via `PatternIR.to_system_ir()` |

---

## API Quick Reference

All functions live in `gds_viz` and return Mermaid strings.

| Function | Input | View |
|----------|-------|------|
| `system_to_mermaid(system)` | `SystemIR` | Structural |
| `canonical_to_mermaid(canonical)` | `CanonicalGDS` | Canonical |
| `spec_to_mermaid(spec)` | `GDSSpec` | By role |
| `spec_to_mermaid(spec, group_by=...)` | `GDSSpec` | By domain |
| `params_to_mermaid(spec)` | `GDSSpec` | Parameters |
| `trace_to_mermaid(spec, ent, var)` | `GDSSpec` | Traceability |

All accept an optional `theme=` parameter: `"neutral"`, `"default"`, `"dark"`, `"forest"`, `"base"`.

### Usage Pattern

```python
from gds_viz import system_to_mermaid
from my_model import build_system

system = build_system()
mermaid_str = system_to_mermaid(system, theme="dark")
# Paste into GitHub markdown, mermaid.live, or mo.mermaid()
```

## Running Interactively

The guide includes a [marimo notebook](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/visualization/notebook.py) with interactive dropdowns for selecting views, themes, and models:

```bash
uv run marimo run packages/gds-examples/guides/visualization/notebook.py
```

Run the test suite:

```bash
uv run --package gds-examples pytest packages/gds-examples/guides/visualization/ -v
```

## Source Files

| File | Purpose |
|------|---------|
| [`all_views_demo.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/visualization/all_views_demo.py) | All 6 view types on the SIR model |
| [`theme_customization.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/visualization/theme_customization.py) | 5 built-in theme demos |
| [`cross_dsl_views.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/visualization/cross_dsl_views.py) | Cross-DSL visualization comparison |
| [`notebook.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/visualization/notebook.py) | Interactive marimo notebook |

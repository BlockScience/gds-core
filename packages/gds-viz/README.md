# gds-viz

[![PyPI](https://img.shields.io/pypi/v/gds-viz)](https://pypi.org/project/gds-viz/)
[![Python](https://img.shields.io/pypi/pyversions/gds-viz)](https://pypi.org/project/gds-viz/)
[![License](https://img.shields.io/github/license/BlockScience/gds-viz)](LICENSE)

Mermaid diagram renderers for [gds-framework](https://github.com/BlockScience/gds-framework) specifications.

```bash
uv add gds-viz
# or: pip install gds-viz
```

## Views

gds-viz provides six views — each a different projection of the GDS specification `{h, X}`:

| View | Function | Input | Answers |
|---|---|---|---|
| 1. Structural | `system_to_mermaid()` | `SystemIR` | What blocks exist and how are they wired? |
| 2. Canonical GDS | `canonical_to_mermaid()` | `CanonicalGDS` | What is the formal decomposition h = f ∘ g? |
| 3. Architecture (role) | `spec_to_mermaid()` | `GDSSpec` | How do blocks group by GDS role? |
| 4. Architecture (domain) | `spec_to_mermaid(group_by=...)` | `GDSSpec` | How do blocks group by domain/agent? |
| 5. Parameter influence | `params_to_mermaid()` | `GDSSpec` | What does each parameter control? |
| 6. Traceability | `trace_to_mermaid()` | `GDSSpec` | What can affect a specific state variable? |

### View 1: Structural

The compiled block graph from `SystemIR`. Shows composition topology — sequential, parallel, feedback, temporal — with role-based shapes (stadium for boundary, double-bracket for mechanism) and wiring types (solid, dashed, thick).

```python
from gds_viz import system_to_mermaid
mermaid = system_to_mermaid(system)
```

### View 2: Canonical GDS

The mathematical decomposition: `X_t → U → g → f → X_{t+1}` with parameter space Θ. Derives from `CanonicalGDS` (via `project_canonical(spec)`). Shows state variables in X nodes, role subgraphs, labeled update edges, and parameter dependencies.

```python
from gds.canonical import project_canonical
from gds_viz import canonical_to_mermaid
mermaid = canonical_to_mermaid(project_canonical(spec))
```

### Views 3 & 4: Architecture

Domain-level diagrams from `GDSSpec`. Show entity state cylinders, typed wire labels (from `Wire.space`), and mechanism-to-entity update edges. View 3 groups by GDS role; View 4 groups by any tag key.

```python
from gds_viz import spec_to_mermaid
by_role = spec_to_mermaid(spec)                    # View 3
by_agent = spec_to_mermaid(spec, group_by="domain") # View 4
```

Tags are set on blocks at definition time:

```python
sensor = BoundaryAction(name="Sensor", ..., tags={"domain": "Observation"})
```

### View 5: Parameter Influence

Shows Θ → block → entity causal map. Hexagon nodes for parameters, dashed edges to blocks that use them, then forward through the dependency graph to entities. Answers: "if I change parameter X, what state is affected?"

```python
from gds_viz import params_to_mermaid
mermaid = params_to_mermaid(spec)
```

### View 6: Traceability

For a single entity variable, traces every block that can transitively affect it and every parameter feeding those blocks. Right-to-left layout with thick edges for direct updates. Answers: "what controls this variable?"

```python
from gds_viz import trace_to_mermaid
mermaid = trace_to_mermaid(spec, "Susceptible", "count")
```

<details>
<summary><strong>What gds-viz does NOT cover</strong></summary>

The six views above exhaust what is **derivable from the GDS specification** `{h, X}`. Two commonly requested views are deliberately excluded:

**State Machine View** — requires discrete states and transition guards. GDS defines a continuous state space X, not a finite set of named states. Discretizing X is domain-specific interpretation, not derivable from `{h, X}`.

**Simulation / Execution Order View** — requires operational semantics (when blocks execute, in what order, with what timing). GDS specifies only structural relationships. The composition algebra defines topology, not a runtime.

| Concern | In GDS? | Where it belongs |
|---|---|---|
| State space, block topology, dependencies, parameters | Yes | `GDSSpec`, `SystemIR`, `SpecQuery` |
| Discrete state machine | **No** | Domain-specific layer or `gds-sim` |
| Execution schedule, time semantics | **No** | Simulator / runtime (`gds-sim`) |

A future `gds-sim` package could add execution semantics, making these views derivable from `(GDSSpec, SimConfig)`.

</details>

## License

Apache-2.0

---
Built with [Claude Code](https://claude.ai/code). All code is test-driven and human-reviewed.

## Credits & Attribution

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/BlockScience/MSML) and [bdp-lib](https://github.com/BlockScience/bdp-lib).

**Contributors:**
* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (BlockScience).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (BlockScience).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

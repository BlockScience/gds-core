# Views

gds-viz provides six complementary views of a GDS specification.

## View 1: Structural

The compiled block graph from `SystemIR`. Shows composition topology — sequential, parallel, feedback, temporal — with role-based shapes and wiring types.

```python
from gds_viz import system_to_mermaid
mermaid = system_to_mermaid(system)
```

**Shape conventions:**

- Stadium `([...])` — BoundaryAction
- Double-bracket `[[...]]` — Mechanism
- Rectangle `[...]` — Policy / other
- Solid arrow `-->` — covariant forward flow
- Thick arrow `==>` — contravariant feedback
- Dashed arrow `-.->` — temporal loop

## View 2: Canonical GDS

The mathematical decomposition: `X_t → U → g → f → X_{t+1}` with parameter space Θ. Derives from `CanonicalGDS`.

```python
from gds.canonical import project_canonical
from gds_viz import canonical_to_mermaid
mermaid = canonical_to_mermaid(project_canonical(spec))
```

Shows state variables in X nodes, role subgraphs (U, g, f), labeled update edges, and parameter dependencies.

## Views 3 & 4: Architecture

Domain-level diagrams from `GDSSpec`. Show entity state cylinders, typed wire labels, and mechanism-to-entity update edges.

```python
from gds_viz import spec_to_mermaid

by_role = spec_to_mermaid(spec)                      # View 3: group by role
by_agent = spec_to_mermaid(spec, group_by="domain")  # View 4: group by tag
```

View 3 groups blocks by GDS role (Boundary, Policy, Mechanism, ControlAction). View 4 groups by any tag key — set tags on blocks at definition time:

```python
sensor = BoundaryAction(name="Sensor", ..., tags={"domain": "Observation"})
```

## View 5: Parameter Influence

Shows Θ → block → entity causal map. Hexagon nodes for parameters, dashed edges to blocks that use them, then forward through the dependency graph to entities.

```python
from gds_viz import params_to_mermaid
mermaid = params_to_mermaid(spec)
```

Answers: "if I change parameter X, what state is affected?"

## View 6: Traceability

For a single entity variable, traces every block that can transitively affect it and every parameter feeding those blocks.

```python
from gds_viz import trace_to_mermaid
mermaid = trace_to_mermaid(spec, "Susceptible", "count")
```

Right-to-left layout with thick edges for direct updates. Answers: "what controls this variable?"

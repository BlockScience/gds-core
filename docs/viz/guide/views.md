# Views Gallery

gds-viz provides six complementary views of a GDS specification. Each view is a different projection of the same compiled artifacts, answering a different question about the system.

All examples on this page use the **SIR epidemic model** from `gds-examples`.

## View 1: Structural

The compiled block graph from `SystemIR`. Shows composition topology -- sequential, parallel, feedback, temporal -- with role-based shapes and wiring types.

```python
from gds_viz import system_to_mermaid
mermaid = system_to_mermaid(system)
```

**Shape conventions:**

| Shape | Meaning | Role |
|-------|---------|------|
| Stadium `([...])` | Exogenous input (no forward_in) | BoundaryAction |
| Double-bracket `[[...]]` | State sink (no forward_out) | Terminal Mechanism |
| Rectangle `[...]` | Has both inputs and outputs | Policy / other |

**Arrow conventions:**

| Arrow | Meaning |
|-------|---------|
| Solid `-->` | Covariant forward flow |
| Thick `==>` | Contravariant feedback (within-timestep) |
| Dashed `-.->` | Temporal loop (cross-timestep) |

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Contact_Process([Contact Process]):::boundary
    Infection_Policy[Infection Policy]:::generic
    Update_Susceptible[[Update Susceptible]]:::mechanism
    Update_Infected[[Update Infected]]:::mechanism
    Update_Recovered[[Update Recovered]]:::mechanism
    Contact_Process --Contact Signal--> Infection_Policy
    Infection_Policy --Susceptible Delta--> Update_Susceptible
    Infection_Policy --Infected Delta--> Update_Infected
    Infection_Policy --Recovered Delta--> Update_Recovered
```

**Reading this diagram:** The Contact Process boundary action (stadium shape) feeds into the Infection Policy, which fans out to three terminal mechanisms (double-bracket shapes). Arrow labels show the port names used for auto-wiring.

### Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `system` | `SystemIR` | required | The compiled system to visualize |
| `show_hierarchy` | `bool` | `False` | If True, uses subgraphs for composition tree structure |
| `theme` | `MermaidTheme` | `None` | Mermaid theme (`"neutral"`, `"dark"`, etc.) |

---

## View 2: Canonical GDS

The mathematical decomposition: X_t --> U --> g --> f --> X_{t+1}. Derives from `CanonicalGDS` via `project_canonical()`.

```python
from gds.canonical import project_canonical
from gds_viz import canonical_to_mermaid

canonical = project_canonical(spec)
mermaid = canonical_to_mermaid(canonical)
```

Shows:

- **X_t / X_{t+1}** -- state variable nodes listing all entity variables
- **U** -- boundary subgraph (exogenous inputs)
- **g** -- policy subgraph (decision logic)
- **f** -- mechanism subgraph (state dynamics)
- **Theta** -- parameter space (hexagon) with dashed edges to g and f
- **Update edges** -- labeled dashed arrows from mechanisms to X_{t+1}

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart LR
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    X_t(["X_t<br/>Susceptible.count, Infected.count, Recovered.count"]):::state
    X_next(["X_{t+1}<br/>Susceptible.count, Infected.count, Recovered.count"]):::state
    Theta{{"Θ<br/>gamma, beta, contact_rate"}}:::param
    subgraph U ["Boundary (U)"]
        Contact_Process[Contact Process]:::boundary
    end
    subgraph g ["Policy (g)"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Update_Susceptible[Update Susceptible]:::mechanism
        Update_Infected[Update Infected]:::mechanism
        Update_Recovered[Update Recovered]:::mechanism
    end
    X_t --> U
    U --> g
    g --> f
    Update_Susceptible -.-> |Susceptible.count| X_next
    Update_Infected -.-> |Infected.count| X_next
    Update_Recovered -.-> |Recovered.count| X_next
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

**Reading this diagram:** Left-to-right flow from state X_t through boundary inputs (U), decision logic (g), and state dynamics (f) to the next state X_{t+1}. The Theta hexagon shows parameters feeding into g and f. Dashed arrows from mechanisms to X_{t+1} are labeled with the specific entity.variable they update.

### Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `canonical` | `CanonicalGDS` | required | The canonical projection to visualize |
| `show_updates` | `bool` | `True` | Label mechanism-to-X edges with entity.variable |
| `show_parameters` | `bool` | `True` | Show Theta node when parameters exist |
| `theme` | `MermaidTheme` | `None` | Mermaid theme |

---

## View 3: Architecture by Role

Blocks grouped by GDS role: Boundary (U), Policy (g), Mechanism (f). Entity cylinders show state variables and which mechanisms write to them.

```python
from gds_viz import spec_to_mermaid
mermaid = spec_to_mermaid(spec)
```

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    subgraph boundary ["Boundary (U)"]
        Contact_Process([Contact Process]):::boundary
    end
    subgraph policy ["Policy (g)"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Update_Susceptible[[Update Susceptible]]:::mechanism
        Update_Infected[[Update Infected]]:::mechanism
        Update_Recovered[[Update Recovered]]:::mechanism
    end
    entity_Susceptible[("Susceptible<br/>count: S")]:::entity
    entity_Infected[("Infected<br/>count: I")]:::entity
    entity_Recovered[("Recovered<br/>count: R")]:::entity
    Update_Susceptible -.-> entity_Susceptible
    Update_Infected -.-> entity_Infected
    Update_Recovered -.-> entity_Recovered
    Contact_Process --ContactSignalSpace--> Infection_Policy
    Infection_Policy --DeltaSpace--> Update_Infected
    Infection_Policy --DeltaSpace--> Update_Recovered
    Infection_Policy --DeltaSpace--> Update_Susceptible
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

**Reading this diagram:** Blocks are organized into role subgraphs. Wire labels show the Space used for communication (e.g., `ContactSignalSpace`, `DeltaSpace`). Entity cylinders at the bottom show which state variables exist and which mechanisms write to them.

---

## View 4: Architecture by Domain

Blocks grouped by a tag key instead of GDS role. Useful for showing organizational ownership -- which team or subsystem owns each block.

```python
from gds_viz import spec_to_mermaid
mermaid = spec_to_mermaid(spec, group_by="domain")
```

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    subgraph Observation ["Observation"]
        Contact_Process([Contact Process]):::boundary
    end
    subgraph Decision ["Decision"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph State_Update ["State Update"]
        Update_Susceptible[[Update Susceptible]]:::mechanism
        Update_Infected[[Update Infected]]:::mechanism
        Update_Recovered[[Update Recovered]]:::mechanism
    end
    entity_Susceptible[("Susceptible<br/>count: S")]:::entity
    entity_Infected[("Infected<br/>count: I")]:::entity
    entity_Recovered[("Recovered<br/>count: R")]:::entity
    Update_Susceptible -.-> entity_Susceptible
    Update_Infected -.-> entity_Infected
    Update_Recovered -.-> entity_Recovered
    Contact_Process --ContactSignalSpace--> Infection_Policy
    Infection_Policy --DeltaSpace--> Update_Infected
    Infection_Policy --DeltaSpace--> Update_Recovered
    Infection_Policy --DeltaSpace--> Update_Susceptible
```

**Reading this diagram:** Same blocks and wires as View 3, but grouped by the `"domain"` tag set on each block at definition time. The subgraph labels ("Observation", "Decision", "State Update") come from tag values, not GDS roles.

!!! tip "Setting domain tags"
    Tags are set when defining blocks:
    ```python
    sensor = BoundaryAction(
        name="Contact Process",
        ...,
        tags={"domain": "Observation"},
    )
    ```

---

## View 5: Parameter Influence

Shows the causal map from parameters (Theta) through blocks to entities. Answers: "if I change parameter X, which state variables are affected?"

```python
from gds_viz import params_to_mermaid
mermaid = params_to_mermaid(spec)
```

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart LR
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    param_beta{{"beta"}}:::param
    param_contact_rate{{"contact_rate"}}:::param
    param_gamma{{"gamma"}}:::param
    Contact_Process[Contact Process]
    Infection_Policy[Infection Policy]
    entity_Infected[("Infected<br/>I")]:::entity
    entity_Recovered[("Recovered<br/>R")]:::entity
    entity_Susceptible[("Susceptible<br/>S")]:::entity
    param_beta -.-> Infection_Policy
    param_contact_rate -.-> Contact_Process
    param_gamma -.-> Infection_Policy
    Update_Infected -.-> entity_Infected
    Update_Susceptible -.-> entity_Susceptible
    Update_Recovered -.-> entity_Recovered
    Contact_Process --> Infection_Policy
    Infection_Policy --> Update_Infected
    Infection_Policy --> Update_Recovered
    Infection_Policy --> Update_Susceptible
```

**Reading this diagram:** Parameter hexagons (orange) on the left feed into blocks via dashed arrows. Blocks flow through the dependency graph (solid arrows) to mechanisms, which update entity cylinders on the right. For example, `beta` feeds `Infection Policy`, which drives all three update mechanisms.

---

## View 6: Traceability

For a single entity variable, traces every block that can transitively affect it and every parameter feeding those blocks. Right-to-left layout.

```python
from gds_viz import trace_to_mermaid
mermaid = trace_to_mermaid(spec, "Susceptible", "count")
```

### Rendered Output

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart RL
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    target(["Susceptible.count (S)"]):::target
    Contact_Process[Contact Process]
    Infection_Policy[Infection Policy]
    Update_Susceptible[Update Susceptible]
    param_beta{{"beta"}}:::param
    param_contact_rate{{"contact_rate"}}:::param
    param_gamma{{"gamma"}}:::param
    Update_Susceptible ==> target
    Contact_Process --> Infection_Policy
    Infection_Policy --> Update_Susceptible
    param_contact_rate -.-> Contact_Process
    param_beta -.-> Infection_Policy
    param_gamma -.-> Infection_Policy
```

**Reading this diagram:** The red target node on the right is the variable being traced (`Susceptible.count`). Thick arrows (`==>`) show direct updates from mechanisms. Normal arrows show transitive dependencies. Dashed arrows show parameter influences. Reading right-to-left: `Susceptible.count` is directly updated by `Update Susceptible`, which depends on `Infection Policy`, which depends on `Contact Process` and parameters `beta`, `gamma`, and `contact_rate`.

### Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spec` | `GDSSpec` | required | The GDS specification |
| `entity` | `str` | required | Entity name (e.g., `"Susceptible"`) |
| `variable` | `str` | required | Variable name (e.g., `"count"`) |
| `theme` | `MermaidTheme` | `None` | Mermaid theme |

---

## View Summary

| # | View | Function | Input | Layout | Question |
|:-:|------|----------|-------|--------|----------|
| 1 | Structural | `system_to_mermaid()` | `SystemIR` | Top-down | What blocks exist and how are they wired? |
| 2 | Canonical | `canonical_to_mermaid()` | `CanonicalGDS` | Left-right | What is the formal h = f . g decomposition? |
| 3 | Architecture (role) | `spec_to_mermaid()` | `GDSSpec` | Top-down | How do blocks group by GDS role? |
| 4 | Architecture (domain) | `spec_to_mermaid(group_by=...)` | `GDSSpec` | Top-down | How do blocks group by domain/agent? |
| 5 | Parameter influence | `params_to_mermaid()` | `GDSSpec` | Left-right | What does each parameter control? |
| 6 | Traceability | `trace_to_mermaid()` | `GDSSpec` | Right-left | What can affect a specific state variable? |

## Cross-DSL Compatibility

All view functions operate on `GDSSpec` and `SystemIR`, which every compilation path produces. The same functions work unchanged regardless of whether the model was built with raw GDS blocks, stockflow DSL, control DSL, or games DSL.

```python
# All of these produce the same types -- gds-viz works with all of them:
from stockflow.dsl.compile import compile_model, compile_to_system
from gds_control.dsl.compile import compile_model, compile_to_system
from ogs.dsl.spec_bridge import compile_pattern_to_spec
```

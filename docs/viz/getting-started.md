# Getting Started

## Installation

```bash
pip install gds-viz
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add gds-viz
```

gds-viz imports as `gds_viz`:

```python
from gds_viz import system_to_mermaid, canonical_to_mermaid, spec_to_mermaid
```

## Requirements

- Python 3.12 or later
- [gds-framework](https://pypi.org/project/gds-framework/) >= 0.2.3 (installed automatically)

## How It Works

gds-viz takes GDS objects (`SystemIR`, `GDSSpec`, `CanonicalGDS`) and returns **Mermaid markdown strings**. It does not render images directly -- you paste the output into any Mermaid-compatible renderer.

```python
from gds_viz import system_to_mermaid

mermaid_str = system_to_mermaid(system)
print(mermaid_str)  # paste into GitHub markdown, mermaid.live, etc.
```

## Quick Start: SIR Epidemic Model

This example uses the SIR epidemic model from `gds-examples` to demonstrate all six views. The model has three entities (Susceptible, Infected, Recovered), one boundary action, one policy, and three mechanisms.

### Step 1: Build the Model

```python
from sir_epidemic.model import build_spec, build_system
from gds.canonical import project_canonical

spec = build_spec()
system = build_system()
canonical = project_canonical(spec)
```

### Step 2: Generate Views

```python
from gds_viz import (
    system_to_mermaid,
    canonical_to_mermaid,
    spec_to_mermaid,
    params_to_mermaid,
    trace_to_mermaid,
)

# View 1: Structural -- compiled block topology
print(system_to_mermaid(system))

# View 2: Canonical -- h = f . g decomposition
print(canonical_to_mermaid(canonical))

# View 3: Architecture by role -- blocks grouped by GDS role
print(spec_to_mermaid(spec))

# View 5: Parameter influence -- Theta -> blocks -> entities
print(params_to_mermaid(spec))

# View 6: Traceability -- what affects Susceptible.count?
print(trace_to_mermaid(spec, "Susceptible", "count"))
```

### Step 3: Render

Paste the Mermaid output into any compatible renderer:

- **GitHub / GitLab** -- native Mermaid support in markdown files
- **VS Code** -- with a Mermaid extension
- **Obsidian** -- built-in support
- **[mermaid.live](https://mermaid.live)** -- online editor
- **MkDocs** -- with `pymdownx.superfences` Mermaid fence (used by this documentation)
- **marimo** -- `mo.mermaid(mermaid_str)` for interactive notebooks

## Rendered Output

Here is the actual output from the SIR epidemic model, rendered inline.

### View 1: Structural

The compiled block graph from `SystemIR`. Shows composition topology with role-based shapes and wiring types.

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

### View 2: Canonical GDS

The mathematical decomposition: X_t --> U --> g --> f --> X_{t+1}. Shows the abstract dynamical system with state (X), input (U), policy (g), mechanism (f), and parameter space (Theta).

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

### View 3: Architecture by Role

Blocks grouped by GDS role. Entity cylinders show which state variables each mechanism writes.

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

## Where Visualization Fits

Visualization is a **post-compilation** concern. It operates on the same compiled artifacts that verification uses:

```
Define model → build_spec() / build_system()
                        ↓
              Compile → GDSSpec, SystemIR, CanonicalGDS
                        ↓
              ┌─────────┴──────────┐
              ↓                    ↓
        Verify (gds)        Visualize (gds-viz)
```

The six views are different projections of the same specification -- they never modify it, only read it. You can generate views at any point after compilation.

## Next Steps

- **[Views Guide](guide/views.md)** -- detailed gallery of all six view types with rendered output
- **[Theming Guide](guide/theming.md)** -- customizing diagram appearance with 5 built-in themes
- **[API Reference](api/init.md)** -- full function signatures and options
- **[Visualization Guide](../guides/visualization.md)** -- cross-DSL examples and interactive notebooks

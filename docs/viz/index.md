# gds-viz

[![PyPI](https://img.shields.io/pypi/v/gds-viz)](https://pypi.org/project/gds-viz/)
[![Python](https://img.shields.io/pypi/pyversions/gds-viz)](https://pypi.org/project/gds-viz/)
[![License](https://img.shields.io/github/license/BlockScience/gds-viz)](https://github.com/BlockScience/gds-viz/blob/main/LICENSE)

**Mermaid diagram renderers** for [gds-framework](https://blockscience.github.io/gds-framework) specifications.

## Six Views

gds-viz provides six views — each a different projection of the GDS specification `{h, X}`:

| View | Function | Input | Answers |
|---|---|---|---|
| 1. Structural | `system_to_mermaid()` | `SystemIR` | What blocks exist and how are they wired? |
| 2. Canonical GDS | `canonical_to_mermaid()` | `CanonicalGDS` | What is the formal decomposition h = f ∘ g? |
| 3. Architecture (role) | `spec_to_mermaid()` | `GDSSpec` | How do blocks group by GDS role? |
| 4. Architecture (domain) | `spec_to_mermaid(group_by=...)` | `GDSSpec` | How do blocks group by domain/agent? |
| 5. Parameter influence | `params_to_mermaid()` | `GDSSpec` | What does each parameter control? |
| 6. Traceability | `trace_to_mermaid()` | `GDSSpec` | What can affect a specific state variable? |

## Quick Start

```bash
uv add gds-viz
# or: pip install gds-viz
```

```python
from gds_viz import system_to_mermaid, canonical_to_mermaid, spec_to_mermaid

# View 1: Structural
mermaid = system_to_mermaid(system_ir)

# View 2: Canonical
from gds.canonical import project_canonical
mermaid = canonical_to_mermaid(project_canonical(spec))

# View 3: Architecture by role
mermaid = spec_to_mermaid(spec)
```

## Sample Output

Here is a canonical GDS diagram generated from the SIR epidemic model -- `canonical_to_mermaid(project_canonical(spec))`:

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

See all six views in the [Views Gallery](guide/views.md).

## What gds-viz Does NOT Cover

The six views exhaust what is **derivable from the GDS specification** `{h, X}`. Two views are deliberately excluded:

- **State Machine View** — requires discrete states and transition guards. GDS defines a continuous state space X, not a finite set of named states.
- **Simulation / Execution Order View** — requires operational semantics. GDS specifies structure, not runtime.

## Credits

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish)

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

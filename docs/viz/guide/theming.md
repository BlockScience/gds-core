# Theming

All gds-viz functions accept an optional `theme` parameter to control diagram appearance. The `MermaidTheme` type restricts values to Mermaid's five built-in themes.

## Usage

```python
from gds_viz import system_to_mermaid, MermaidTheme

# Pass any theme name
mermaid = system_to_mermaid(system, theme="dark")

# Type-safe with MermaidTheme literal
theme: MermaidTheme = "forest"
mermaid = system_to_mermaid(system, theme=theme)
```

All view functions support theming:

```python
from gds_viz import (
    system_to_mermaid,
    canonical_to_mermaid,
    spec_to_mermaid,
    block_to_mermaid,
    params_to_mermaid,
    trace_to_mermaid,
)

system_to_mermaid(system, theme="neutral")
canonical_to_mermaid(canonical, theme="dark")
spec_to_mermaid(spec, theme="forest")
block_to_mermaid(block, theme="neutral")
params_to_mermaid(spec, theme="base")
trace_to_mermaid(spec, "Entity", "var", theme="default")
```

## Available Themes

| Theme | Best For | Canvas |
|-------|----------|--------|
| `neutral` | Light backgrounds (GitHub, docs) | Muted gray -- **default** |
| `default` | Mermaid's built-in Material style | Blue-toned |
| `dark` | Dark-mode renderers | Dark canvas, light text |
| `forest` | Nature-inspired presentations | Green-tinted |
| `base` | Minimal chrome, very light fills | Near-white |

## Theme Comparison

The same SIR epidemic structural diagram rendered with different themes.

### Neutral (default)

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

### Dark

```mermaid
%%{init:{"theme":"dark"}}%%
flowchart TD
    classDef boundary fill:#1e40af,stroke:#60a5fa,stroke-width:2px,color:#dbeafe
    classDef policy fill:#92400e,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    classDef mechanism fill:#166534,stroke:#4ade80,stroke-width:2px,color:#dcfce7
    classDef control fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    classDef generic fill:#334155,stroke:#94a3b8,stroke-width:1px,color:#e2e8f0
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

### Forest

```mermaid
%%{init:{"theme":"forest"}}%%
flowchart TD
    classDef boundary fill:#a7f3d0,stroke:#059669,stroke-width:2px,color:#064e3b
    classDef policy fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#15803d,stroke-width:2px,color:#14532d
    classDef control fill:#d9f99d,stroke:#65a30d,stroke-width:2px,color:#365314
    classDef generic fill:#d1d5db,stroke:#6b7280,stroke-width:1px,color:#1f2937
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

## Color Scheme

gds-viz uses a consistent color scheme across all views. Each role and element type has a dedicated palette that adapts to the selected theme.

### Neutral Theme Palette

| Element | Fill | Stroke | CSS Class |
|---------|------|--------|-----------|
| BoundaryAction | `#93c5fd` (light blue) | `#2563eb` | `boundary` |
| Policy | `#fcd34d` (yellow) | `#d97706` | `policy` |
| Mechanism | `#86efac` (green) | `#16a34a` | `mechanism` |
| ControlAction | `#d8b4fe` (purple) | `#9333ea` | `control` |
| Generic | `#cbd5e1` (gray) | `#64748b` | `generic` |
| Entity | `#e2e8f0` (light gray) | `#475569` | `entity` |
| Parameter | `#fdba74` (orange) | `#ea580c` | `param` |
| State (X_t) | `#5eead4` (teal) | `#0d9488` | `state` |
| Target | `#fca5a5` (red) | `#dc2626` | `target` |

## Rendering Targets

Output is standard Mermaid markdown. It renders in:

- **GitHub / GitLab** -- native Mermaid support in markdown files and issues
- **VS Code** -- with a Mermaid extension
- **Obsidian** -- built-in support
- **[mermaid.live](https://mermaid.live)** -- online editor and playground
- **MkDocs** -- with `pymdownx.superfences` Mermaid fence (used by this documentation)
- **marimo** -- `mo.mermaid(mermaid_str)` for interactive notebooks

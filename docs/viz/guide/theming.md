# Theming

## Mermaid Theme

All diagrams use the `neutral` Mermaid theme via the init directive:

```
%%{init:{"theme":"neutral"}}%%
```

## Color Scheme

gds-viz uses a consistent color scheme across all views:

| Role | Fill | Stroke | CSS Class |
|---|---|---|---|
| BoundaryAction | `#93c5fd` (light blue) | `#2563eb` | `boundary` |
| Policy | `#fcd34d` (yellow) | `#d97706` | `policy` |
| Mechanism | `#86efac` (green) | `#16a34a` | `mechanism` |
| ControlAction | `#d8b4fe` (purple) | `#9333ea` | `control` |
| Generic | `#cbd5e1` (gray) | `#64748b` | `generic` |
| Entity | `#e2e8f0` (light gray) | `#475569` | `entity` |
| Parameter | `#fdba74` (orange) | `#ea580c` | `param` |
| State | `#5eead4` (teal) | `#0d9488` | `state` |

## Rendering

Output is standard Mermaid markdown. It renders in:

- GitHub / GitLab (native support)
- VS Code (with Mermaid extension)
- Obsidian
- [mermaid.live](https://mermaid.live) (online editor)
- MkDocs (with pymdownx.superfences mermaid fence)

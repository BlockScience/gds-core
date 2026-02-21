# Visualization

gds-games includes 6 Mermaid diagram generators in `ogs.viz`.

## Generating Diagrams

```python
from ogs import compile_to_ir
from ogs.viz import generate_all_views

ir = compile_to_ir(pattern)
views = generate_all_views(ir.patterns[0])

for name, mermaid in views.items():
    print(f"## {name}\n```mermaid\n{mermaid}\n```\n")
```

## Available Views

| View | Function | Description |
|---|---|---|
| Structural | `structural_to_mermaid()` | Full game topology with all flows |
| Architecture by Role | `architecture_by_role_to_mermaid()` | Games grouped by GameType |
| Architecture by Domain | `architecture_by_domain_to_mermaid()` | Games grouped by domain tag |
| Hierarchy | `hierarchy_to_mermaid()` | Composition tree nesting |
| Flow Topology | `flow_topology_to_mermaid()` | Covariant flows only |
| Terminal Conditions | `terminal_conditions_to_mermaid()` | State transition diagram |

## Individual Views

```python
from ogs.viz import structural_to_mermaid, hierarchy_to_mermaid

structural = structural_to_mermaid(pattern_ir)
hierarchy = hierarchy_to_mermaid(pattern_ir)
```

All functions take `PatternIR` and return a Mermaid markdown string.

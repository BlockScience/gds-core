# GDS Ecosystem

The GDS ecosystem is a family of composable packages for specifying, visualizing, and analyzing complex systems.

## Packages

| Package | Description | Docs | PyPI |
|---|---|---|---|
| **gds-framework** | Foundation — typed compositional specifications | [Docs](https://blockscience.github.io/gds-framework) | [PyPI](https://pypi.org/project/gds-framework/) |
| **gds-viz** | Mermaid diagram renderers for GDS specifications | [Docs](https://blockscience.github.io/gds-viz) | [PyPI](https://pypi.org/project/gds-viz/) |
| **gds-games** | Typed DSL for compositional game theory | [Docs](https://blockscience.github.io/gds-games) | [PyPI](https://pypi.org/project/gds-games/) |
| **gds-examples** | Six tutorial models demonstrating every framework feature | [Docs](https://blockscience.github.io/gds-examples) | [PyPI](https://pypi.org/project/gds-examples/) |

## Dependency Graph

```mermaid
graph TD
    F[gds-framework] --> V[gds-viz]
    F --> G[gds-games]
    F --> E[gds-examples]
    V --> E
```

## Links

- [GitHub Organization](https://github.com/BlockScience)
- [GDS Theory Paper](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) (Zargham & Shorish, 2022)
- [cadCAD Ecosystem](https://github.com/cadCAD-org/cadCAD)
- [BlockScience](https://block.science/)

# gds-core

[![License](https://img.shields.io/github/license/BlockScience/gds-core)](LICENSE)
[![CI](https://github.com/BlockScience/gds-core/actions/workflows/ci.yml/badge.svg)](https://github.com/BlockScience/gds-core/actions/workflows/ci.yml)

Monorepo for the **Generalized Dynamical Systems** ecosystem — typed compositional specifications for complex systems, grounded in [GDS theory](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) (Zargham & Shorish, 2022).

## Packages

| Package | PyPI | Description |
|---------|------|-------------|
| [gds-framework](packages/gds-framework/) | [![PyPI](https://img.shields.io/pypi/v/gds-framework)](https://pypi.org/project/gds-framework/) | Core engine — blocks, composition algebra, compiler, verification |
| [gds-viz](packages/gds-viz/) | [![PyPI](https://img.shields.io/pypi/v/gds-viz)](https://pypi.org/project/gds-viz/) | Mermaid diagram renderers for GDS specifications |
| [gds-games](packages/gds-games/) | [![PyPI](https://img.shields.io/pypi/v/gds-games)](https://pypi.org/project/gds-games/) | Typed DSL for compositional game theory (Open Games) |
| [gds-examples](packages/gds-examples/) | [![PyPI](https://img.shields.io/pypi/v/gds-examples)](https://pypi.org/project/gds-examples/) | Six tutorial models demonstrating every framework feature |

## Quick Start

```bash
# Clone and install all packages (editable, workspace-linked)
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages

# Run tests for a specific package
uv run --package gds-framework pytest packages/gds-framework/tests -v

# Run all tests
uv run --package gds-framework pytest packages/gds-framework/tests packages/gds-viz/tests packages/gds-games/tests packages/gds-examples -v

# Lint & format
uv run ruff check packages/
uv run ruff format --check packages/
```

## Development

This is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) monorepo. All four packages are developed together with shared tooling:

- **Linting/formatting**: Ruff (configured at root, line-length 88)
- **Testing**: pytest per-package
- **Docs**: Unified MkDocs Material site
- **CI**: GitHub Actions matrix across all packages
- **Publishing**: Tag-based per-package PyPI publishing (`gds-framework/v0.3.1`)

## Documentation

Full documentation at [blockscience.github.io/gds-core](https://blockscience.github.io/gds-core).

## Citation

If you use GDS in your research, please cite:

> M. Zargham & J. Shorish, "Generalized Dynamical Systems," 2022. DOI: [10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc)

See [CITATION.cff](CITATION.cff) for BibTeX and other formats.

## Credits & Attribution

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/BlockScience/MSML) and [bdp-lib](https://github.com/BlockScience/bdp-lib).

**Contributors:**
* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (BlockScience).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (BlockScience).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

## License

Apache-2.0 — see [LICENSE](LICENSE).

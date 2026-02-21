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

## License

Apache-2.0 — see [LICENSE](LICENSE).

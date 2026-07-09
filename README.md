# gds-core

[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](LICENSE)
[![CI](https://github.com/DynamicalSystemsGroup/gds-core/actions/workflows/ci.yml/badge.svg)](https://github.com/DynamicalSystemsGroup/gds-core/actions/workflows/ci.yml)

Monorepo for the **Generalized Dynamical Systems** ecosystem — typed compositional specifications for complex systems, grounded in [GDS theory](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) (Zargham & Shorish, 2022).

## Packages

| Package | PyPI | Description |
|---------|------|-------------|
| [gds-framework](packages/gds-framework/) | [![PyPI](https://img.shields.io/pypi/v/gds-framework)](https://pypi.org/project/gds-framework/) | Core engine — blocks, composition algebra, compiler, verification |
| [gds-viz](packages/gds-viz/) | [![PyPI](https://img.shields.io/pypi/v/gds-viz)](https://pypi.org/project/gds-viz/) | Mermaid diagram renderers for GDS specifications |
| [gds-interchange](packages/gds-interchange/) | [![PyPI](https://img.shields.io/pypi/v/gds-interchange)](https://pypi.org/project/gds-interchange/) | OWL/SHACL/SPARQL export and RDF round-trip tooling |
| [gds-owl](packages/gds-owl/) | [![PyPI](https://img.shields.io/pypi/v/gds-owl)](https://pypi.org/project/gds-owl/) | Compatibility distribution for `gds_interchange.owl` |
| [gds-proof](packages/gds-proof/) | [![PyPI](https://img.shields.io/pypi/v/gds-proof)](https://pypi.org/project/gds-proof/) | Symbolic invariant analysis and proof verification |
| [gds-domains](packages/gds-domains/) | [![PyPI](https://img.shields.io/pypi/v/gds-domains)](https://pypi.org/project/gds-domains/) | Shared namespace for domain DSL packages |
| [gds-games](packages/gds-games/) | [![PyPI](https://img.shields.io/pypi/v/gds-games)](https://pypi.org/project/gds-games/) | Typed DSL for compositional game theory (Open Games) |
| [gds-stockflow](packages/gds-stockflow/) | [![PyPI](https://img.shields.io/pypi/v/gds-stockflow)](https://pypi.org/project/gds-stockflow/) | Declarative stock-flow DSL over GDS semantics |
| [gds-control](packages/gds-control/) | [![PyPI](https://img.shields.io/pypi/v/gds-control)](https://pypi.org/project/gds-control/) | State-space control DSL over GDS semantics |
| [gds-software](packages/gds-software/) | [![PyPI](https://img.shields.io/pypi/v/gds-software)](https://pypi.org/project/gds-software/) | Software architecture DSL (DFD, SM, C4, ERD, Dependency) |
| [gds-business](packages/gds-business/) | [![PyPI](https://img.shields.io/pypi/v/gds-business)](https://pypi.org/project/gds-business/) | Business dynamics DSL (CLD, supply chain, value stream map) |
| [gds-symbolic](packages/gds-symbolic/) | [![PyPI](https://img.shields.io/pypi/v/gds-symbolic)](https://pypi.org/project/gds-symbolic/) | SymPy bridge for control models |
| [gds-sim](packages/gds-sim/) | [![PyPI](https://img.shields.io/pypi/v/gds-sim)](https://pypi.org/project/gds-sim/) | Standalone discrete-time simulation engine for GDS models |
| [gds-continuous](packages/gds-continuous/) | [![PyPI](https://img.shields.io/pypi/v/gds-continuous)](https://pypi.org/project/gds-continuous/) | Continuous-time ODE integration runtime |
| [gds-analysis](packages/gds-analysis/) | [![PyPI](https://img.shields.io/pypi/v/gds-analysis)](https://pypi.org/project/gds-analysis/) | GDSSpec-to-simulation bridge, reachability, and `gds_analysis.psuu` parameter search |
| [gds-psuu](packages/gds-psuu/) | [![PyPI](https://img.shields.io/pypi/v/gds-psuu)](https://pypi.org/project/gds-psuu/) | Deprecated compatibility package re-exporting `gds_analysis.psuu` |
| [gds-examples](packages/gds-examples/) | [![PyPI](https://img.shields.io/pypi/v/gds-examples)](https://pypi.org/project/gds-examples/) | Tutorial models demonstrating framework features |

## Quick Start

```bash
# Clone and install all packages (editable, workspace-linked)
git clone https://github.com/DynamicalSystemsGroup/gds-core.git
cd gds-core
uv sync --all-packages

# Run tests for a specific package
uv run --package gds-framework pytest packages/gds-framework/tests -v

# Run all tests
uv run --package gds-framework pytest packages/gds-framework/tests packages/gds-viz/tests packages/gds-interchange/tests packages/gds-owl/tests packages/gds-proof/tests packages/gds-domains/tests packages/gds-games/tests packages/gds-stockflow/tests packages/gds-control/tests packages/gds-software/tests packages/gds-business/tests packages/gds-symbolic/tests packages/gds-sim/tests packages/gds-continuous/tests packages/gds-analysis/tests packages/gds-psuu/tests packages/gds-examples/tests -v

# Lint & format
uv run ruff check packages/
uv run ruff format --check packages/
```

## Development

This is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) monorepo. All packages are developed together with shared tooling:

- **Linting/formatting**: Ruff (configured at root, line-length 88)
- **Testing**: pytest per-package
- **Docs**: Unified MkDocs Material site
- **CI**: GitHub Actions matrix across all packages
- **Publishing**: Tag-based per-package PyPI publishing (`gds-framework/v0.3.1`)

## Documentation

Full documentation at [dynamicalsystemsgroup.github.io/gds-core](https://dynamicalsystemsgroup.github.io/gds-core).

## Citation

If you use GDS in your research, please cite:

> M. Zargham & J. Shorish, "Generalized Dynamical Systems," 2022. DOI: [10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc)

See [CITATION.cff](CITATION.cff) for BibTeX and other formats.

## Credits & Attribution

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [Dynamical Systems Group](https://www.dynamicalsystemsgroup.com/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.dynamicalsystemsgroup.com/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/DynamicalSystemsGroup/MSML) and [bdp-lib](https://github.com/DynamicalSystemsGroup/bdp-lib).

**Contributors:**
* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (Dynamical Systems Group).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (Dynamical Systems Group).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

## License

Apache-2.0 — see [LICENSE](LICENSE).

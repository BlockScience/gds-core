# GDS Framework Examples

[![PyPI](https://img.shields.io/pypi/v/gds-examples)](https://pypi.org/project/gds-examples/)
[![Python](https://img.shields.io/pypi/pyversions/gds-examples)](https://pypi.org/project/gds-examples/)
[![License](https://img.shields.io/github/license/BlockScience/gds-examples)](https://github.com/BlockScience/gds-examples/blob/main/LICENSE)

**Six complete domain models** demonstrating every [gds-framework](https://blockscience.github.io/gds-framework) feature. Each `model.py` is written as a tutorial chapter with inline GDS theory commentary — read them in order.

## Quick Start

```bash
# Run all example tests (168 tests)
uv run pytest examples/ -v

# Run a specific example
uv run pytest examples/sir_epidemic/ -v

# Generate all 6 views for one example
uv run python examples/sir_epidemic/generate_views.py --save
```

## Learning Path

| # | Example | New Concept | Composition |
|:-:|---------|-------------|-------------|
| 1 | [SIR Epidemic](examples/sir-epidemic.md) | Fundamentals — TypeDef, Entity, Space, blocks | `>>` `\|` |
| 2 | [Thermostat PID](examples/thermostat.md) | `.feedback()`, CONTRAVARIANT backward flow | `>>` `.feedback()` |
| 3 | [Lotka-Volterra](examples/lotka-volterra.md) | `.loop()`, COVARIANT temporal iteration | `>>` `\|` `.loop()` |
| 4 | [Prisoner's Dilemma](examples/prisoners-dilemma.md) | Nested `\|`, multi-entity X, complex trees | `\|` `>>` `.loop()` |
| 5 | [Insurance Contract](examples/insurance.md) | ControlAction role, complete 4-role taxonomy | `>>` |
| 6 | [Crosswalk Problem](examples/crosswalk.md) | Mechanism design, discrete Markov transitions | `>>` |

Start with SIR Epidemic and work down — each introduces one new concept.

## File Structure

Each example follows the same layout:

```
examples/sir_epidemic/
├── __init__.py          # empty
├── model.py             # types, entities, spaces, blocks, build_spec(), build_system()
├── test_model.py        # comprehensive tests for every layer
├── generate_views.py    # generates all 6 visualization views with commentary
└── VIEWS.md             # generated output — 6 Mermaid diagrams with explanations
```

## Credits

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish)

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

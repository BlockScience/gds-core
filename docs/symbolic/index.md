# gds-symbolic

[![PyPI](https://img.shields.io/pypi/v/gds-symbolic)](https://pypi.org/project/gds-symbolic/)
[![Python](https://img.shields.io/pypi/pyversions/gds-symbolic)](https://pypi.org/project/gds-symbolic/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**SymPy bridge for gds-control** -- symbolic state equations, automatic linearization, and ODE code generation.

## What is this?

`gds-symbolic` extends `gds-control`'s `ControlModel` with symbolic mathematics. Instead of writing numerical right-hand side functions by hand, you declare state and output equations as symbolic expressions and let the compiler do the rest.

- **`StateEquation`** -- symbolic expression for `dx/dt` (e.g., `"-k * x + b * u"`)
- **`OutputEquation`** -- symbolic expression for sensor output `y` (e.g., `"x + noise"`)
- **`compile_to_ode()`** -- lambdifies symbolic equations into a callable `ODEFunction` compatible with `gds-continuous`
- **`linearize()`** -- computes Jacobian matrices (A, B, C, D) at an operating point
- **Safe expression parsing** -- uses `sympy.parsing.sympy_parser.parse_expr`, never `eval`

## Architecture

```
gds-control (pip install gds-control)
|
|  State-space control DSL: State, Input, Sensor, Controller.
|
+-- gds-symbolic (uv add gds-symbolic[sympy])
    |
    |  Symbolic layer: StateEquation, OutputEquation,
    |  compile_to_ode(), linearize().
    |
    +-- gds-continuous (optional integration)
        |
        |  ODE simulation engine: ODEModel, ODESimulation.
```

## Key Types

| Type | Purpose |
|------|---------|
| `StateEquation` | Symbolic `dx_i/dt = expr(x, u, params)` |
| `OutputEquation` | Symbolic `y_i = expr(x, u, params)` |
| `SymbolicControlModel` | Extends `ControlModel` with symbolic equations |
| `ODEFunction` | Lambdified callable: `f(t, x, params) -> dx/dt` |
| `LinearSystem` | Matrices `(A, B, C, D)` from Jacobian linearization |

## How It Works

```
Symbolic expressions (strings)
    |
    v
parse_expr()  -->  SymPy Expr objects
    |
    v
compile_to_ode()  -->  ODEFunction (lambdified, numpy-backed)
    |                       |
    v                       v
linearize()           gds-continuous ODEModel
    |
    v
LinearSystem(A, B, C, D)   -->  eigenvalue analysis, controllability, etc.
```

All expression parsing uses `sympy.parsing.sympy_parser.parse_expr` with a restricted transformation set -- arbitrary code execution is not possible.

## Quick Start

```bash
uv add "gds-symbolic[sympy]"
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on [gds-control](../control/index.md) by [BlockScience](https://block.science).

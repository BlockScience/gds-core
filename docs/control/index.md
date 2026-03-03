# gds-control

[![PyPI](https://img.shields.io/pypi/v/gds-control)](https://pypi.org/project/gds-control/)
[![Python](https://img.shields.io/pypi/pyversions/gds-control)](https://pypi.org/project/gds-control/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**State-space control DSL over GDS semantics** -- control theory with formal verification.

## What is this?

`gds-control` extends the GDS framework with control systems vocabulary -- states, inputs, sensors, and controllers. It provides:

- **4 element types** -- State, Input, Sensor, Controller
- **Typed compilation** -- Each element compiles to GDS role blocks, entities, and composition trees
- **6 verification checks** -- Domain-specific structural validation (CS-001..CS-006)
- **Canonical decomposition** -- Validated h = f &#x2218; g projection mapping directly to state-space representation
- **Full GDS integration** -- All downstream tooling works immediately (canonical projection, semantic checks, gds-viz)

## Architecture

```
gds-framework (pip install gds-framework)
|
|  Domain-neutral composition algebra, typed spaces,
|  state model, verification engine, flat IR compiler.
|
+-- gds-control (pip install gds-control)
    |
    |  Control DSL: State, Input, Sensor, Controller elements,
    |  compile_model(), domain verification, verify() dispatch.
    |
    +-- Your application
        |
        |  Concrete control models, analysis notebooks,
        |  verification runners.
```

## GDS Mapping

The DSL maps directly to the standard state-space representation:

```
x' = Ax + Bu    (state dynamics -> Mechanism)
y  = Cx + Du    (sensor output  -> Policy)
u  = K(y, r)    (control law    -> Policy)
r               (reference      -> BoundaryAction)
```

```
Your declaration                    What the compiler produces
----------------                    -------------------------
State("temperature")         ->     Mechanism + Entity (state update f + state X)
Input("setpoint")            ->     BoundaryAction (exogenous input U)
Sensor("thermometer")        ->     Policy (observation g)
Controller("PID")            ->     Policy (decision logic g)
ControlModel(...)            ->     GDSSpec + SystemIR (full GDS specification)
```

## Composition Tree

The compiler builds a tiered composition tree:

```
(inputs | sensors) >> (controllers) >> (state dynamics)
    .loop([state dynamics forward_out -> sensor forward_in])
```

- **Within each tier:** parallel composition (`|`) -- independent inputs and sensors run side-by-side
- **Across tiers:** sequential composition (`>>`) -- sensors feed controllers, controllers feed state dynamics
- **Temporal recurrence:** `.loop()` -- state outputs at timestep *t* feed back to sensors at timestep *t+1*

**Design decision:** All non-state-updating blocks use `Policy`. `ControlAction` is deliberately not used -- it sits outside the canonical *g* partition, which would break the clean `(A, B, C, D) <-> (X, U, g, f)` mapping.

## Canonical Form

Control models produce the full dynamical form:

| |X| | |f| | Form | Character |
|-----|-----|------|-----------|
| n | n | h = f &#x2218; g | Full dynamical system |

States carry state (X), dynamics blocks provide f, and sensors + controllers contribute to g.

## Quick Start

```bash
uv add gds-control
# or: pip install gds-control
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on [gds-framework](../framework/index.md) by [BlockScience](https://block.science).

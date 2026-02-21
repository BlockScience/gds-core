# gds-framework

[![PyPI](https://img.shields.io/pypi/v/gds-framework)](https://pypi.org/project/gds-framework/)
[![Python](https://img.shields.io/pypi/pyversions/gds-framework)](https://pypi.org/project/gds-framework/)
[![License](https://img.shields.io/github/license/BlockScience/gds-framework)](https://github.com/BlockScience/gds-framework/blob/main/LICENSE)
[![CI](https://github.com/BlockScience/gds-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/BlockScience/gds-framework/actions/workflows/ci.yml)

**Typed compositional specifications for complex systems**, grounded in [Generalized Dynamical Systems](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) theory (Zargham & Shorish, 2022).

## What is this?

`gds-framework` is a **foundation layer** for specifying dynamical systems as compositions of typed blocks. It provides the domain-neutral primitives — you bring the domain knowledge.

```
gds-framework                          Your domain package
─────────────────                       ──────────────────
Block, Interface, Port                  PredatorBlock, PreyBlock
>> | .feedback() .loop()                predator >> prey >> environment
TypeDef, Space, Entity                  Population(int, ≥0), EcosystemState
GDSSpec, verify()                       check_conservation(), check_stability()
compile_system() → SystemIR             visualize(), simulate()
```

A [Generalized Dynamical System](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) is a pair **{h, X}** where **X** is a state space and **h: X → X** is a state transition map. The GDS canonical form decomposes **h** into a pipeline of typed blocks — observations, decisions, and state updates — that compose via wiring:

| GDS concept | Paper notation | gds-framework |
|---|---|---|
| State Space | X | `Entity` with `StateVariable`s |
| Exogenous observation | g(·) | `BoundaryAction` |
| Decision / policy | g: X → U_x | `Policy` |
| State update | f: X × U_x → X | `Mechanism` |
| Admissible input constraint | U: X → ℘(U) | `ControlAction` |
| Transition map | h = f\|_x ∘ g | Composed wiring (`>>`) |
| Trajectory | x₀, x₁, ... | Temporal loop (`.loop()`) |

## Quick Start

```bash
pip install gds-framework
```

```python
from gds import (
    BoundaryAction, Policy, ControlAction,
    interface, Wiring,
    compile_system, verify,
)
from gds.ir.models import FlowDirection

# Define blocks with GDS roles and typed interfaces
sensor = BoundaryAction(
    name="Temperature Sensor",
    interface=interface(forward_out=["Temperature"]),
)
controller = Policy(
    name="PID Controller",
    interface=interface(
        forward_in=["Temperature", "Setpoint"],
        forward_out=["Heater Command"],
        backward_in=["Energy Cost"],
    ),
)
plant = ControlAction(
    name="Room",
    interface=interface(
        forward_in=["Heater Command"],
        forward_out=["Temperature"],
        backward_out=["Energy Cost"],
    ),
)

# Compose with operators — types checked at construction time
system = (sensor >> controller >> plant).feedback([
    Wiring(
        source_block="Room", source_port="Energy Cost",
        target_block="PID Controller", target_port="Energy Cost",
        direction=FlowDirection.CONTRAVARIANT,
    )
])

# Compile to flat IR and verify
ir = compile_system("Thermostat", system)
report = verify(ir)
print(f"{len(ir.blocks)} blocks, {len(ir.wirings)} wirings")
# 3 blocks, 3 wirings
print(f"{report.checks_passed}/{report.checks_total} checks passed")
# 13/14 checks passed (G-002 flags BoundaryAction for having no inputs — expected)
```

## What's Included

**Layer 1 — Composition Algebra:**
Blocks with bidirectional typed interfaces, composed via four operators (`>>`, `|`, `.feedback()`, `.loop()`). A 3-stage compiler flattens composition trees into flat IR. Six generic verification checks validate structural properties.

**Layer 2 — Specification Layer:**
`TypeDef` with runtime constraints, typed `Space`s, `Entity` with `StateVariable`s, block roles (`BoundaryAction`, `Policy`, `Mechanism`, `ControlAction`), `GDSSpec` registry, `ParameterSchema` for configuration space Θ, `CanonicalGDS` projection deriving the formal h = f ∘ g decomposition, `Tagged` mixin for inert semantic annotations, semantic verification (completeness, determinism, reachability, type safety, parameter references, canonical wellformedness), `SpecQuery` for dependency analysis, and JSON serialization.

## Status

**v0.2.0 — Alpha.** Both layers are implemented and tested (347 tests, 99% coverage). The composition algebra and specification layer are stable. Domain packages and simulation execution are not yet built — `gds-framework` is the foundation they will build on.

## Credits

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/BlockScience/MSML) and [bdp-lib](https://github.com/BlockScience/bdp-lib).

**Contributors:**

* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (BlockScience).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (BlockScience).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.

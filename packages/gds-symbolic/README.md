# gds-symbolic

Symbolic math bridge for the GDS ecosystem — compiles SymPy expressions
into plain Python callables for use with `gds-continuous`.

## Installation

```bash
uv add gds-symbolic[sympy]
```

## Quick Start

```python
from gds_control.dsl.elements import State, Input, Sensor, Controller
from gds_symbolic import SymbolicControlModel, StateEquation

model = SymbolicControlModel(
    name="damped_oscillator",
    states=[State(name="x"), State(name="v")],
    inputs=[Input(name="force")],
    sensors=[Sensor(name="position", observes=["x"])],
    controllers=[Controller(name="actuator", reads=["position", "force"], drives=["x", "v"])],
    state_equations=[
        StateEquation(state_name="x", expr_str="v"),
        StateEquation(state_name="v", expr_str="-k*x - c*v + force"),
    ],
    symbolic_params=["k", "c"],
)

# Compile to plain callable (no SymPy at runtime)
ode_fn, state_order = model.to_ode_function()

# Linearize at origin
lin = model.linearize(x0=[0.0, 0.0], u0=[0.0])
print(lin.A)  # [[0, 1], [-k, -c]] evaluated at operating point
```

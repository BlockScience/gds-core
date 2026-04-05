# Getting Started

## Installation

```bash
uv add "gds-symbolic[sympy]"
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Symbolic Model

Define a damped harmonic oscillator symbolically: two state variables (position and velocity), one input (external force).

```python
from gds_domains.symbolic import (
    SymbolicControlModel,
    StateEquation,
    OutputEquation,
    compile_to_ode,
)

# 1. Declare symbolic state equations
#    dx1/dt = x2           (velocity)
#    dx2/dt = -k*x1 - c*x2 + u   (acceleration with damping)
model = SymbolicControlModel(
    name="DampedOscillator",
    state_equations=[
        StateEquation(state="x1", expr="x2"),
        StateEquation(state="x2", expr="-k * x1 - c * x2 + u"),
    ],
    output_equations=[
        OutputEquation(output="position", expr="x1"),
    ],
    parameters={"k": 4.0, "c": 0.5},
)

# 2. Compile to a callable ODE function
ode_fn = compile_to_ode(model)

# 3. Evaluate at a point
dx = ode_fn(t=0.0, state={"x1": 1.0, "x2": 0.0}, params={"k": 4.0, "c": 0.5, "u": 0.0})
print(dx)  # {"x1": 0.0, "x2": -4.0}
```

## Integration with gds-continuous

Plug the compiled ODE function directly into `gds-continuous`:

```python
from gds_continuous import ODEModel, ODESimulation

ode_model = ODEModel(
    state_names=["x1", "x2"],
    initial_state={"x1": 1.0, "x2": 0.0},
    rhs=ode_fn,
    params={"k": 4.0, "c": 0.5, "u": 0.0},
)

sim = ODESimulation(model=ode_model, t_span=(0.0, 20.0), solver="RK45")
results = sim.run()

import matplotlib.pyplot as plt
plt.plot(results.t, results["x1"], label="position")
plt.plot(results.t, results["x2"], label="velocity")
plt.legend()
plt.title("Damped Harmonic Oscillator")
plt.xlabel("Time")
plt.grid(True)
plt.show()
```

## Linearization

Compute Jacobian matrices at an operating point to get the standard state-space form `(A, B, C, D)`:

```python
from gds_domains.symbolic import linearize

# Linearize around the equilibrium (x1=0, x2=0, u=0)
lin = linearize(
    model,
    operating_point={"x1": 0.0, "x2": 0.0},
    input_point={"u": 0.0},
)

print("A =", lin.A)  # [[ 0.  1.], [-4. -0.5]]
print("B =", lin.B)  # [[0.], [1.]]
print("C =", lin.C)  # [[1. 0.]]
print("D =", lin.D)  # [[0.]]
```

The `LinearSystem` object holds NumPy arrays for each matrix:

```python
import numpy as np

# Check eigenvalues for stability
eigenvalues = np.linalg.eigvals(lin.A)
print(f"Eigenvalues: {eigenvalues}")
print(f"Stable: {all(e.real < 0 for e in eigenvalues)}")
```

## Nonlinear Example: Van der Pol Oscillator

A classic nonlinear system where linearization reveals local stability:

```python
from gds_domains.symbolic import SymbolicControlModel, StateEquation, linearize

vdp = SymbolicControlModel(
    name="VanDerPol",
    state_equations=[
        StateEquation(state="x1", expr="x2"),
        StateEquation(state="x2", expr="mu * (1 - x1**2) * x2 - x1"),
    ],
    parameters={"mu": 1.0},
)

# Linearize at the origin
lin = linearize(vdp, operating_point={"x1": 0.0, "x2": 0.0})
print("A =", lin.A)  # [[0, 1], [-1, mu]]  -- unstable for mu > 0
```

## Next Steps

- [Symbolic Overview](index.md) -- architecture and key types
- [Continuous-Time](../continuous/index.md) -- ODE simulation engine for running compiled models
- [Control](../control/index.md) -- the underlying control DSL

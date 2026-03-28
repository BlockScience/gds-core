# gds-continuous

Continuous-time ODE integration engine for the GDS ecosystem.

## Installation

```bash
uv add gds-continuous[scipy]
```

## Quick Start

```python
from gds_continuous import ODEModel, ODESimulation

# Define an ODE: dx/dt = -x
model = ODEModel(
    state_names=["x"],
    initial_state={"x": 1.0},
    rhs=lambda t, y, p: [-y[0]],
)

# Integrate
sim = ODESimulation(model=model, t_span=(0.0, 5.0))
results = sim.run()
```

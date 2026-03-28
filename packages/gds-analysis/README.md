# gds-analysis

Dynamical analysis for GDS specifications. Bridges `gds-framework` structural annotations to `gds-sim` runtime.

## Installation

```bash
uv add gds-analysis
```

## Quick Start

```python
from gds_analysis import spec_to_model, trajectory_distances
from gds_sim import Simulation

# Build a runnable model from a GDSSpec
model = spec_to_model(
    spec,
    policies={"Sensor": sensor_fn, "Controller": controller_fn},
    sufs={"Heater": heater_fn},
    initial_state={"Room.temperature": 18.0},
)

# Run simulation
sim = Simulation(model=model, timesteps=100)
results = sim.run()

# Compute distances using StateMetric annotations
distances = trajectory_distances(spec, results.to_list())
```

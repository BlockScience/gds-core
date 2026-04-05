# Getting Started

## Installation

```bash
uv add gds-analysis
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## From Specification to Simulation

The typical workflow: build a GDS specification from a domain model, supply behavioral functions, then simulate.

```python
from gds_domains.control import (
    State, Input, Sensor, Controller,
    ControlModel, compile_model,
)
from gds_analysis import spec_to_model

# 1. Build a GDS specification from a control model
model = ControlModel(
    name="Thermostat",
    states=[State(name="temperature", initial=20.0)],
    inputs=[Input(name="setpoint")],
    sensors=[Sensor(name="thermometer", observes=["temperature"])],
    controllers=[
        Controller(name="PID", reads=["thermometer", "setpoint"], drives=["temperature"]),
    ],
)
spec = compile_model(model)

# 2. Supply behavioral functions (R3 -- not in the spec)
sim_model = spec_to_model(
    spec,
    policies={
        "thermometer": lambda state, params, **kw: {"reading": state["temperature"]},
        "PID": lambda state, params, **kw: {
            "command": params["Kp"] * (params["setpoint"] - state["temperature"])
        },
    },
    sufs={
        "temperature": lambda state, params, signal=None, **kw: (
            "temperature",
            state["temperature"] + signal["command"] * 0.1,
        ),
    },
    initial_state={"temperature": 20.0},
    params={"setpoint": 22.0, "Kp": 0.3},
)

# 3. Run via gds-sim
from gds_sim import Simulation

results = Simulation(model=sim_model, timesteps=50, runs=1).run()
print(f"Final temperature: {results['temperature'][-1]:.1f}")
```

## Guarded Policies

Enforce `AdmissibleInputConstraint` at runtime:

```python
from gds_analysis import guarded_policy

# Wrap a policy to enforce admissibility
safe_policy = guarded_policy(
    policy_fn=my_policy,
    constraint=lambda state, action: action["power"] <= state["max_power"],
    fallback=lambda state, params, **kw: {"power": 0.0},
)
```

If the constraint predicate returns `False`, the fallback function is called instead. Without a fallback, `ConstraintViolationError` is raised.

## Computing Reachable Sets

Explore what states are reachable from an initial condition:

```python
from gds_analysis import reachable_set, reachable_graph, configuration_space

# R(x) = set of states reachable in one step from x
reached = reachable_set(
    spec,
    sim_model,
    state={"temperature": 20.0},
    input_samples=[
        {"command": 0.0},
        {"command": 1.0},
        {"command": -1.0},
    ],
)
print(f"Reachable states: {len(reached)}")

# Build graph over sampled states and extract configuration space
graph = reachable_graph(spec, sim_model, states=sampled_states, input_samples=inputs)
x_c = configuration_space(graph)  # largest SCC -- mutually reachable states
```

## Trajectory Analysis

Measure convergence along a simulation trajectory:

```python
from gds_analysis import trajectory_distances

distances = trajectory_distances(
    results,
    metric=lambda s1, s2: abs(s1["temperature"] - s2["temperature"]),
)

# Check convergence: distances should decrease
print(f"Initial distance: {distances[0]:.3f}")
print(f"Final distance:   {distances[-1]:.3f}")
```

## Next Steps

- [Analysis Overview](index.md) -- architecture and key functions
- [Framework](../framework/index.md) -- GDS specification and structural annotations
- [PSUU](../psuu/index.md) -- systematic parameter exploration over simulations

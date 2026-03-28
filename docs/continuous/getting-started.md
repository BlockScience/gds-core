# Getting Started

## Installation

```bash
uv add "gds-continuous[scipy]"
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First ODE: Exponential Decay

Model the simplest continuous-time system: exponential decay `dx/dt = -kx`.

```python
from gds_continuous import ODEModel, ODESimulation, ODEResults

# 1. Define the right-hand side: dx/dt = f(t, x, params)
def decay_rhs(t, state, params):
    k = params["k"]
    return {"x": -k * state["x"]}

# 2. Build the model
model = ODEModel(
    state_names=["x"],
    initial_state={"x": 10.0},
    rhs=decay_rhs,
    params={"k": 0.5},
)

# 3. Configure and run the simulation
sim = ODESimulation(model=model, t_span=(0.0, 10.0), solver="RK45")
results: ODEResults = sim.run()

# 4. Inspect results
print(f"t = {results.t[-1]:.1f}, x = {results['x'][-1]:.4f}")
# t = 10.0, x = 0.0067
```

## Plotting Results

```python
import matplotlib.pyplot as plt

plt.plot(results.t, results["x"])
plt.xlabel("Time")
plt.ylabel("x(t)")
plt.title("Exponential Decay: dx/dt = -0.5x")
plt.grid(True)
plt.show()
```

## A Two-State System: Lotka-Volterra

Model predator-prey dynamics with coupled ODEs:

```python
from gds_continuous import ODEModel, ODESimulation

def lotka_volterra(t, state, params):
    x, y = state["prey"], state["predator"]
    a, b, c, d = params["a"], params["b"], params["c"], params["d"]
    return {
        "prey": a * x - b * x * y,
        "predator": c * x * y - d * y,
    }

model = ODEModel(
    state_names=["prey", "predator"],
    initial_state={"prey": 10.0, "predator": 5.0},
    rhs=lotka_volterra,
    params={"a": 1.1, "b": 0.4, "c": 0.1, "d": 0.4},
)

sim = ODESimulation(model=model, t_span=(0.0, 50.0), solver="RK45")
results = sim.run()
```

## Parameter Sweep

Compare different decay rates by running multiple simulations:

```python
import matplotlib.pyplot as plt
from gds_continuous import ODEModel, ODESimulation

def decay_rhs(t, state, params):
    return {"x": -params["k"] * state["x"]}

fig, ax = plt.subplots()
for k in [0.1, 0.3, 0.5, 1.0, 2.0]:
    model = ODEModel(
        state_names=["x"],
        initial_state={"x": 10.0},
        rhs=decay_rhs,
        params={"k": k},
    )
    results = ODESimulation(model=model, t_span=(0.0, 10.0), solver="RK45").run()
    ax.plot(results.t, results["x"], label=f"k={k}")

ax.set_xlabel("Time")
ax.set_ylabel("x(t)")
ax.legend()
ax.set_title("Exponential Decay: Parameter Sweep")
plt.show()
```

## Choosing a Solver

For most problems, the default `RK45` works well. Switch solvers when needed:

```python
# Stiff system -- use an implicit solver
sim = ODESimulation(model=model, t_span=(0.0, 10.0), solver="Radau")

# Unknown stiffness -- let LSODA auto-detect
sim = ODESimulation(model=model, t_span=(0.0, 10.0), solver="LSODA")

# High accuracy -- use DOP853 with tight tolerances
sim = ODESimulation(model=model, t_span=(0.0, 10.0), solver="DOP853", rtol=1e-10, atol=1e-12)
```

## Next Steps

- [Overview](index.md) -- solver comparison table and architecture
- [Symbolic Math](../symbolic/index.md) -- generate ODE right-hand sides from symbolic equations
- [Analysis](../analysis/index.md) -- bridge GDS specifications to continuous-time simulation

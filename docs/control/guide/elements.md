# Elements & GDS Mapping

`gds-control` provides four element types, each mapping to a specific GDS role and corresponding to the standard state-space representation.

## State

A state variable in the plant. Each state becomes a GDS entity with a `value` state variable, and a dynamics block that applies incoming control signals.

```python
State(name="temperature", initial=20.0)
```

**GDS mapping:** `Mechanism` (state update *f*) + `Entity` (state *X*)

**State-space:** x (state vector)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | State name (becomes entity name) |
| `initial` | float \| None | None | Initial value |

### Port Convention

- Output: `"{Name} State"` (temporal feedback to sensors)
- Input: `"{ControllerName} Control"` (incoming control signals)

---

## Input

An exogenous reference signal or disturbance entering the system from outside. Inputs have no internal sources -- they represent the boundary between the system and its environment.

```python
Input(name="setpoint")
```

**GDS mapping:** `BoundaryAction` (exogenous input *U*)

**State-space:** r (reference signal)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Input name |

### Port Convention

- Output: `"{Name} Reference"`

---

## Sensor

A sensor reads state variables and emits a measurement signal. The `observes` list declares which states the sensor can read -- validated at model construction time.

```python
Sensor(name="thermometer", observes=["temperature"])
```

**GDS mapping:** `Policy` (observation *g*)

**State-space:** y = Cx + Du (sensor output)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Sensor name |
| `observes` | list[str] | [] | Names of states this sensor reads |

### Port Convention

- Input: `"{StateName} State"`
- Output: `"{Name} Measurement"`

---

## Controller

A controller reads sensor measurements and/or reference inputs, then emits control signals to drive state variables.

```python
Controller(name="PID", reads=["thermometer", "setpoint"], drives=["temperature"])
```

**GDS mapping:** `Policy` (decision logic *g*)

**State-space:** u = K(y, r) (control law)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Controller name |
| `reads` | list[str] | [] | Names of sensors/inputs this controller reads |
| `drives` | list[str] | [] | Names of states this controller drives |

### Port Convention

- Input: `"{ReadName} Measurement"` or `"{ReadName} Reference"`
- Output: `"{Name} Control"`

---

## Semantic Type System

Four distinct semantic spaces, all `float`-backed but structurally separate -- this prevents accidentally wiring a measurement where a control signal is expected:

| Type | Space | Used By | Description |
|------|-------|---------|-------------|
| `StateType` | `StateSpace` | States | Plant state variables |
| `ReferenceType` | `ReferenceSpace` | Inputs | Exogenous reference/disturbance signals |
| `MeasurementType` | `MeasurementSpace` | Sensors | Sensor output measurements |
| `ControlType` | `ControlSpace` | Controllers | Controller output signals |

## Composition Structure

The compiler builds a tiered composition tree:

```
(inputs | sensors) >> (controllers) >> (state dynamics)
    .loop([state dynamics forward_out -> sensor forward_in])
```

This maps to the GDS canonical form `h = f . g` where states carry state (X), dynamics provide f, and sensors + controllers contribute to g.

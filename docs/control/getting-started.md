# Getting Started

## Installation

```bash
uv add gds-control
# or: pip install gds-control
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Control Model

A control model describes a feedback control system: states represent the plant, inputs provide reference signals, sensors observe state, and controllers compute control actions.

```python
from gds_control import (
    State, Input, Sensor, Controller,
    ControlModel, compile_model, compile_to_system, verify,
)

# Declare a thermostat control system
model = ControlModel(
    name="Thermostat",
    states=[State(name="temperature", initial=20.0)],
    inputs=[Input(name="setpoint")],
    sensors=[Sensor(name="thermometer", observes=["temperature"])],
    controllers=[
        Controller(
            name="PID",
            reads=["thermometer", "setpoint"],
            drives=["temperature"],
        )
    ],
)

# Compile to GDS
spec = compile_model(model)
print(f"Blocks: {len(spec.blocks)}")      # 4 blocks
print(f"Entities: {len(spec.entities)}")   # 1 (temperature state)

# Compile to SystemIR for verification
ir = compile_to_system(model)
print(f"{len(ir.blocks)} blocks, {len(ir.wirings)} wirings")

# Verify — domain checks + GDS structural checks
report = verify(model, include_gds_checks=True)
print(f"{report.checks_passed}/{report.checks_total} checks passed")
```

## A Multi-State Model

Control models support multiple states with multiple sensors and controllers:

```python
from gds_control import (
    State, Input, Sensor, Controller,
    ControlModel, verify,
)

model = ControlModel(
    name="HVAC System",
    states=[
        State(name="temperature", initial=22.0),
        State(name="humidity", initial=45.0),
    ],
    inputs=[
        Input(name="temp_setpoint"),
        Input(name="humidity_setpoint"),
    ],
    sensors=[
        Sensor(name="temp_sensor", observes=["temperature"]),
        Sensor(name="humidity_sensor", observes=["humidity"]),
    ],
    controllers=[
        Controller(
            name="heater",
            reads=["temp_sensor", "temp_setpoint"],
            drives=["temperature"],
        ),
        Controller(
            name="humidifier",
            reads=["humidity_sensor", "humidity_setpoint"],
            drives=["humidity"],
        ),
    ],
)

# Verify
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'PASS' if f.passed else 'FAIL'} {f.message}")
```

## Next Steps

- [Elements & GDS Mapping](guide/elements.md) -- detailed element reference and how each maps to GDS
- [Verification Guide](guide/verification.md) -- all 6 domain checks explained
- [API Reference](api/init.md) -- complete auto-generated API docs

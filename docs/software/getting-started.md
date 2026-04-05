# Getting Started

## Installation

```bash
uv add gds-software
# or: pip install gds-domains
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First DFD

A Data Flow Diagram models processes, external entities, data stores, and the flows between them:

```python
from gds_domains.software import (
    ExternalEntity, Process, DataStore, DataFlow,
    DFDModel, compile_dfd, compile_dfd_to_system, verify,
)

model = DFDModel(
    name="Order System",
    entities=[ExternalEntity(name="Customer")],
    processes=[
        Process(name="Validate Order"),
        Process(name="Process Payment"),
    ],
    stores=[DataStore(name="Order DB")],
    flows=[
        DataFlow(name="Order", source="Customer", target="Validate Order"),
        DataFlow(name="Valid Order", source="Validate Order", target="Process Payment"),
        DataFlow(name="Record", source="Process Payment", target="Order DB"),
        DataFlow(name="Confirmation", source="Process Payment", target="Customer"),
    ],
)

# Compile to GDS
spec = compile_dfd(model)
ir = compile_dfd_to_system(model)
print(f"{len(ir.blocks)} blocks, {len(ir.wirings)} wirings")

# Verify
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'PASS' if f.passed else 'FAIL'} {f.message}")
```

## Your First State Machine

A State Machine models states, events, and transitions:

```python
from gds_domains.software import (
    State, Event, Transition, StateMachineModel,
    compile_sm, verify,
)

model = StateMachineModel(
    name="Traffic Light",
    states=[
        State(name="Red", is_initial=True),
        State(name="Green"),
        State(name="Yellow"),
    ],
    events=[
        Event(name="timer"),
    ],
    transitions=[
        Transition(source="Red", target="Green", event="timer"),
        Transition(source="Green", target="Yellow", event="timer"),
        Transition(source="Yellow", target="Red", event="timer"),
    ],
)

# Compile and verify
spec = compile_sm(model)
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'PASS' if f.passed else 'FAIL'} {f.message}")
```

## Your First Component Diagram

A Component Diagram models software components with provided and required interfaces:

```python
from gds_domains.software import (
    Component, InterfaceDef, Connector,
    ComponentModel, compile_component, verify,
)

model = ComponentModel(
    name="Web App",
    components=[
        Component(name="Frontend", provides=["UI"], requires=["API"]),
        Component(name="Backend", provides=["API"], requires=["DB"]),
        Component(name="Database", provides=["DB"]),
    ],
    interfaces=[
        InterfaceDef(name="UI"),
        InterfaceDef(name="API"),
        InterfaceDef(name="DB"),
    ],
    connectors=[
        Connector(name="F->B", source="Frontend", target="Backend", interface="API"),
        Connector(name="B->D", source="Backend", target="Database", interface="DB"),
    ],
)

spec = compile_component(model)
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'PASS' if f.passed else 'FAIL'} {f.message}")
```

## Next Steps

- [Diagram Types Guide](guide/diagram-types.md) -- all 6 diagram types with elements and GDS mapping
- [Verification Guide](guide/verification.md) -- all 27 domain checks explained
- [API Reference](api/init.md) -- complete auto-generated API docs

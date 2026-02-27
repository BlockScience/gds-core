# Verification Guide

A hands-on walkthrough of the three verification layers in GDS, using deliberately broken models to demonstrate what each check catches and how to fix it.

## Three Verification Layers

| Layer | Checks | Operates on | Catches |
|-------|--------|-------------|---------|
| **Generic** | G-001..G-006 | `SystemIR` | Structural topology errors |
| **Semantic** | SC-001..SC-007 | `GDSSpec` | Domain property violations |
| **Domain** | SF-001..SF-005 | DSL model | DSL-specific errors |

Each layer operates on a different representation, and the layers are complementary: a model can pass all generic checks but fail semantic checks (and vice versa).

---

## Layer 1: Generic Checks (G-series)

Generic checks operate on the compiled `SystemIR` -- the flat block graph with typed wirings. They verify **structural topology** independent of any domain semantics.

### G-004: Dangling Wirings

A wiring references a block that does not exist in the system.

```python
from gds.ir.models import BlockIR, FlowDirection, SystemIR, WiringIR

system = SystemIR(
    name="Dangling Wiring Demo",
    blocks=[
        BlockIR(name="A", signature=("", "Signal", "", "")),
        BlockIR(name="B", signature=("Signal", "", "", "")),
    ],
    wirings=[
        WiringIR(
            source="Ghost",  # does not exist!
            target="B",
            label="signal",
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

```python
from gds.verification.engine import verify
from gds.verification.generic_checks import check_g004_dangling_wirings

report = verify(system, checks=[check_g004_dangling_wirings])
# -> G-004 FAIL: source 'Ghost' unknown
```

### G-001/G-005: Type Mismatches

Block A outputs `Temperature` but Block B expects `Pressure`. The wiring label does not match either side.

```python
system = SystemIR(
    name="Type Mismatch Demo",
    blocks=[
        BlockIR(name="A", signature=("", "Temperature", "", "")),
        BlockIR(name="B", signature=("Pressure", "", "", "")),
    ],
    wirings=[
        WiringIR(
            source="A", target="B",
            label="humidity",  # matches neither side
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

- **G-001** flags: wiring label does not match source out or target in
- **G-005** flags: type mismatch in sequential composition

### G-006: Covariant Cycles

Three blocks form a cycle via non-temporal covariant wirings -- an algebraic loop that cannot be resolved within a single timestep.

```python
system = SystemIR(
    name="Covariant Cycle Demo",
    blocks=[
        BlockIR(name="A", signature=("Signal", "Signal", "", "")),
        BlockIR(name="B", signature=("Signal", "Signal", "", "")),
        BlockIR(name="C", signature=("Signal", "Signal", "", "")),
    ],
    wirings=[
        WiringIR(source="A", target="B", label="signal",
                 direction=FlowDirection.COVARIANT),
        WiringIR(source="B", target="C", label="signal",
                 direction=FlowDirection.COVARIANT),
        WiringIR(source="C", target="A", label="signal",
                 direction=FlowDirection.COVARIANT),
    ],
)
# -> G-006 FAIL: covariant flow graph contains a cycle
```

### G-003: Direction Contradictions

A wiring marked COVARIANT but also `is_feedback=True` is a contradiction: feedback implies contravariant flow.

```python
WiringIR(
    source="A", target="B",
    label="command",
    direction=FlowDirection.COVARIANT,
    is_feedback=True,  # contradiction!
)
# -> G-003 FAIL: COVARIANT + is_feedback contradiction
```

### Fix and Re-verify

The core workflow: build a broken model, run checks, inspect findings, fix errors, re-verify.

```python
from gds.verification.engine import verify
from guides.verification.broken_models import (
    dangling_wiring_system,
    fixed_pipeline_system,
)

# Step 1: Broken model
broken_report = verify(dangling_wiring_system())
# -> errors >= 1

# Step 2: Fixed model
fixed_report = verify(fixed_pipeline_system())
# -> all checks pass, 0 errors
```

---

## Layer 2: Semantic Checks (SC-series)

Semantic checks operate on `GDSSpec` -- the specification registry with types, entities, blocks, and parameters. They verify **domain properties** like completeness, determinism, and canonical well-formedness.

### SC-001: Orphan State Variables

Entity `Reservoir` has variable `level` but no mechanism updates it.

```python
from gds.blocks.roles import Policy
from gds.spec import GDSSpec
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

Count = TypeDef(name="Count", python_type=int, constraint=lambda x: x >= 0)

spec = GDSSpec(name="Orphan State Demo")
spec.register_type(Count)

reservoir = Entity(
    name="Reservoir",
    variables={
        "level": StateVariable(name="level", typedef=Count, symbol="L"),
    },
)
spec.register_entity(reservoir)

# A policy observes but no mechanism updates the reservoir
observe = Policy(
    name="Observe Level",
    interface=Interface(forward_out=(port("Level Signal"),)),
)
spec.register_block(observe)
```

```python
from gds.verification.spec_checks import check_completeness

findings = check_completeness(spec)
# -> SC-001 WARNING: orphan state variable Reservoir.level
```

### SC-002: Write Conflicts

Two mechanisms both update `Counter.value` within the same wiring -- non-deterministic state transition.

```python
from gds.blocks.roles import BoundaryAction, Mechanism

inc = Mechanism(
    name="Increment Counter",
    interface=Interface(forward_in=(port("Delta Signal"),)),
    updates=[("Counter", "value")],
)

dec = Mechanism(
    name="Decrement Counter",
    interface=Interface(forward_in=(port("Delta Signal"),)),
    updates=[("Counter", "value")],  # same variable!
)
```

```python
from gds.verification.spec_checks import check_determinism

findings = check_determinism(spec)
# -> SC-002 ERROR: write conflict -- Counter.value updated by two mechanisms
```

### SC-006/SC-007: Empty Canonical Form

A spec with no mechanisms and no entities -- empty state transition and empty state space.

```python
spec = GDSSpec(name="Empty Canonical Demo")
spec.register_block(Policy(
    name="Observer",
    interface=Interface(
        forward_in=(port("Input Signal"),),
        forward_out=(port("Output Signal"),),
    ),
))
```

```python
from gds.verification.spec_checks import check_canonical_wellformedness

findings = check_canonical_wellformedness(spec)
# -> SC-006 FAIL: no mechanisms found -- state transition f is empty
# -> SC-007 FAIL: state space X is empty
```

---

## Layer 3: Domain Checks (SF-series)

Domain checks operate on the **DSL model** before compilation. They catch errors that only make sense in the domain semantics -- for example, "orphan stock" is meaningless outside stock-flow.

The StockFlow DSL provides SF-001..SF-005, running before GDS compilation for early feedback in domain-native terms.

### SF-001: Orphan Stocks

A stock has no connected flows -- nothing fills or drains it.

```python
from stockflow.dsl.elements import Flow, Stock
from stockflow.dsl.model import StockFlowModel

model = StockFlowModel(
    name="Orphan Stock Demo",
    stocks=[
        Stock(name="Active"),
        Stock(name="Inventory"),  # no flows!
    ],
    flows=[
        Flow(name="Production", target="Active"),
        Flow(name="Consumption", source="Active"),
    ],
)
```

```python
from stockflow.verification.checks import check_sf001_orphan_stocks

findings = check_sf001_orphan_stocks(model)
# -> SF-001 WARNING: Stock 'Inventory' has no connected flows
```

### SF-003: Auxiliary Cycles

Circular dependency between auxiliaries -- Price depends on Demand, which depends on Price.

```python
from stockflow.dsl.elements import Auxiliary, Stock
from stockflow.dsl.model import StockFlowModel

model = StockFlowModel(
    name="Cyclic Auxiliary Demo",
    stocks=[Stock(name="Supply")],
    auxiliaries=[
        Auxiliary(name="Price", inputs=["Demand"]),
        Auxiliary(name="Demand", inputs=["Price"]),
    ],
)
```

```python
from stockflow.verification.checks import check_sf003_auxiliary_acyclicity

findings = check_sf003_auxiliary_acyclicity(model)
# -> SF-003 ERROR: cycle detected in auxiliary dependency graph
```

### SF-004: Unused Converters

A converter is declared but no auxiliary reads from it.

```python
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel

model = StockFlowModel(
    name="Unused Converter Demo",
    stocks=[Stock(name="Revenue")],
    flows=[Flow(name="Income", target="Revenue")],
    auxiliaries=[Auxiliary(name="Growth", inputs=["Revenue"])],
    converters=[Converter(name="Tax Rate")],  # unused!
)
```

```python
from stockflow.verification.checks import check_sf004_converter_connectivity

findings = check_sf004_converter_connectivity(model)
# -> SF-004 WARNING: Converter 'Tax Rate' is NOT referenced by any auxiliary
```

### Combined Domain + GDS Checks

The StockFlow verification engine can run domain checks (SF) **and** generic GDS checks (G) together:

```python
from stockflow.verification.engine import verify

report = verify(model, include_gds_checks=True)

sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
```

---

## Check Reference

### Generic Checks (SystemIR)

| ID | Name | Catches |
|----|------|---------|
| G-001 | Domain/codomain matching | Wiring label vs port mismatch |
| G-002 | Signature completeness | Blocks with no ports |
| G-003 | Direction consistency | COVARIANT + feedback flag |
| G-004 | Dangling wirings | References to missing blocks |
| G-005 | Sequential type compat | Mismatched `>>` port types |
| G-006 | Covariant acyclicity | Algebraic loops |

### Semantic Checks (GDSSpec)

| ID | Name | Catches |
|----|------|---------|
| SC-001 | Completeness | Orphan state variables |
| SC-002 | Determinism | Write conflicts |
| SC-003 | Reachability | Unreachable blocks |
| SC-004 | Type safety | TypeDef violations |
| SC-005 | Parameter refs | Unregistered params |
| SC-006 | Canonical f | No mechanisms |
| SC-007 | Canonical X | No state space |

### Domain Checks (StockFlowModel)

| ID | Name | Catches |
|----|------|---------|
| SF-001 | Orphan stocks | Stocks with no flows |
| SF-003 | Auxiliary cycles | Circular aux deps |
| SF-004 | Converter connectivity | Unused converters |

### API Pattern

```python
from gds.verification.engine import verify

system = compile_system(name="My Model", root=pipeline)
report = verify(system)

for finding in report.findings:
    print(f"{finding.check_id}: {finding.message}")
```

## Running Interactively

The guide includes a [marimo notebook](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/verification/notebook.py) with interactive dropdowns for selecting broken models and watching checks in real time:

```bash
uv run marimo run packages/gds-examples/guides/verification/notebook.py
```

Run the test suite:

```bash
uv run --package gds-examples pytest packages/gds-examples/guides/verification/ -v
```

## Source Files

| File | Purpose |
|------|---------|
| [`broken_models.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/verification/broken_models.py) | Deliberately broken models for each check |
| [`verification_demo.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/verification/verification_demo.py) | Generic and semantic check demos |
| [`domain_checks_demo.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/verification/domain_checks_demo.py) | StockFlow domain check demos |
| [`notebook.py`](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/guides/verification/notebook.py) | Interactive marimo notebook |

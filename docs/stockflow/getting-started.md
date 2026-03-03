# Getting Started

## Installation

```bash
uv add gds-stockflow
# or: pip install gds-stockflow
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Stock-Flow Model

A stock-flow model describes accumulation dynamics: stocks hold value, flows transfer it, auxiliaries compute intermediate values, and converters inject exogenous inputs.

```python
from stockflow import (
    Stock, Flow, Auxiliary, Converter,
    StockFlowModel, compile_model, compile_to_system, verify,
)

# Declare a simple population model
model = StockFlowModel(
    name="Population",
    stocks=[Stock(name="Population", initial=1000.0)],
    flows=[
        Flow(name="Births", target="Population"),
        Flow(name="Deaths", source="Population"),
    ],
    auxiliaries=[
        Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
        Auxiliary(name="Death Rate", inputs=["Population"]),
    ],
    converters=[Converter(name="Fertility")],
)

# Compile to GDS
spec = compile_model(model)
print(f"Blocks: {len(spec.blocks)}")      # 6 blocks
print(f"Entities: {len(spec.entities)}")   # 1 (Population stock)

# Compile to SystemIR for verification
ir = compile_to_system(model)
print(f"{len(ir.blocks)} blocks, {len(ir.wirings)} wirings")

# Verify — domain checks + GDS structural checks
report = verify(model, include_gds_checks=True)
print(f"{report.checks_passed}/{report.checks_total} checks passed")
```

## A Multi-Stock Model

Stock-flow models shine with multiple interacting stocks:

```python
from stockflow import (
    Stock, Flow, Auxiliary, StockFlowModel, verify,
)

model = StockFlowModel(
    name="SIR Epidemic",
    stocks=[
        Stock(name="Susceptible", initial=990.0),
        Stock(name="Infected", initial=10.0),
        Stock(name="Recovered", initial=0.0),
    ],
    flows=[
        Flow(name="Infection", source="Susceptible", target="Infected"),
        Flow(name="Recovery", source="Infected", target="Recovered"),
    ],
    auxiliaries=[
        Auxiliary(name="Infection Rate", inputs=["Susceptible", "Infected"]),
        Auxiliary(name="Recovery Rate", inputs=["Infected"]),
    ],
)

# Compile and verify
spec = model.compile() if hasattr(model, 'compile') else compile_model(model)
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'PASS' if f.passed else 'FAIL'} {f.message}")
```

## Next Steps

- [Elements & GDS Mapping](guide/elements.md) -- detailed element reference and how each maps to GDS
- [Verification Guide](guide/verification.md) -- all 5 domain checks explained
- [API Reference](api/init.md) -- complete auto-generated API docs

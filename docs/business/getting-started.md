# Getting Started

## Installation

```bash
uv add gds-business
# or: pip install gds-business
```

For development (monorepo):

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First CLD

A Causal Loop Diagram models feedback structure using variables and causal links:

```python
from gds_business import (
    Variable, CausalLink, CausalLoopModel, verify
)

model = CausalLoopModel(
    name="Population Dynamics",
    variables=[
        Variable(name="Population"),
        Variable(name="Births"),
        Variable(name="Deaths"),
    ],
    links=[
        CausalLink(source="Population", target="Births", polarity="+"),
        CausalLink(source="Births", target="Population", polarity="+"),
        CausalLink(source="Population", target="Deaths", polarity="+"),
        CausalLink(source="Deaths", target="Population", polarity="-"),
    ],
)

# Compile to GDS
spec = model.compile()
print(f"Blocks: {len(spec.blocks)}")    # 3 Policy blocks
print(f"Entities: {len(spec.entities)}")  # 0 (stateless)

# Verify
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'✓' if f.passed else '✗'} {f.message}")
```

## Your First Supply Chain

A Supply Chain Network models inventory dynamics across nodes:

```python
from gds_business import (
    SupplyNode, Shipment, DemandSource, OrderPolicy,
    SupplyChainModel, verify,
)

model = SupplyChainModel(
    name="Beer Game",
    nodes=[
        SupplyNode(name="Factory", initial_inventory=100),
        SupplyNode(name="Distributor", initial_inventory=100),
        SupplyNode(name="Retailer", initial_inventory=100),
    ],
    shipments=[
        Shipment(name="F->D", source_node="Factory", target_node="Distributor"),
        Shipment(name="D->R", source_node="Distributor", target_node="Retailer"),
    ],
    demand_sources=[
        DemandSource(name="Customer", target_node="Retailer"),
    ],
    order_policies=[
        OrderPolicy(name="Retailer Policy", node="Retailer", inputs=["Retailer"]),
        OrderPolicy(name="Distributor Policy", node="Distributor", inputs=["Distributor"]),
        OrderPolicy(name="Factory Policy", node="Factory", inputs=["Factory"]),
    ],
)

# Compile — stateful, with inventory entities
spec = model.compile()
print(f"Entities: {len(spec.entities)}")  # 3 (one per node)

# Verify
report = verify(model, include_gds_checks=False)
for f in report.findings:
    if not f.passed:
        print(f"  [{f.check_id}] ✗ {f.message}")
```

## Your First Value Stream Map

A Value Stream Map models lean manufacturing flows:

```python
from gds_business import (
    ProcessStep, InventoryBuffer, Supplier, Customer,
    MaterialFlow, ValueStreamModel, verify,
)

model = ValueStreamModel(
    name="Assembly Line",
    steps=[
        ProcessStep(name="Cutting", cycle_time=30.0, uptime=0.95),
        ProcessStep(name="Welding", cycle_time=45.0, uptime=0.90),
        ProcessStep(name="Assembly", cycle_time=25.0),
    ],
    buffers=[
        InventoryBuffer(name="Cut WIP", between=("Cutting", "Welding"), quantity=10),
        InventoryBuffer(name="Weld WIP", between=("Welding", "Assembly"), quantity=5),
    ],
    suppliers=[Supplier(name="Steel Supplier")],
    customers=[Customer(name="End Customer", takt_time=50.0)],
    material_flows=[
        MaterialFlow(source="Steel Supplier", target="Cutting"),
        MaterialFlow(source="Cutting", target="Cut WIP"),
        MaterialFlow(source="Cut WIP", target="Welding"),
        MaterialFlow(source="Welding", target="Weld WIP"),
        MaterialFlow(source="Weld WIP", target="Assembly"),
        MaterialFlow(source="Assembly", target="End Customer"),
    ],
)

# With buffers → stateful (Mechanism + Entity)
spec = model.compile()
print(f"Entities: {len(spec.entities)}")  # 2 buffers

# Verify — check bottleneck vs takt time
report = verify(model, include_gds_checks=False)
for f in report.findings:
    print(f"  [{f.check_id}] {'✓' if f.passed else '✗'} {f.message}")
```

## Next Steps

- [Diagram Types Guide](guide/diagram-types.md) — detailed element reference and GDS mapping
- [Verification Guide](guide/verification.md) — all 11 domain checks explained
- [API Reference](api/index.md) — complete auto-generated API docs

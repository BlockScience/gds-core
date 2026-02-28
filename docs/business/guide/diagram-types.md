# Diagram Types

`gds-business` supports three business dynamics diagram types, each with its own element vocabulary, GDS mapping, and composition structure.

## Causal Loop Diagram (CLD)

Causal loop diagrams model **feedback structure** in complex systems using variables and directed causal links.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `Variable` | A system variable (e.g., Population, Revenue) | Policy |
| `CausalLink` | Directed influence with polarity (+/-) and optional delay | Wiring |

### Polarity

- **Positive (+)**: Source increases → target increases (same direction)
- **Negative (-)**: Source increases → target decreases (opposite direction)

### Loop Classification

Loops are classified by counting negative links:

- **Even negatives** → **Reinforcing (R)** — amplifies change
- **Odd negatives** → **Balancing (B)** — counteracts change

### GDS Mapping

All variables map to `Policy` blocks (signal relays). No state, no entities. Single parallel tier composition.

```
Composition: (all_variables |)
Canonical:   h = g (stateless)
```

### Example

```python
from gds_business import Variable, CausalLink, CausalLoopModel

model = CausalLoopModel(
    name="Market Dynamics",
    variables=[
        Variable(name="Price"),
        Variable(name="Demand"),
        Variable(name="Supply"),
    ],
    links=[
        CausalLink(source="Price", target="Demand", polarity="-"),
        CausalLink(source="Price", target="Supply", polarity="+"),
        CausalLink(source="Demand", target="Price", polarity="+"),
        CausalLink(source="Supply", target="Price", polarity="-"),
    ],
)
```

---

## Supply Chain Network (SCN)

Supply chain networks model **multi-echelon inventory dynamics** with demand signals, order policies, and material flows.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `SupplyNode` | Warehouse/factory with inventory state | Mechanism + Entity |
| `Shipment` | Directed flow link between nodes | Wiring |
| `DemandSource` | Exogenous demand signal | BoundaryAction |
| `OrderPolicy` | Reorder decision logic | Policy |

### GDS Mapping

Three-tier composition with temporal feedback loop:

```
Composition: (demands |) >> (policies |) >> (node_mechanisms |)
                 .loop([inventory → policies])
Canonical:   h = f ∘ g (stateful — inventory stocks are state X)
```

### Semantic Types

| Type | Space | Description |
|------|-------|-------------|
| `InventoryType` | `InventorySpace` | Inventory level at a node |
| `ShipmentRateType` | `ShipmentRateSpace` | Rate of material flow |
| `DemandType` | `DemandSpace` | Exogenous demand signal |

### Example

```python
from gds_business import (
    SupplyNode, Shipment, DemandSource, OrderPolicy,
    SupplyChainModel,
)

model = SupplyChainModel(
    name="Two-Echelon Chain",
    nodes=[
        SupplyNode(name="Warehouse", initial_inventory=200, capacity=500),
        SupplyNode(name="Retail", initial_inventory=50),
    ],
    shipments=[
        Shipment(name="W->R", source_node="Warehouse", target_node="Retail", lead_time=2.0),
    ],
    demand_sources=[
        DemandSource(name="Customer Demand", target_node="Retail"),
    ],
    order_policies=[
        OrderPolicy(name="Retail Reorder", node="Retail", inputs=["Retail"]),
    ],
)
```

---

## Value Stream Map (VSM)

Value stream maps model **lean manufacturing process flows** with process steps, inventory buffers, suppliers, customers, and material/information flows.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `ProcessStep` | Processing stage with cycle time, uptime, etc. | Policy |
| `InventoryBuffer` | WIP buffer between stages | Mechanism + Entity |
| `Supplier` | External material source | BoundaryAction |
| `Customer` | External demand sink with takt time | BoundaryAction |
| `MaterialFlow` | Material movement (push or pull) | Wiring |
| `InformationFlow` | Signal/kanban flow | Wiring |

### GDS Mapping

Three-tier composition with optional temporal loop:

```
Composition: (suppliers | customers) >> (steps |) >> (buffers |)
                 .loop([buffer content → steps])  # if buffers exist
Canonical:   h = g (no buffers) or h = f ∘ g (with buffers)
```

### Semantic Types

| Type | Space | Description |
|------|-------|-------------|
| `MaterialType` | `MaterialSpace` | Material flow payload |
| `ProcessSignalType` | `ProcessSignalSpace` | Process step signal/kanban |

### Push vs Pull

Material flows carry a `flow_type` attribute:

- **push** — material is pushed downstream based on production schedule
- **pull** — material is pulled by downstream demand (kanban)

VSM-002 identifies where the flow type transitions, marking the **push/pull boundary**.

### Example

```python
from gds_business import (
    ProcessStep, InventoryBuffer, Supplier, Customer,
    MaterialFlow, InformationFlow, ValueStreamModel,
)

model = ValueStreamModel(
    name="Assembly Line",
    steps=[
        ProcessStep(name="Stamping", cycle_time=10.0, changeover_time=30.0, uptime=0.85),
        ProcessStep(name="Welding", cycle_time=45.0, uptime=0.90),
        ProcessStep(name="Assembly", cycle_time=25.0, operators=3),
    ],
    buffers=[
        InventoryBuffer(name="Stamped Parts", between=("Stamping", "Welding"), quantity=100),
    ],
    suppliers=[Supplier(name="Coil Supplier")],
    customers=[Customer(name="Shipping", takt_time=60.0)],
    material_flows=[
        MaterialFlow(source="Coil Supplier", target="Stamping"),
        MaterialFlow(source="Stamping", target="Stamped Parts"),
        MaterialFlow(source="Stamped Parts", target="Welding", flow_type="push"),
        MaterialFlow(source="Welding", target="Assembly", flow_type="pull"),
        MaterialFlow(source="Assembly", target="Shipping"),
    ],
    information_flows=[
        InformationFlow(source="Shipping", target="Assembly"),
    ],
)
```

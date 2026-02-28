# gds-business

[![PyPI](https://img.shields.io/pypi/v/gds-business)](https://pypi.org/project/gds-business/)
[![Python](https://img.shields.io/pypi/pyversions/gds-business)](https://pypi.org/project/gds-business/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Business dynamics DSL over GDS semantics** — causal loop diagrams, supply chain networks, and value stream maps with formal verification.

## What is this?

`gds-business` extends the GDS framework with business dynamics vocabulary — system dynamics diagrams, supply chain modeling, and lean manufacturing analysis. It provides:

- **3 diagram types** — Causal Loop Diagrams (CLD), Supply Chain Networks (SCN), Value Stream Maps (VSM)
- **Typed compilation** — Each diagram compiles to GDS role blocks, entities, and composition trees
- **11 verification checks** — Domain-specific structural validation (CLD-001..003, SCN-001..004, VSM-001..004)
- **Canonical decomposition** — Validated h = f ∘ g projection across all three diagram types
- **Full GDS integration** — All downstream tooling works immediately (canonical projection, semantic checks, gds-viz)

## Architecture

```
gds-framework (pip install gds-framework)
│
│  Domain-neutral composition algebra, typed spaces,
│  state model, verification engine, flat IR compiler.
│
└── gds-business (pip install gds-business)
    │
    │  Business dynamics DSL: CLD, SCN, VSM elements,
    │  compile_*(), domain verification, verify() dispatch.
    │
    └── Your application
        │
        │  Concrete business models, analysis notebooks,
        │  verification runners.
```

## Quick Start

```bash
uv add gds-business
# or: pip install gds-business
```

```python
from gds_business import (
    # CLD
    Variable, CausalLink, CausalLoopModel,
    # Supply Chain
    SupplyNode, Shipment, DemandSource, OrderPolicy, SupplyChainModel,
    # VSM
    ProcessStep, InventoryBuffer, Supplier, Customer, MaterialFlow, ValueStreamModel,
    # Verification
    verify,
)

# ── Causal Loop Diagram ─────────────────────────────────
cld = CausalLoopModel(
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

# ── Supply Chain Network ────────────────────────────────
scn = SupplyChainModel(
    name="Beer Game",
    nodes=[
        SupplyNode(name="Factory", initial_inventory=100),
        SupplyNode(name="Retailer", initial_inventory=100),
    ],
    shipments=[
        Shipment(name="F->R", source_node="Factory", target_node="Retailer"),
    ],
    demand_sources=[
        DemandSource(name="Customer", target_node="Retailer"),
    ],
    order_policies=[
        OrderPolicy(name="Reorder", node="Retailer", inputs=["Retailer"]),
    ],
)

# ── Compile & Verify ────────────────────────────────────
spec = cld.compile()          # → GDSSpec
ir = scn.compile_system()     # → SystemIR
report = verify(cld)          # → VerificationReport
```

## Canonical Spectrum

All three diagram types map cleanly onto the GDS canonical form h = f ∘ g:

| Diagram | |X| | |f| | Form | Character |
|---------|-----|-----|------|-----------|
| CLD | 0 | 0 | h = g | Stateless — pure signal relay |
| SCN | n | n | h = f ∘ g | Full dynamical — inventory state |
| VSM (no buffers) | 0 | 0 | h = g | Stateless process chain |
| VSM (with buffers) | m | m | h = f ∘ g | Partially stateful |

## Diagram Types

### Causal Loop Diagrams (CLD)

Model feedback structure in complex systems. Variables connected by causal links with polarity (reinforcing/balancing). Stateless — all variables map to Policy blocks.

### Supply Chain Networks (SCN)

Model multi-echelon supply chains with inventory dynamics. Demand sources drive order policies that update inventory at supply nodes. Stateful — nodes carry inventory state via Mechanism + Entity.

### Value Stream Maps (VSM)

Model lean manufacturing value streams with process steps, inventory buffers, and material/information flows. Partially stateful — buffers add state when present.

## Credits

Built on [gds-framework](../framework/index.md) by [BlockScience](https://block.science).

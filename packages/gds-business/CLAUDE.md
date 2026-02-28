# gds-business CLAUDE.md

Business dynamics DSL over GDS semantics. Three diagram types: causal loop diagrams (CLD), supply chain networks (SCN), and value stream maps (VSM).

## Package Layout

```
gds_business/
├── common/          # Shared types, errors, compile utilities
├── cld/             # Causal Loop Diagrams (stateless)
├── supplychain/     # Supply Chain Networks (stateful)
├── vsm/             # Value Stream Maps (partially stateful)
└── verification/    # Union dispatch verify()
```

Each diagram subpackage follows the 4-file pattern: `elements.py` → `model.py` → `compile.py` → `checks.py`.

## Diagram Types

| Diagram | Elements | GDS Mapping | Canonical |
|---------|----------|-------------|-----------|
| CLD | Variable, CausalLink | All Policy | h = g (stateless) |
| SCN | SupplyNode, Shipment, DemandSource, OrderPolicy | BoundaryAction + Policy + Mechanism/Entity | h = f ∘ g (stateful) |
| VSM | ProcessStep, InventoryBuffer, Supplier, Customer, MaterialFlow, InformationFlow | BoundaryAction + Policy + Mechanism/Entity (if buffers) | h = g or h = f ∘ g |

## Compilation Pattern

- `compile_*(model)` → `GDSSpec` — registers types, spaces, entities, blocks, wirings
- `compile_*_to_system(model)` → `SystemIR` — builds composition tree, delegates to `gds.compiler.compile_system()`

## Verification Checks

- **CLD-001..CLD-003**: Loop polarity, variable reachability, no self-loops
- **SCN-001..SCN-004**: Network connectivity, shipment validity, demand validity, no orphans
- **VSM-001..VSM-004**: Linear flow, push/pull boundary, flow validity, bottleneck vs takt

## Commands

```bash
uv run --package gds-business pytest packages/gds-business/tests -v
uv run ruff check packages/gds-business/
uv run ruff format --check packages/gds-business/
```

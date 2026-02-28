# API Reference

Complete API documentation for `gds-business`, auto-generated from source docstrings.

## Common

| Module | Description |
|--------|-------------|
| [gds_business](init.md) | Package root — version, top-level imports |
| [gds_business.common](common.md) | Shared types, errors, compilation utilities |

## Causal Loop Diagrams

| Module | Description |
|--------|-------------|
| [gds_business.cld.elements](cld-elements.md) | Variable, CausalLink declarations |
| [gds_business.cld.model](cld-model.md) | CausalLoopModel container |
| [gds_business.cld.compile](cld-compile.md) | CLD → GDSSpec / SystemIR compiler |
| [gds_business.cld.checks](cld-checks.md) | CLD-001..CLD-003 verification checks |

## Supply Chain Networks

| Module | Description |
|--------|-------------|
| [gds_business.supplychain.elements](scn-elements.md) | SupplyNode, Shipment, DemandSource, OrderPolicy |
| [gds_business.supplychain.model](scn-model.md) | SupplyChainModel container |
| [gds_business.supplychain.compile](scn-compile.md) | SCN → GDSSpec / SystemIR compiler |
| [gds_business.supplychain.checks](scn-checks.md) | SCN-001..SCN-004 verification checks |

## Value Stream Maps

| Module | Description |
|--------|-------------|
| [gds_business.vsm.elements](vsm-elements.md) | ProcessStep, InventoryBuffer, Supplier, Customer, flows |
| [gds_business.vsm.model](vsm-model.md) | ValueStreamModel container |
| [gds_business.vsm.compile](vsm-compile.md) | VSM → GDSSpec / SystemIR compiler |
| [gds_business.vsm.checks](vsm-checks.md) | VSM-001..VSM-004 verification checks |

## Verification

| Module | Description |
|--------|-------------|
| [gds_business.verification](verification.md) | Union dispatch verify() engine |

# API Reference

Complete API documentation for `gds-domains` (business), auto-generated from source docstrings.

## Common

| Module | Description |
|--------|-------------|
| [gds_domains.business](init.md) | Package root — version, top-level imports |
| [gds_domains.business.common](common.md) | Shared types, errors, compilation utilities |

## Causal Loop Diagrams

| Module | Description |
|--------|-------------|
| [gds_domains.business.cld.elements](cld-elements.md) | Variable, CausalLink declarations |
| [gds_domains.business.cld.model](cld-model.md) | CausalLoopModel container |
| [gds_domains.business.cld.compile](cld-compile.md) | CLD → GDSSpec / SystemIR compiler |
| [gds_domains.business.cld.checks](cld-checks.md) | CLD-001..CLD-003 verification checks |

## Supply Chain Networks

| Module | Description |
|--------|-------------|
| [gds_domains.business.supplychain.elements](scn-elements.md) | SupplyNode, Shipment, DemandSource, OrderPolicy |
| [gds_domains.business.supplychain.model](scn-model.md) | SupplyChainModel container |
| [gds_domains.business.supplychain.compile](scn-compile.md) | SCN → GDSSpec / SystemIR compiler |
| [gds_domains.business.supplychain.checks](scn-checks.md) | SCN-001..SCN-004 verification checks |

## Value Stream Maps

| Module | Description |
|--------|-------------|
| [gds_domains.business.vsm.elements](vsm-elements.md) | ProcessStep, InventoryBuffer, Supplier, Customer, flows |
| [gds_domains.business.vsm.model](vsm-model.md) | ValueStreamModel container |
| [gds_domains.business.vsm.compile](vsm-compile.md) | VSM → GDSSpec / SystemIR compiler |
| [gds_domains.business.vsm.checks](vsm-checks.md) | VSM-001..VSM-004 verification checks |

## Verification

| Module | Description |
|--------|-------------|
| [gds_domains.business.verification](verification.md) | Union dispatch verify() engine |

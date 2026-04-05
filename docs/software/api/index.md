# API Reference

Complete API documentation for `gds-domains` (software), auto-generated from source docstrings.

## Common

| Module | Description |
|--------|-------------|
| [gds_domains.software](init.md) | Package root -- version, top-level imports |
| [gds_domains.software.common](common.md) | Shared types, errors, compilation utilities |

## Data Flow Diagrams

| Module | Description |
|--------|-------------|
| [gds_domains.software.dfd.elements](dfd-elements.md) | ExternalEntity, Process, DataStore, DataFlow declarations |
| [gds_domains.software.dfd.model](dfd-model.md) | DFDModel container |
| [gds_domains.software.dfd.compile](dfd-compile.md) | DFD -> GDSSpec / SystemIR compiler |
| [gds_domains.software.dfd.checks](dfd-checks.md) | DFD-001..DFD-005 verification checks |

## State Machines

| Module | Description |
|--------|-------------|
| [gds_domains.software.statemachine.elements](sm-elements.md) | State, Event, Transition, Guard, Region |
| [gds_domains.software.statemachine.model](sm-model.md) | StateMachineModel container |
| [gds_domains.software.statemachine.compile](sm-compile.md) | SM -> GDSSpec / SystemIR compiler |
| [gds_domains.software.statemachine.checks](sm-checks.md) | SM-001..SM-006 verification checks |

## Component Diagrams

| Module | Description |
|--------|-------------|
| [gds_domains.software.component.elements](cp-elements.md) | Component, InterfaceDef, Connector |
| [gds_domains.software.component.model](cp-model.md) | ComponentModel container |
| [gds_domains.software.component.compile](cp-compile.md) | Component -> GDSSpec / SystemIR compiler |
| [gds_domains.software.component.checks](cp-checks.md) | CP-001..CP-004 verification checks |

## C4 Models

| Module | Description |
|--------|-------------|
| [gds_domains.software.c4.elements](c4-elements.md) | Person, ExternalSystem, Container, C4Component, C4Relationship |
| [gds_domains.software.c4.model](c4-model.md) | C4Model container |
| [gds_domains.software.c4.compile](c4-compile.md) | C4 -> GDSSpec / SystemIR compiler |
| [gds_domains.software.c4.checks](c4-checks.md) | C4-001..C4-004 verification checks |

## Entity-Relationship Diagrams

| Module | Description |
|--------|-------------|
| [gds_domains.software.erd.elements](erd-elements.md) | ERDEntity, Attribute, ERDRelationship, Cardinality |
| [gds_domains.software.erd.model](erd-model.md) | ERDModel container |
| [gds_domains.software.erd.compile](erd-compile.md) | ERD -> GDSSpec / SystemIR compiler |
| [gds_domains.software.erd.checks](erd-checks.md) | ER-001..ER-004 verification checks |

## Dependency Graphs

| Module | Description |
|--------|-------------|
| [gds_domains.software.dependency.elements](dep-elements.md) | Module, Dep, Layer |
| [gds_domains.software.dependency.model](dep-model.md) | DependencyModel container |
| [gds_domains.software.dependency.compile](dep-compile.md) | Dependency -> GDSSpec / SystemIR compiler |
| [gds_domains.software.dependency.checks](dep-checks.md) | DG-001..DG-004 verification checks |

## Verification

| Module | Description |
|--------|-------------|
| [gds_domains.software.verification](verification.md) | Union dispatch verify() engine |

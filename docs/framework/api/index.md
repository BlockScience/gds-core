# API Reference

Complete API documentation for `gds-framework`, auto-generated from source docstrings.

## Core

| Module | Description |
|---|---|
| [gds](init.md) | Package root — version, top-level imports |
| [gds.spec](spec.md) | `GDSSpec` central registry |
| [gds.canonical](canonical.md) | Canonical `h = f . g` decomposition |

## Blocks & Composition

| Module | Description |
|---|---|
| [gds.blocks](blocks.md) | `AtomicBlock`, roles, composition operators |
| [gds.compiler](compiler.md) | 3-stage compiler: flatten, wire, hierarchy |
| [gds.ir](ir.md) | `SystemIR`, `BlockIR`, `WiringIR`, `HierarchyNodeIR` |

## Type System

| Module | Description |
|---|---|
| [gds.types](types.md) | `TypeDef`, token utilities, port helpers |
| [gds.spaces](spaces.md) | `Space`, `EMPTY`, `TERMINAL` |
| [gds.state](state.md) | `Entity`, `StateVariable` |

## Verification & Query

| Module | Description |
|---|---|
| [gds.verification](verification.md) | Generic checks (G-001..G-006), semantic checks (SC-001..SC-007) |
| [gds.query](query.md) | Structural queries on specs and IR |
| [gds.parameters](parameters.md) | `ParameterDef` — structural metadata |

## Utilities

| Module | Description |
|---|---|
| [gds.serialize](serialize.md) | Serialization support |

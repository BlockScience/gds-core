# Verification

`gds-software` provides 27 domain-specific verification checks across six diagram types, plus access to the 6 GDS generic checks (G-001..G-006) via the unified `verify()` function.

## Using verify()

The `verify()` function auto-dispatches to the correct domain checks based on model type:

```python
from gds_software import verify

report = verify(model)                          # Domain + GDS checks
report = verify(model, include_gds_checks=False)  # Domain checks only
```

The returned `VerificationReport` contains a list of `Finding` objects with:

- `check_id` -- e.g., "DFD-001", "SM-003", "G-003"
- `severity` -- ERROR, WARNING, or INFO
- `message` -- human-readable description
- `passed` -- whether the check passed
- `source_elements` -- elements involved

## DFD Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| DFD-001 | Process connectivity | WARNING | Every process has >= 1 incoming and >= 1 outgoing flow |
| DFD-002 | Flow validity | ERROR | Flow source/target reference declared elements |
| DFD-003 | No external-to-external | ERROR | No direct flow between two external entities |
| DFD-004 | Store connectivity | WARNING | Every data store has >= 1 connected flow |
| DFD-005 | Process output | ERROR | Every process has at least one outgoing flow |

## State Machine Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| SM-001 | Initial state | ERROR | Exactly one initial state exists (per region) |
| SM-002 | Reachability | WARNING | All states reachable from initial state via transitions |
| SM-003 | Determinism | WARNING | No two transitions from the same state on the same event (without distinct guards) |
| SM-004 | Guard completeness | INFO | For guarded transitions, checks if guards cover all cases |
| SM-005 | Region partition | ERROR | If regions declared, every state belongs to exactly one region |
| SM-006 | Transition validity | ERROR | Transition source/target/event reference declared elements |

## Component Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| CP-001 | Interface satisfaction | WARNING | Every required interface is satisfied by some component's provided interface |
| CP-002 | Connector validity | ERROR | Connector source/target reference declared components |
| CP-003 | Dangling interfaces | WARNING | Every declared interface is referenced by at least one component |
| CP-004 | Component naming | ERROR | No duplicate component names |

## C4 Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| C4-001 | Relationship validity | ERROR | Relationship source/target reference declared elements |
| C4-002 | Container hierarchy | WARNING | Components reference valid parent containers |
| C4-003 | External connectivity | WARNING | Every external system has >= 1 relationship |
| C4-004 | Level consistency | WARNING | Relationships connect elements at appropriate C4 levels |

## ERD Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| ER-001 | Relationship validity | ERROR | Relationship source/target reference declared entities |
| ER-002 | Primary key existence | WARNING | Every entity has at least one PK attribute |
| ER-003 | Attribute uniqueness | ERROR | No duplicate attribute names within an entity |
| ER-004 | Relationship naming | ERROR | No duplicate relationship names |

## Dependency Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| DG-001 | Dependency validity | ERROR | Dep source/target reference declared modules |
| DG-002 | Acyclicity | ERROR | No circular dependencies in the module graph |
| DG-003 | Layer ordering | WARNING | Dependencies respect layer ordering (higher layers depend on lower) |
| DG-004 | Module connectivity | WARNING | Every module is part of at least one dependency |

## GDS Generic Checks

When `include_gds_checks=True` (default), the model is compiled to `SystemIR` and the 6 GDS generic checks run:

| ID | Name | What it checks |
|----|------|----------------|
| G-001 | Domain/codomain compatibility | Wiring type tokens match |
| G-002 | Signature completeness | Every block has inputs and outputs |
| G-003 | Unique block naming | No duplicate block names |
| G-004 | Wiring source existence | Wired blocks exist |
| G-005 | Wiring target existence | Wired blocks exist |
| G-006 | Hierarchy consistency | Block tree is well-formed |

!!! note
    G-002 will flag `BoundaryAction` blocks (ExternalEntity, Person, Event) as having "no inputs" -- this is expected since they are exogenous sources by design.

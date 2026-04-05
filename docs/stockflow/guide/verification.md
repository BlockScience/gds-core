# Verification

`gds-stockflow` provides 5 domain-specific verification checks, plus access to the 6 GDS generic checks (G-001..G-006) via the unified `verify()` function.

## Using verify()

The `verify()` function runs domain checks on the stock-flow model:

```python
from gds_domains.stockflow import verify

report = verify(model)                          # Domain checks only
report = verify(model, include_gds_checks=True) # Domain + GDS checks
```

The returned `VerificationReport` contains a list of `Finding` objects with:

- `check_id` -- e.g., "SF-001", "G-003"
- `severity` -- ERROR, WARNING, or INFO
- `message` -- human-readable description
- `passed` -- whether the check passed
- `source_elements` -- elements involved

## Domain Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| SF-001 | Orphan stocks | WARNING | Every stock has >= 1 connected flow |
| SF-002 | Flow-stock validity | ERROR | Flow source/target reference declared stocks |
| SF-003 | Auxiliary acyclicity | ERROR | No cycles in auxiliary dependency graph |
| SF-004 | Converter connectivity | WARNING | Every converter referenced by >= 1 auxiliary |
| SF-005 | Flow completeness | ERROR | Every flow has at least one of source or target |

### SF-001: Orphan Stocks

Stocks not connected to any flow are flagged -- they accumulate nothing:

```
[SF-001] WARNING: Stock 'Unused' has no connected flows
```

### SF-002: Flow-Stock Validity

Flow source and target must reference declared stock names:

```
[SF-002] ERROR: Flow 'Transfer' references undeclared stock 'Missing'
```

### SF-003: Auxiliary Acyclicity

Auxiliaries form a dependency graph. Cycles would create infinite recursion:

```
[SF-003] ERROR: Cycle detected in auxiliary dependencies: A -> B -> A
```

### SF-004: Converter Connectivity

Converters not referenced by any auxiliary are flagged as unused:

```
[SF-004] WARNING: Converter 'Unused Param' is not referenced by any auxiliary
```

### SF-005: Flow Completeness

Every flow must have at least one of `source` or `target`:

```
[SF-005] ERROR: Flow 'Broken' has neither source nor target
```

## GDS Generic Checks

When `include_gds_checks=True`, the model is compiled to `SystemIR` and the 6 GDS generic checks run:

| ID | Name | What it checks |
|----|------|----------------|
| G-001 | Domain/codomain compatibility | Wiring type tokens match |
| G-002 | Signature completeness | Every block has inputs and outputs |
| G-003 | Unique block naming | No duplicate block names |
| G-004 | Wiring source existence | Wired blocks exist |
| G-005 | Wiring target existence | Wired blocks exist |
| G-006 | Hierarchy consistency | Block tree is well-formed |

!!! note
    G-002 will flag `BoundaryAction` blocks (Converters) as having "no inputs" -- this is expected since they are exogenous sources by design.

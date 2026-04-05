# Verification

`gds-control` provides 6 domain-specific verification checks, plus access to the 6 GDS generic checks (G-001..G-006) via the unified `verify()` function.

## Using verify()

The `verify()` function runs domain checks on the control model:

```python
from gds_domains.control import verify

report = verify(model)                          # Domain checks only
report = verify(model, include_gds_checks=True) # Domain + GDS checks
```

The returned `VerificationReport` contains a list of `Finding` objects with:

- `check_id` -- e.g., "CS-001", "G-003"
- `severity` -- ERROR, WARNING, or INFO
- `message` -- human-readable description
- `passed` -- whether the check passed
- `source_elements` -- elements involved

## Domain Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| CS-001 | Undriven states | WARNING | Every state driven by >= 1 controller |
| CS-002 | Unobserved states | WARNING | Every state observed by >= 1 sensor |
| CS-003 | Unused inputs | WARNING | Every input read by >= 1 controller |
| CS-004 | Controller read validity | ERROR | Controller `reads` reference declared sensors/inputs |
| CS-005 | Controller drive validity | ERROR | Controller `drives` reference declared states |
| CS-006 | Sensor observe validity | ERROR | Sensor `observes` reference declared states |

### CS-001: Undriven States

States not driven by any controller cannot be actuated:

```
[CS-001] WARNING: State 'pressure' is NOT driven by any controller
```

### CS-002: Unobserved States

States not observed by any sensor are invisible to the control loop:

```
[CS-002] WARNING: State 'pressure' is NOT observed by any sensor
```

### CS-003: Unused Inputs

Inputs not read by any controller have no effect on the system:

```
[CS-003] WARNING: Input 'disturbance' is NOT read by any controller
```

### CS-004: Controller Read Validity

Controllers must reference declared sensors or inputs in their `reads` list:

```
[CS-004] ERROR: Controller 'PID' reads 'missing_sensor' which is NOT a declared sensor or input
```

### CS-005: Controller Drive Validity

Controllers must reference declared states in their `drives` list:

```
[CS-005] ERROR: Controller 'PID' drives 'missing_state' which is NOT a declared state
```

### CS-006: Sensor Observe Validity

Sensors must reference declared states in their `observes` list:

```
[CS-006] ERROR: Sensor 'probe' observes 'missing_state' which is NOT a declared state
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
    G-002 will flag `BoundaryAction` blocks (Inputs) as having "no inputs" -- this is expected since they are exogenous sources by design.

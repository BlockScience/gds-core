# Verification

## Running Verification

```python
from ogs import compile_to_ir, verify

ir = compile_to_ir(pattern)
report = verify(ir)

print(f"{report.checks_passed}/{report.checks_total} checks passed")
for finding in report.findings:
    print(f"  [{finding.severity.value}] {finding.check_id}: {finding.message}")
```

## Type Checks (T-001..T-006)

| Check | Name | What It Validates |
|---|---|---|
| T-001 | Sequential type match | y tokens of left game overlap x tokens of right |
| T-002 | Feedback type match | Backward port tokens match across feedback |
| T-003 | Corecursive type match | Cross-timestep port compatibility |
| T-004 | Signature completeness | All required ports are present |
| T-005 | Port uniqueness | No duplicate port names |
| T-006 | Token consistency | Port token sets are well-formed |

## Structural Checks (S-001..S-007)

| Check | Name | What It Validates |
|---|---|---|
| S-001 | Pattern completeness | All games are connected |
| S-002 | Flow consistency | Flows match declared composition type |
| S-003 | Hierarchy validity | Composition tree is well-formed |
| S-004 | Terminal conditions | Terminal games are properly placed |
| S-005 | Cycle detection | No unintended cycles (only feedback/corecursive) |
| S-006 | Metadata consistency | Action spaces reference valid games |
| S-007 | IR integrity | Compiled IR matches source pattern |

## GDS Check Delegation

Include generic GDS checks alongside OGS checks:

```python
report = verify(ir, include_gds_checks=True)
```

This projects the PatternIR to SystemIR and runs G-001..G-006 checks.

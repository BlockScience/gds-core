# Verification

The verification engine runs pluggable checks against compiled `SystemIR`.

## Running Verification

```python
from gds import compile_system, verify

ir = compile_system("My Model", composed_system)
report = verify(ir)

print(f"{report.checks_passed}/{report.checks_total} checks passed")
for finding in report.findings:
    print(f"  [{finding.severity.value}] {finding.check_id}: {finding.message}")
```

## Generic Checks (G-001..G-006)

Validate IR topology — applicable to any model.

| Check | Name | What It Validates |
|---|---|---|
| G-001 | Port token overlap | Sequential wirings have token overlap |
| G-002 | Signature completeness | All ports are connected |
| G-003 | Wiring validity | Wiring references exist in the block set |
| G-004 | Hierarchy consistency | Hierarchy tree matches block set |
| G-005 | Token consistency | Port tokens are internally consistent |
| G-006 | Block uniqueness | No duplicate block names |

!!! note "G-002 and BoundaryActions"
    G-002 flags BoundaryActions (no inputs) and terminal Mechanisms (no outputs) as warnings. This is expected for valid GDS models — these blocks are system boundaries by design.

## Semantic Checks (SC-001..SC-007)

Validate `GDSSpec` properties — domain-aware checks.

| Check | Name | What It Validates |
|---|---|---|
| SC-001 | Completeness | Every entity variable is updated by some Mechanism |
| SC-002 | Determinism | No entity variable is updated by multiple Mechanisms |
| SC-003 | Reachability | All blocks are reachable from boundary blocks |
| SC-004 | Type safety | Wire spaces match block port types |
| SC-005 | Parameter references | Block `params_used` match registered parameters |
| SC-006 | Canonical wellformedness | Canonical projection produces valid decomposition |
| SC-007 | Reserved | — |

## Custom Checks

Register custom verification checks with the `@gds_check` decorator:

```python
from gds import gds_check, Finding, Severity
from gds.ir.models import SystemIR

@gds_check
def check_no_orphan_blocks(system: SystemIR) -> list[Finding]:
    """Flag blocks with no wirings."""
    wired = {w.source_block for w in system.wirings} | {w.target_block for w in system.wirings}
    return [
        Finding(
            check_id="CUSTOM-001",
            severity=Severity.WARNING,
            message=f"Block '{b.name}' has no wirings",
        )
        for b in system.blocks if b.name not in wired
    ]
```

## Severity Levels

| Level | Meaning |
|---|---|
| `ERROR` | Structural violation — model is invalid |
| `WARNING` | Suspicious pattern — may be intentional |
| `INFO` | Informational — no action needed |

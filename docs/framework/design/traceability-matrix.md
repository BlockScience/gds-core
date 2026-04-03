# Verification Check Traceability Matrix

This document maps formal verification requirements (from [Check Specifications](check-specifications.md))
to their test implementations.

## Matrix

| Requirement | Test File | Test Class/Method | Coverage |
|------------|-----------|-------------------|----------|
| G-001 | test_verification.py | TestG001 | Domain/codomain matching pass/fail |
| G-002 | test_verification.py | TestG002 | Signature completeness pass/fail |
| G-003 | test_verification.py | TestG003 | Direction consistency pass/fail |
| G-004 | test_verification.py | TestG004 | Dangling wirings pass/fail |
| G-005 | test_verification.py | TestG005 | Sequential type compatibility pass/fail |
| G-006 | test_verification.py | TestG006 | Covariant acyclicity pass/fail |
| SC-001 | test_spec_checks.py | TestCompleteness | Orphan variable detection |
| SC-002 | test_spec_checks.py | TestDeterminism | Write conflict detection |
| SC-003 | test_spec_checks.py | TestReachability | Signal path queries |
| SC-004 | test_spec_checks.py | TestTypeSafety | Wire-space consistency |
| SC-005 | test_spec_checks.py | TestParameterReferences | Parameter resolution pass/fail |
| SC-006 | test_spec_checks.py | TestCanonicalWellformedness | Non-empty f (mechanism exists) |
| SC-007 | test_spec_checks.py | TestCanonicalWellformedness | Non-empty X (entity exists) |
| SC-008 | test_spec_checks.py | TestAdmissibilityReferences | Constraint reference validation |
| SC-009 | test_spec_checks.py | TestTransitionReads | Transition signature validation |

## Running Requirement-Traced Tests

```bash
# Run all requirement-traced tests
uv run --package gds-framework pytest packages/gds-framework/tests -v -m "requirement"

# Run tests for a specific requirement
uv run --package gds-framework pytest packages/gds-framework/tests -v -m "requirement('G-006')"
```

## Coverage Gaps

As of this document's creation, all 15 core checks have at least one positive and one negative test case.
Domain-specific checks (CS-xxx, SF-xxx, T-xxx, S-xxx, etc.) are tested in their respective packages
but are not yet covered by this traceability matrix.

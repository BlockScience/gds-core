"""Verification and analysis showcase -- step-by-step demonstration.

Walks through the GDS verification system by building broken models,
running checks, inspecting findings, fixing errors, and re-verifying.

Concepts Covered:
    - VerificationReport structure (findings, severity, check IDs)
    - Generic checks (G-001..G-006) on SystemIR
    - Semantic checks (SC-001..SC-007) on GDSSpec
    - The fix-and-re-verify workflow

Prerequisites: Read sir_epidemic/model.py for GDS fundamentals.

How to read this file:
    Each function is a self-contained demonstration. They are called
    by the test suite but can also be studied as documentation.
"""

from gds.verification.engine import verify
from gds.verification.findings import Severity, VerificationReport
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
)
from guides.verification.broken_models import (
    covariant_cycle_system,
    dangling_wiring_system,
    empty_canonical_spec,
    fixed_pipeline_system,
    fixed_spec,
    orphan_state_spec,
    type_mismatch_system,
    write_conflict_spec,
)

# ══════════════════════════════════════════════════════════════════
# Part 1: Generic checks on SystemIR
# ══════════════════════════════════════════════════════════════════


def demo_dangling_wiring() -> VerificationReport:
    """Demonstrate G-004: detecting dangling wirings.

    A wiring references block 'Ghost' which does not exist. The
    verification engine flags this as an ERROR finding.

    Returns:
        VerificationReport with at least one G-004 failure.
    """
    system = dangling_wiring_system()

    # Run only the G-004 check
    report = verify(system, checks=[check_g004_dangling_wirings])

    # Inspect findings
    assert report.system_name == "Dangling Wiring Demo"
    assert report.errors >= 1

    # Find the specific failing finding
    failures = [f for f in report.findings if not f.passed]
    assert any(f.check_id == "G-004" for f in failures)
    assert any("Ghost" in f.message for f in failures)

    return report


def demo_type_mismatch() -> VerificationReport:
    """Demonstrate G-001 and G-005: detecting type mismatches.

    Block A outputs 'Temperature' but Block B expects 'Pressure'.
    The wiring label 'humidity' matches neither side.

    Returns:
        VerificationReport with G-001 and G-005 failures.
    """
    system = type_mismatch_system()

    report = verify(
        system,
        checks=[
            check_g001_domain_codomain_matching,
            check_g005_sequential_type_compatibility,
        ],
    )

    # Both checks should flag the mismatch
    g001_failures = [
        f for f in report.findings if f.check_id == "G-001" and not f.passed
    ]
    g005_failures = [
        f for f in report.findings if f.check_id == "G-005" and not f.passed
    ]
    assert len(g001_failures) >= 1
    assert len(g005_failures) >= 1

    return report


def demo_covariant_cycle() -> VerificationReport:
    """Demonstrate G-006: detecting algebraic loops.

    Three blocks form a cycle: A -> B -> C -> A, all covariant and
    non-temporal. This is an algebraic loop that cannot be resolved
    within a single timestep.

    Returns:
        VerificationReport with a G-006 failure.
    """
    system = covariant_cycle_system()

    report = verify(system, checks=[check_g006_covariant_acyclicity])

    failures = [f for f in report.findings if not f.passed]
    assert len(failures) >= 1
    assert failures[0].check_id == "G-006"
    assert "cycle" in failures[0].message.lower()

    return report


def demo_full_verification_broken() -> VerificationReport:
    """Run all generic checks on a broken system, showing multiple errors.

    The type-mismatch system triggers failures in G-001 and G-005,
    while G-004 and G-006 pass (wirings reference real blocks, no cycles).

    Returns:
        VerificationReport with mixed passed/failed findings.
    """
    system = type_mismatch_system()
    report = verify(system)

    # Report properties
    assert report.checks_total > 0
    assert report.errors >= 1
    assert report.checks_passed >= 1  # G-004, G-006 should pass

    return report


def demo_fix_and_reverify() -> tuple[VerificationReport, VerificationReport]:
    """Fix-and-re-verify workflow: broken model -> fix -> clean report.

    First verifies a broken system (dangling wiring), then verifies
    the fixed version and confirms all checks pass.

    Returns:
        Tuple of (broken_report, fixed_report).
    """
    # Step 1: Verify broken model
    broken = dangling_wiring_system()
    broken_report = verify(broken)
    assert broken_report.errors >= 1

    # Step 2: Verify fixed model
    fixed = fixed_pipeline_system()
    fixed_report = verify(fixed)

    # All generic checks should pass on the fixed model
    failed = [f for f in fixed_report.findings if not f.passed]
    assert len(failed) == 0, f"Unexpected failures: {failed}"

    return broken_report, fixed_report


# ══════════════════════════════════════════════════════════════════
# Part 2: Semantic checks on GDSSpec
# ══════════════════════════════════════════════════════════════════


def demo_orphan_state() -> list:
    """Demonstrate SC-001: detecting orphan state variables.

    Entity 'Reservoir' has a 'level' variable but no mechanism updates
    it. The completeness check flags this as a WARNING.

    Returns:
        List of SC-001 findings.
    """
    spec = orphan_state_spec()

    findings = check_completeness(spec)

    failures = [f for f in findings if not f.passed]
    assert len(failures) == 1
    assert failures[0].check_id == "SC-001"
    assert failures[0].severity == Severity.WARNING
    assert "Reservoir.level" in failures[0].message

    return findings


def demo_write_conflict() -> list:
    """Demonstrate SC-002: detecting write conflicts.

    Two mechanisms both update ('Counter', 'value') within the same
    wiring. The determinism check flags this as an ERROR.

    Returns:
        List of SC-002 findings.
    """
    spec = write_conflict_spec()

    findings = check_determinism(spec)

    failures = [f for f in findings if not f.passed]
    assert len(failures) >= 1
    assert failures[0].check_id == "SC-002"
    assert failures[0].severity == Severity.ERROR

    return findings


def demo_empty_canonical() -> list:
    """Demonstrate SC-006 and SC-007: detecting empty canonical form.

    A spec with no mechanisms and no entities has an empty state
    transition f and empty state space X. Both canonical wellformedness
    checks fail.

    Returns:
        List of SC-006 and SC-007 findings.
    """
    spec = empty_canonical_spec()

    findings = check_canonical_wellformedness(spec)

    sc006 = [f for f in findings if f.check_id == "SC-006"]
    sc007 = [f for f in findings if f.check_id == "SC-007"]
    assert len(sc006) == 1 and not sc006[0].passed
    assert len(sc007) == 1 and not sc007[0].passed

    return findings


def demo_generic_vs_semantic() -> dict:
    """Compare generic and semantic verification on the same model.

    Generic checks (G-series) operate on the compiled SystemIR and
    verify structural topology. Semantic checks (SC-series) operate
    on the GDSSpec and verify domain properties like completeness
    and determinism.

    This demonstrates that both check families are complementary:
    a model can pass all generic checks but fail semantic checks
    (and vice versa).

    Returns:
        Dict with 'generic' and 'semantic' VerificationReports.
    """
    # Build a spec that is structurally sound but semantically flawed:
    # the orphan state spec has no mechanisms, so canonical checks fail,
    # but a compiled SystemIR from a simple pipeline passes G-checks.
    spec = fixed_spec()

    # Semantic checks on the spec
    sc_completeness = check_completeness(spec)
    sc_determinism = check_determinism(spec)
    sc_canonical = check_canonical_wellformedness(spec)
    semantic_findings = sc_completeness + sc_determinism + sc_canonical

    # All semantic checks should pass on the fixed spec
    semantic_failures = [f for f in semantic_findings if not f.passed]
    assert len(semantic_failures) == 0

    # Generic checks on a clean pipeline system
    system = fixed_pipeline_system()
    generic_report = verify(system)
    generic_failures = [f for f in generic_report.findings if not f.passed]
    assert len(generic_failures) == 0

    semantic_report = VerificationReport(
        system_name=spec.name,
        findings=semantic_findings,
    )

    return {
        "generic": generic_report,
        "semantic": semantic_report,
    }

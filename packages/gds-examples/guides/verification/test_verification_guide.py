"""Tests for the verification and analysis showcase.

Verifies that:
    - Each broken model produces expected findings
    - Fixed models pass verification
    - Specific check IDs are triggered by specific errors
    - Domain checks complement generic checks
"""

from gds.verification.engine import verify
from gds.verification.findings import Severity
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g002_signature_completeness,
    check_g003_direction_consistency,
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
    direction_contradiction_system,
    empty_canonical_spec,
    fixed_pipeline_system,
    fixed_spec,
    incomplete_signature_system,
    orphan_state_spec,
    type_mismatch_system,
    write_conflict_spec,
)
from guides.verification.domain_checks_demo import (
    cyclic_auxiliary_model,
    demo_broken_domain_full_verification,
    demo_cyclic_auxiliaries,
    demo_domain_plus_gds_checks,
    demo_orphan_stock,
    demo_unused_converter,
    good_stockflow_model,
    orphan_stock_model,
    unused_converter_model,
)
from guides.verification.verification_demo import (
    demo_covariant_cycle,
    demo_dangling_wiring,
    demo_empty_canonical,
    demo_fix_and_reverify,
    demo_full_verification_broken,
    demo_generic_vs_semantic,
    demo_orphan_state,
    demo_type_mismatch,
    demo_write_conflict,
)
from stockflow.verification.checks import (
    check_sf001_orphan_stocks,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
)
from stockflow.verification.engine import verify as sf_verify

# ══════════════════════════════════════════════════════════════════
# Generic check tests (G-001..G-006 on SystemIR)
# ══════════════════════════════════════════════════════════════════


class TestG004DanglingWirings:
    """Verify that dangling wiring references are detected."""

    def test_dangling_source_detected(self):
        system = dangling_wiring_system()
        findings = check_g004_dangling_wirings(system)
        failures = [f for f in findings if not f.passed]
        assert len(failures) >= 1
        assert any("Ghost" in f.message for f in failures)

    def test_demo_returns_report(self):
        report = demo_dangling_wiring()
        assert report.system_name == "Dangling Wiring Demo"
        assert report.errors >= 1


class TestG001G005TypeMismatch:
    """Verify that type mismatches between ports are detected."""

    def test_g001_mismatch_detected(self):
        system = type_mismatch_system()
        findings = check_g001_domain_codomain_matching(system)
        failures = [f for f in findings if not f.passed]
        assert len(failures) >= 1
        assert failures[0].check_id == "G-001"

    def test_g005_mismatch_detected(self):
        system = type_mismatch_system()
        findings = check_g005_sequential_type_compatibility(system)
        failures = [f for f in findings if not f.passed]
        assert len(failures) >= 1
        assert failures[0].check_id == "G-005"

    def test_demo_returns_report(self):
        report = demo_type_mismatch()
        assert report.errors >= 2


class TestG006CovariantCycle:
    """Verify that covariant cycles are detected."""

    def test_cycle_detected(self):
        system = covariant_cycle_system()
        findings = check_g006_covariant_acyclicity(system)
        failures = [f for f in findings if not f.passed]
        assert len(failures) >= 1
        assert "cycle" in failures[0].message.lower()

    def test_demo_returns_report(self):
        report = demo_covariant_cycle()
        assert report.errors >= 1


class TestG003DirectionContradiction:
    """Verify that direction flag contradictions are detected."""

    def test_covariant_feedback_contradiction(self):
        system = direction_contradiction_system()
        findings = check_g003_direction_consistency(system)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 1
        assert "contradiction" in failures[0].message.lower()
        assert failures[0].check_id == "G-003"


class TestG002IncompleteSignature:
    """Verify that blocks with empty signatures are detected."""

    def test_orphan_block_detected(self):
        system = incomplete_signature_system()
        findings = check_g002_signature_completeness(system)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert any("Orphan" in f.message for f in failed)


# ══════════════════════════════════════════════════════════════════
# Fixed model tests
# ══════════════════════════════════════════════════════════════════


class TestFixedModels:
    """Verify that fixed/repaired models pass all checks."""

    def test_fixed_pipeline_passes_all_generic(self):
        system = fixed_pipeline_system()
        report = verify(system)
        failures = [f for f in report.findings if not f.passed]
        assert len(failures) == 0

    def test_fixed_spec_passes_completeness(self):
        spec = fixed_spec()
        findings = check_completeness(spec)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 0

    def test_fixed_spec_passes_determinism(self):
        spec = fixed_spec()
        findings = check_determinism(spec)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 0

    def test_fixed_spec_passes_canonical(self):
        spec = fixed_spec()
        findings = check_canonical_wellformedness(spec)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 0

    def test_fix_and_reverify_workflow(self):
        broken_report, fixed_report = demo_fix_and_reverify()
        assert broken_report.errors >= 1
        assert fixed_report.errors == 0


# ══════════════════════════════════════════════════════════════════
# Semantic check tests (SC-001..SC-007 on GDSSpec)
# ══════════════════════════════════════════════════════════════════


class TestSC001OrphanState:
    """Verify that orphan state variables are detected."""

    def test_orphan_detected(self):
        spec = orphan_state_spec()
        findings = check_completeness(spec)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 1
        assert failures[0].check_id == "SC-001"
        assert failures[0].severity == Severity.WARNING

    def test_demo_returns_findings(self):
        findings = demo_orphan_state()
        assert any(f.check_id == "SC-001" for f in findings)


class TestSC002WriteConflict:
    """Verify that write conflicts are detected."""

    def test_conflict_detected(self):
        spec = write_conflict_spec()
        findings = check_determinism(spec)
        failures = [f for f in findings if not f.passed]
        assert len(failures) >= 1
        assert failures[0].check_id == "SC-002"
        assert failures[0].severity == Severity.ERROR

    def test_demo_returns_findings(self):
        findings = demo_write_conflict()
        assert any(f.check_id == "SC-002" for f in findings)


class TestSC006SC007EmptyCanonical:
    """Verify that empty canonical form is detected."""

    def test_no_mechanisms_detected(self):
        spec = empty_canonical_spec()
        findings = check_canonical_wellformedness(spec)
        sc006 = [f for f in findings if f.check_id == "SC-006"]
        assert len(sc006) == 1
        assert not sc006[0].passed

    def test_no_state_detected(self):
        spec = empty_canonical_spec()
        findings = check_canonical_wellformedness(spec)
        sc007 = [f for f in findings if f.check_id == "SC-007"]
        assert len(sc007) == 1
        assert not sc007[0].passed

    def test_demo_returns_findings(self):
        findings = demo_empty_canonical()
        check_ids = {f.check_id for f in findings}
        assert "SC-006" in check_ids
        assert "SC-007" in check_ids


# ══════════════════════════════════════════════════════════════════
# Comparison tests
# ══════════════════════════════════════════════════════════════════


class TestGenericVsSemantic:
    """Verify that generic and semantic checks are complementary."""

    def test_full_verification_shows_mixed_results(self):
        report = demo_full_verification_broken()
        assert report.checks_total > 0
        assert report.errors >= 1
        assert report.checks_passed >= 1

    def test_generic_vs_semantic_comparison(self):
        results = demo_generic_vs_semantic()
        generic = results["generic"]
        semantic = results["semantic"]

        # Both should have findings
        assert generic.checks_total > 0
        assert semantic.checks_total > 0

        # Both should pass on the fixed models
        assert generic.errors == 0
        assert semantic.errors == 0


# ══════════════════════════════════════════════════════════════════
# Domain-specific check tests (SF-001..SF-005 on StockFlowModel)
# ══════════════════════════════════════════════════════════════════


class TestSF001OrphanStock:
    """Verify that orphan stocks in stock-flow models are detected."""

    def test_orphan_stock_detected(self):
        model = orphan_stock_model()
        findings = check_sf001_orphan_stocks(model)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 1
        assert "Inventory" in failures[0].source_elements

    def test_demo_returns_findings(self):
        findings = demo_orphan_stock()
        assert len(findings) >= 1


class TestSF003AuxiliaryCycle:
    """Verify that auxiliary dependency cycles are detected."""

    def test_cycle_detected(self):
        model = cyclic_auxiliary_model()
        findings = check_sf003_auxiliary_acyclicity(model)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 1
        assert failures[0].check_id == "SF-003"

    def test_demo_returns_findings(self):
        findings = demo_cyclic_auxiliaries()
        assert any(not f.passed for f in findings)


class TestSF004UnusedConverter:
    """Verify that unreferenced converters are detected."""

    def test_unused_converter_detected(self):
        model = unused_converter_model()
        findings = check_sf004_converter_connectivity(model)
        failures = [f for f in findings if not f.passed]
        assert len(failures) == 1
        assert "Tax Rate" in failures[0].source_elements

    def test_demo_returns_findings(self):
        findings = demo_unused_converter()
        assert len(findings) >= 1


class TestDomainPlusGDS:
    """Verify that domain and GDS checks run together."""

    def test_sf_only_has_no_gds(self):
        report = sf_verify(good_stockflow_model(), include_gds_checks=False)
        gds = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds) == 0

    def test_full_has_both(self):
        results = demo_domain_plus_gds_checks()
        sf_only = results["sf_only"]
        full = results["full"]

        sf_ids = {f.check_id for f in sf_only.findings}
        full_ids = {f.check_id for f in full.findings}

        assert any(cid.startswith("SF-") for cid in sf_ids)
        assert any(cid.startswith("SF-") for cid in full_ids)
        assert any(cid.startswith("G-") for cid in full_ids)

    def test_broken_domain_shows_both_layers(self):
        results = demo_broken_domain_full_verification()
        assert results["sf_total"] > 0
        assert results["sf_failures"] >= 1
        assert results["gds_total"] > 0


# ══════════════════════════════════════════════════════════════════
# VerificationReport structure tests
# ══════════════════════════════════════════════════════════════════


class TestVerificationReportStructure:
    """Verify the VerificationReport API works as documented."""

    def test_report_counts_consistent(self):
        system = type_mismatch_system()
        report = verify(system)

        # Total = passed + errors + warnings + info
        assert (
            report.checks_total
            == report.checks_passed
            + report.errors
            + report.warnings
            + report.info_count
        )

    def test_finding_fields(self):
        system = dangling_wiring_system()
        findings = check_g004_dangling_wirings(system)

        for f in findings:
            assert f.check_id  # non-empty
            assert f.severity in (Severity.ERROR, Severity.WARNING, Severity.INFO)
            assert f.message  # non-empty
            assert isinstance(f.passed, bool)
            assert isinstance(f.source_elements, list)

    def test_severity_levels(self):
        # ERROR: dangling wiring
        system = dangling_wiring_system()
        findings = check_g004_dangling_wirings(system)
        failures = [f for f in findings if not f.passed]
        assert failures[0].severity == Severity.ERROR

        # WARNING: orphan state
        spec = orphan_state_spec()
        sc_findings = check_completeness(spec)
        sc_failures = [f for f in sc_findings if not f.passed]
        assert sc_failures[0].severity == Severity.WARNING

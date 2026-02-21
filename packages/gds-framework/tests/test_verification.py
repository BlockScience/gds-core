"""Tests for generic verification checks (G-001 through G-006)."""

from gds.ir.models import BlockIR, FlowDirection, InputIR, SystemIR, WiringIR
from gds.verification.engine import verify
from gds.verification.findings import VerificationReport
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g002_signature_completeness,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)

# ── G-001: Domain/codomain matching ─────────────────────────


class TestG001:
    def test_matching_wiring_passes(self, sample_system_ir):
        findings = check_g001_domain_codomain_matching(sample_system_ir)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_mismatched_wiring_fails(self):
        sys = SystemIR(
            name="Bad",
            blocks=[
                BlockIR(name="A", signature=("", "X", "", "")),
                BlockIR(name="B", signature=("Y", "", "", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="z",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        findings = check_g001_domain_codomain_matching(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1

    def test_contravariant_skipped(self):
        sys = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "", "cost", "")),
                BlockIR(name="B", signature=("", "", "", "cost")),
            ],
            wirings=[
                WiringIR(
                    source="B",
                    target="A",
                    label="cost",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ],
        )
        findings = check_g001_domain_codomain_matching(sys)
        # G-001 only checks covariant wirings, so contravariant is skipped
        assert len(findings) == 0


# ── G-002: Signature completeness ────────────────────────────


class TestG002:
    def test_complete_block_passes(self, sample_system_ir):
        findings = check_g002_signature_completeness(sample_system_ir)
        # Block B has both input and output
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_missing_output_flags(self):
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A", signature=("X", "", "", ""))],
            wirings=[],
        )
        findings = check_g002_signature_completeness(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1


# ── G-003: Direction consistency ─────────────────────────────


class TestG003:
    def test_covariant_wiring_no_findings(self, sample_system_ir):
        """Covariant wirings are handled by G-001 — G-003 skips them."""
        findings = check_g003_direction_consistency(sample_system_ir)
        # sample_system_ir has only covariant wirings, G-003 skips those
        assert all(f.passed for f in findings)

    def test_covariant_feedback_contradiction(self):
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A"), BlockIR(name="B")],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="x",
                    direction=FlowDirection.COVARIANT,
                    is_feedback=True,
                )
            ],
        )
        findings = check_g003_direction_consistency(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "contradiction" in failed[0].message

    def test_contravariant_temporal_contradiction(self):
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A"), BlockIR(name="B")],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="x",
                    direction=FlowDirection.CONTRAVARIANT,
                    is_temporal=True,
                )
            ],
        )
        findings = check_g003_direction_consistency(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "contradiction" in failed[0].message

    def test_contravariant_matching_passes(self):
        sys = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "", "", "Cost")),
                BlockIR(name="B", signature=("", "", "Cost", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="cost",
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                )
            ],
        )
        findings = check_g003_direction_consistency(sys)
        assert all(f.passed for f in findings)

    def test_contravariant_mismatch_fails(self):
        sys = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "", "", "Cost")),
                BlockIR(name="B", signature=("", "", "Reward", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="unrelated",
                    direction=FlowDirection.CONTRAVARIANT,
                    is_feedback=True,
                )
            ],
        )
        findings = check_g003_direction_consistency(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "MISMATCH" in failed[0].message


# ── G-004: Dangling wirings ──────────────────────────────────


class TestG004:
    def test_valid_passes(self, sample_system_ir):
        findings = check_g004_dangling_wirings(sample_system_ir)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_unknown_source_fails(self):
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="B")],
            wirings=[
                WiringIR(
                    source="NonExistent",
                    target="B",
                    label="x",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        findings = check_g004_dangling_wirings(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1

    def test_unknown_target_fails(self):
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="A")],
            wirings=[
                WiringIR(
                    source="A",
                    target="NonExistent",
                    label="x",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        findings = check_g004_dangling_wirings(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1

    def test_input_as_known_source(self):
        """Wiring from an input should not be flagged as dangling."""
        sys = SystemIR(
            name="Test",
            blocks=[BlockIR(name="B")],
            inputs=[InputIR(name="env_signal")],
            wirings=[
                WiringIR(
                    source="env_signal",
                    target="B",
                    label="signal",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        findings = check_g004_dangling_wirings(sys)
        failed = [f for f in findings if not f.passed]
        assert failed == []


# ── G-005: Sequential type compatibility ─────────────────────


class TestG005:
    def test_compatible_passes(self, sample_system_ir):
        findings = check_g005_sequential_type_compatibility(sample_system_ir)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_incompatible_fails(self):
        sys = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "X", "", "")),
                BlockIR(name="B", signature=("Y", "", "", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="z",
                    direction=FlowDirection.COVARIANT,
                )
            ],
        )
        findings = check_g005_sequential_type_compatibility(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1

    def test_temporal_skipped(self):
        sys = SystemIR(
            name="Test",
            blocks=[
                BlockIR(name="A", signature=("", "X", "", "")),
                BlockIR(name="B", signature=("Y", "", "", "")),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="z",
                    direction=FlowDirection.COVARIANT,
                    is_temporal=True,
                )
            ],
        )
        findings = check_g005_sequential_type_compatibility(sys)
        # Temporal wirings should be skipped
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 0


# ── G-006: Covariant acyclicity ──────────────────────────────


class TestG006:
    def test_dag_passes(self, sample_system_ir):
        findings = check_g006_covariant_acyclicity(sample_system_ir)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_cycle_fails(self):
        sys = SystemIR(
            name="Cycle",
            blocks=[
                BlockIR(name="A"),
                BlockIR(name="B"),
            ],
            wirings=[
                WiringIR(
                    source="A",
                    target="B",
                    label="x",
                    direction=FlowDirection.COVARIANT,
                ),
                WiringIR(
                    source="B",
                    target="A",
                    label="y",
                    direction=FlowDirection.COVARIANT,
                ),
            ],
        )
        findings = check_g006_covariant_acyclicity(sys)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1


# ── Verify orchestrator ──────────────────────────────────────


class TestVerifyOrchestrator:
    def test_runs_all_checks(self, sample_system_ir):
        report = verify(sample_system_ir)
        assert isinstance(report, VerificationReport)
        assert report.system_name == "Sample"
        assert report.checks_total > 0

    def test_custom_subset(self, sample_system_ir):
        report = verify(sample_system_ir, checks=[check_g001_domain_codomain_matching])
        assert all(f.check_id == "G-001" for f in report.findings)

    def test_report_counts(self, thermostat_system_ir):
        report = verify(thermostat_system_ir)
        assert (
            report.checks_total
            == report.errors
            + report.warnings
            + report.info_count
            + report.checks_passed
        )

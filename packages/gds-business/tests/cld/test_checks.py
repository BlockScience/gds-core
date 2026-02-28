"""Tests for CLD verification checks."""

from gds.verification.findings import Severity

from gds_business.cld.checks import (
    ALL_CLD_CHECKS,
    check_cld001_loop_polarity,
    check_cld002_variable_reachability,
    check_cld003_no_self_loops,
)
from gds_business.cld.elements import CausalLink, Variable
from gds_business.cld.model import CausalLoopModel


def _reinforcing_loop() -> CausalLoopModel:
    """A -> B -> A, both positive = reinforcing."""
    return CausalLoopModel(
        name="Reinforcing",
        variables=[Variable(name="A"), Variable(name="B")],
        links=[
            CausalLink(source="A", target="B", polarity="+"),
            CausalLink(source="B", target="A", polarity="+"),
        ],
    )


def _balancing_loop() -> CausalLoopModel:
    """A -> B -> A, one negative = balancing."""
    return CausalLoopModel(
        name="Balancing",
        variables=[Variable(name="A"), Variable(name="B")],
        links=[
            CausalLink(source="A", target="B", polarity="+"),
            CausalLink(source="B", target="A", polarity="-"),
        ],
    )


def _no_loop() -> CausalLoopModel:
    """A -> B, no cycle."""
    return CausalLoopModel(
        name="NoLoop",
        variables=[Variable(name="A"), Variable(name="B")],
        links=[CausalLink(source="A", target="B", polarity="+")],
    )


def _isolated_var() -> CausalLoopModel:
    """A -> B, C isolated."""
    return CausalLoopModel(
        name="Isolated",
        variables=[Variable(name="A"), Variable(name="B"), Variable(name="C")],
        links=[CausalLink(source="A", target="B", polarity="+")],
    )


def _no_links() -> CausalLoopModel:
    return CausalLoopModel(
        name="NoLinks",
        variables=[Variable(name="X")],
    )


class TestCLD001LoopPolarity:
    def test_reinforcing_loop(self):
        findings = check_cld001_loop_polarity(_reinforcing_loop())
        loop_findings = [f for f in findings if "Reinforcing" in f.message]
        assert len(loop_findings) >= 1
        assert all(f.severity == Severity.INFO for f in findings)

    def test_balancing_loop(self):
        findings = check_cld001_loop_polarity(_balancing_loop())
        loop_findings = [f for f in findings if "Balancing" in f.message]
        assert len(loop_findings) >= 1

    def test_no_loop_detected(self):
        findings = check_cld001_loop_polarity(_no_loop())
        assert len(findings) == 1
        assert "No feedback loops" in findings[0].message
        assert findings[0].passed is True

    def test_all_findings_pass(self):
        findings = check_cld001_loop_polarity(_reinforcing_loop())
        assert all(f.passed for f in findings)


class TestCLD002VariableReachability:
    def test_all_reachable(self):
        findings = check_cld002_variable_reachability(_reinforcing_loop())
        assert all(f.passed for f in findings)

    def test_isolated_variable(self):
        findings = check_cld002_variable_reachability(_isolated_var())
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "C" in failed[0].source_elements

    def test_no_links_all_unreachable(self):
        findings = check_cld002_variable_reachability(_no_links())
        assert len(findings) == 1
        assert not findings[0].passed

    def test_severity_is_warning(self):
        findings = check_cld002_variable_reachability(_isolated_var())
        assert all(f.severity == Severity.WARNING for f in findings)


class TestCLD003NoSelfLoops:
    def test_no_self_loops(self):
        findings = check_cld003_no_self_loops(_reinforcing_loop())
        assert all(f.passed for f in findings)

    def test_no_links_empty(self):
        findings = check_cld003_no_self_loops(_no_links())
        assert len(findings) == 0


class TestALLCLDChecks:
    def test_all_checks_registered(self):
        assert len(ALL_CLD_CHECKS) == 3

    def test_all_checks_callable(self):
        model = _reinforcing_loop()
        for check in ALL_CLD_CHECKS:
            findings = check(model)
            assert isinstance(findings, list)

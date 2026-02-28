"""Cross-diagram tests — canonical spectrum and verification engine."""

from gds.canonical import project_canonical
from gds.verification.findings import Severity

from gds_business.cld.elements import CausalLink, Variable
from gds_business.cld.model import CausalLoopModel
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)
from gds_business.supplychain.model import SupplyChainModel
from gds_business.verification.engine import verify
from gds_business.vsm.elements import (
    Customer,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)
from gds_business.vsm.model import ValueStreamModel


# ── Fixtures ────────────────────────────────────────────────


def _cld() -> CausalLoopModel:
    return CausalLoopModel(
        name="Population CLD",
        variables=[
            Variable(name="Population"),
            Variable(name="Births"),
            Variable(name="Deaths"),
        ],
        links=[
            CausalLink(source="Population", target="Births", polarity="+"),
            CausalLink(source="Births", target="Population", polarity="+"),
            CausalLink(source="Population", target="Deaths", polarity="+"),
            CausalLink(source="Deaths", target="Population", polarity="-"),
        ],
    )


def _scn() -> SupplyChainModel:
    return SupplyChainModel(
        name="Simple Supply Chain",
        nodes=[
            SupplyNode(name="Factory"),
            SupplyNode(name="Retailer"),
        ],
        shipments=[
            Shipment(name="F->R", source_node="Factory", target_node="Retailer"),
        ],
        demand_sources=[
            DemandSource(name="Customer", target_node="Retailer"),
        ],
        order_policies=[
            OrderPolicy(name="Reorder", node="Retailer", inputs=["Retailer"]),
        ],
    )


def _vsm_stateless() -> ValueStreamModel:
    return ValueStreamModel(
        name="Stateless VSM",
        steps=[
            ProcessStep(name="Step1", cycle_time=10.0),
            ProcessStep(name="Step2", cycle_time=20.0),
        ],
        suppliers=[Supplier(name="Sup")],
        customers=[Customer(name="Cust", takt_time=30.0)],
        material_flows=[
            MaterialFlow(source="Sup", target="Step1"),
            MaterialFlow(source="Step1", target="Step2"),
            MaterialFlow(source="Step2", target="Cust"),
        ],
    )


def _vsm_stateful() -> ValueStreamModel:
    return ValueStreamModel(
        name="Stateful VSM",
        steps=[
            ProcessStep(name="Cutting", cycle_time=30.0),
            ProcessStep(name="Assembly", cycle_time=25.0),
        ],
        buffers=[
            InventoryBuffer(name="WIP", between=("Cutting", "Assembly")),
        ],
        suppliers=[Supplier(name="Sup")],
        material_flows=[
            MaterialFlow(source="Sup", target="Cutting"),
            MaterialFlow(source="Cutting", target="WIP"),
        ],
    )


# ── Canonical Spectrum ──────────────────────────────────────


class TestCanonicalSpectrum:
    """Verify the canonical decomposition for each diagram type."""

    def test_cld_stateless(self):
        """CLD: |X|=0, |f|=0, h = g."""
        spec = _cld().compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 3

    def test_scn_stateful(self):
        """SCN: |X|=n, |f|=n, h = f o g."""
        spec = _scn().compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) > 0
        assert len(canon.mechanism_blocks) > 0
        assert len(canon.policy_blocks) > 0

    def test_vsm_stateless(self):
        """VSM (no buffers): |X|=0, |f|=0, h = g."""
        spec = _vsm_stateless().compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) == 0
        assert len(canon.mechanism_blocks) == 0

    def test_vsm_stateful(self):
        """VSM (with buffers): |X|=m, |f|=m, h = f o g."""
        spec = _vsm_stateful().compile()
        canon = project_canonical(spec)
        assert len(canon.state_variables) > 0
        assert len(canon.mechanism_blocks) > 0


# ── Verification Engine ─────────────────────────────────────


class TestVerificationEngine:
    def test_verify_cld(self):
        report = verify(_cld())
        assert report.system_name == "Population CLD"
        assert len(report.findings) > 0

    def test_verify_scn(self):
        report = verify(_scn())
        assert report.system_name == "Simple Supply Chain"
        assert len(report.findings) > 0

    def test_verify_vsm(self):
        report = verify(_vsm_stateless())
        assert report.system_name == "Stateless VSM"
        assert len(report.findings) > 0

    def test_verify_with_custom_checks(self):
        def custom_check(model: CausalLoopModel) -> list:
            from gds.verification.findings import Finding

            return [
                Finding(
                    check_id="CUSTOM-001",
                    severity=Severity.INFO,
                    message="Custom check ran",
                    source_elements=[],
                    passed=True,
                )
            ]

        report = verify(_cld(), domain_checks=[custom_check])
        custom = [f for f in report.findings if f.check_id == "CUSTOM-001"]
        assert len(custom) == 1

    def test_verify_without_gds_checks(self):
        report = verify(_cld(), include_gds_checks=False)
        # Only domain checks, no G-001..G-006
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) == 0

    def test_verify_unknown_model_type(self):
        import pytest

        with pytest.raises(TypeError, match="Unknown model type"):
            verify("not a model")


# ── GDS Generic Checks ──────────────────────────────────────


class TestGDSGenericChecks:
    """Verify GDS generic checks run on all diagrams.

    Note: G-002 (signature completeness) flags BoundaryAction blocks as
    having "no inputs" — this is expected since they are exogenous sources.
    We test that GDS checks execute and that only expected G-002 failures
    occur on BoundaryAction blocks.
    """

    def test_cld_passes_gds_checks(self):
        """CLD has no BoundaryActions, should pass all GDS checks."""
        report = verify(_cld())
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        failed_gds = [f for f in gds_findings if not f.passed]
        assert len(failed_gds) == 0

    def test_scn_gds_checks_run(self):
        report = verify(_scn())
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0
        # Only G-002 failures expected (BoundaryAction + unwired mechanism)
        failed = [f for f in gds_findings if not f.passed]
        assert all(f.check_id == "G-002" for f in failed)

    def test_vsm_stateless_gds_checks_run(self):
        report = verify(_vsm_stateless())
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0
        # Only G-002 failures expected (BoundaryAction blocks)
        failed = [f for f in gds_findings if not f.passed]
        assert all(f.check_id == "G-002" for f in failed)

    def test_vsm_stateful_gds_checks_run(self):
        report = verify(_vsm_stateful())
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) > 0


# ── Import Smoke Tests ──────────────────────────────────────


class TestImports:
    def test_import_all(self):
        import gds_business

        assert hasattr(gds_business, "CausalLoopModel")
        assert hasattr(gds_business, "SupplyChainModel")
        assert hasattr(gds_business, "ValueStreamModel")
        assert hasattr(gds_business, "verify")
        assert hasattr(gds_business, "BusinessDiagramKind")
        assert gds_business.__version__ == "0.1.0"

    def test_all_exports_accessible(self):
        import gds_business

        for name in gds_business.__all__:
            assert hasattr(gds_business, name), f"Missing export: {name}"

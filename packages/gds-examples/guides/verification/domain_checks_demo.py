"""Domain-specific verification showcase using the stockflow DSL.

Demonstrates how domain-specific checks (SF-001..SF-005) complement
the generic GDS checks (G-001..G-006). Domain checks operate on the
domain model BEFORE compilation, catching errors that only make sense
in the stock-flow semantics.

Concepts Covered:
    - StockFlowModel construction and validation
    - SF-001 (orphan stocks), SF-003 (auxiliary cycles), SF-004 (unused converters)
    - Running domain + GDS checks together via stockflow.verification.engine.verify()
    - How domain checks complement generic checks

Prerequisites: Read verification_demo.py for generic/semantic checks.
"""

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel
from stockflow.verification.checks import (
    check_sf001_orphan_stocks,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
)
from stockflow.verification.engine import verify

# ══════════════════════════════════════════════════════════════════
# Broken domain models
# ══════════════════════════════════════════════════════════════════


def orphan_stock_model() -> StockFlowModel:
    """A stock-flow model where one stock has no connected flows.

    Stock 'Inventory' is declared but no flow drains from or fills it.
    Detected by SF-001 (orphan stocks).

    Expected findings:
        SF-001: Stock 'Inventory' has no connected flows (WARNING)
    """
    return StockFlowModel(
        name="Orphan Stock Demo",
        stocks=[
            Stock(name="Active"),
            Stock(name="Inventory"),
        ],
        flows=[
            Flow(name="Production", target="Active"),
            Flow(name="Consumption", source="Active"),
        ],
    )


def cyclic_auxiliary_model() -> StockFlowModel:
    """A stock-flow model with circular auxiliary dependencies.

    Auxiliary 'Price' depends on 'Demand', and 'Demand' depends on
    'Price', creating a circular dependency. Detected by SF-003
    (auxiliary acyclicity).

    Expected findings:
        SF-003: cycle detected in auxiliary dependency graph (ERROR)
    """
    return StockFlowModel(
        name="Cyclic Auxiliary Demo",
        stocks=[Stock(name="Supply")],
        auxiliaries=[
            Auxiliary(name="Price", inputs=["Demand"]),
            Auxiliary(name="Demand", inputs=["Price"]),
        ],
    )


def unused_converter_model() -> StockFlowModel:
    """A stock-flow model with an unreferenced converter.

    Converter 'Tax Rate' is declared but no auxiliary reads from it.
    Detected by SF-004 (converter connectivity).

    Expected findings:
        SF-004: Converter 'Tax Rate' is NOT referenced by any auxiliary (WARNING)
    """
    return StockFlowModel(
        name="Unused Converter Demo",
        stocks=[Stock(name="Revenue")],
        flows=[Flow(name="Income", target="Revenue")],
        auxiliaries=[Auxiliary(name="Growth", inputs=["Revenue"])],
        converters=[Converter(name="Tax Rate")],
    )


def good_stockflow_model() -> StockFlowModel:
    """A well-formed stock-flow model that passes all SF checks.

    Models a simple population with birth and death flows, a fertility
    auxiliary, and a fertility converter.
    """
    return StockFlowModel(
        name="Population Model",
        stocks=[Stock(name="Population", initial=1000.0)],
        flows=[
            Flow(name="Births", target="Population"),
            Flow(name="Deaths", source="Population"),
        ],
        auxiliaries=[
            Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
        ],
        converters=[Converter(name="Fertility")],
    )


# ══════════════════════════════════════════════════════════════════
# Demonstrations
# ══════════════════════════════════════════════════════════════════


def demo_orphan_stock() -> list:
    """Demonstrate SF-001: detecting orphan stocks.

    Returns:
        List of SF-001 findings with one failure for 'Inventory'.
    """
    model = orphan_stock_model()
    findings = check_sf001_orphan_stocks(model)

    failures = [f for f in findings if not f.passed]
    assert len(failures) == 1
    assert "Inventory" in failures[0].source_elements

    return findings


def demo_cyclic_auxiliaries() -> list:
    """Demonstrate SF-003: detecting auxiliary dependency cycles.

    Returns:
        List of SF-003 findings with one cycle error.
    """
    model = cyclic_auxiliary_model()
    findings = check_sf003_auxiliary_acyclicity(model)

    failures = [f for f in findings if not f.passed]
    assert len(failures) == 1
    assert failures[0].check_id == "SF-003"

    return findings


def demo_unused_converter() -> list:
    """Demonstrate SF-004: detecting unreferenced converters.

    Returns:
        List of SF-004 findings with one warning for 'Tax Rate'.
    """
    model = unused_converter_model()
    findings = check_sf004_converter_connectivity(model)

    failures = [f for f in findings if not f.passed]
    assert len(failures) == 1
    assert "Tax Rate" in failures[0].source_elements

    return findings


def demo_domain_plus_gds_checks() -> dict:
    """Run domain SF checks AND generic GDS checks on the same model.

    The stockflow verification engine runs SF-001..SF-005 first, then
    optionally compiles to SystemIR and runs G-001..G-006. This shows
    how domain and generic checks complement each other.

    Returns:
        Dict with 'sf_only' and 'full' VerificationReports.
    """
    model = good_stockflow_model()

    # SF checks only (no compilation)
    sf_report = verify(model, include_gds_checks=False)
    sf_findings = [f for f in sf_report.findings if f.check_id.startswith("SF-")]
    assert len(sf_findings) > 0

    # Full verification (SF + GDS)
    full_report = verify(model, include_gds_checks=True)
    gds_findings = [f for f in full_report.findings if f.check_id.startswith("G-")]
    assert len(gds_findings) > 0

    return {
        "sf_only": sf_report,
        "full": full_report,
    }


def demo_broken_domain_full_verification() -> dict:
    """Run full verification on a broken domain model.

    The orphan stock model has one domain error (SF-001) but is
    otherwise structurally sound. Running full verification shows
    that domain errors are surfaced alongside generic check results.

    Returns:
        Dict with counts of SF and GDS findings.
    """
    model = orphan_stock_model()

    report = verify(model, include_gds_checks=True)

    sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
    gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]

    # SF-001 should flag orphan stock
    sf_failures = [f for f in sf_findings if not f.passed]
    assert any(f.check_id == "SF-001" for f in sf_failures)

    return {
        "sf_total": len(sf_findings),
        "sf_failures": len(sf_failures),
        "gds_total": len(gds_findings),
        "gds_failures": len([f for f in gds_findings if not f.passed]),
    }

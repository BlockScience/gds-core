"""Stock-flow DSL over GDS semantics — system dynamics with formal guarantees.

Declare stocks, flows, auxiliaries, and converters as plain data models.
The compiler maps them to GDS role blocks, entities, and composition trees.
All downstream GDS tooling works immediately — canonical projection,
semantic checks, SpecQuery, serialization, gds-viz.
"""

__version__ = "0.1.0"

# ── DSL declarations ────────────────────────────────────────
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.errors import SFCompilationError, SFError, SFValidationError
from stockflow.dsl.model import StockFlowModel
from stockflow.dsl.types import ElementType

# ── Compilation ─────────────────────────────────────────────
from stockflow.dsl.compile import (
    LevelSpace,
    LevelType,
    RateSpace,
    RateType,
    SignalSpace,
    SignalType,
    UnconstrainedLevelSpace,
    UnconstrainedLevelType,
    compile_model,
    compile_to_system,
)

# ── Verification ────────────────────────────────────────────
from stockflow.verification.checks import (
    ALL_SF_CHECKS,
    check_sf001_orphan_stocks,
    check_sf002_flow_stock_validity,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
    check_sf005_flow_completeness,
)
from stockflow.verification.engine import verify

# ── Re-exports from gds-framework ──────────────────────────
from gds.verification.findings import Finding, Severity, VerificationReport

__all__ = [
    # DSL
    "Stock",
    "Flow",
    "Auxiliary",
    "Converter",
    "StockFlowModel",
    "ElementType",
    # Errors
    "SFError",
    "SFValidationError",
    "SFCompilationError",
    # Compilation
    "compile_model",
    "compile_to_system",
    # Semantic types and spaces
    "LevelType",
    "UnconstrainedLevelType",
    "RateType",
    "SignalType",
    "LevelSpace",
    "UnconstrainedLevelSpace",
    "RateSpace",
    "SignalSpace",
    # Verification
    "verify",
    "ALL_SF_CHECKS",
    "check_sf001_orphan_stocks",
    "check_sf002_flow_stock_validity",
    "check_sf003_auxiliary_acyclicity",
    "check_sf004_converter_connectivity",
    "check_sf005_flow_completeness",
    # Re-exports
    "Finding",
    "Severity",
    "VerificationReport",
]

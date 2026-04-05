"""gds-stockflow — DEPRECATED: use gds_domains.stockflow instead."""

import warnings

warnings.warn(
    "Import from gds_domains.stockflow instead of stockflow. "
    "The gds-stockflow package will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "0.99.0"

from gds_domains.stockflow import (  # noqa: F401, E402
    ALL_SF_CHECKS,
    Auxiliary,
    Converter,
    Finding,
    Flow,
    LevelSpace,
    LevelType,
    RateSpace,
    RateType,
    SFCompilationError,
    SFError,
    SFValidationError,
    Severity,
    SignalSpace,
    SignalType,
    Stock,
    StockFlowModel,
    UnconstrainedLevelSpace,
    UnconstrainedLevelType,
    VerificationReport,
    check_sf001_orphan_stocks,
    check_sf002_flow_stock_validity,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
    check_sf005_flow_completeness,
    compile_model,
    compile_to_system,
    verify,
)
from gds_domains.stockflow import ElementType  # noqa: F401, E402

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

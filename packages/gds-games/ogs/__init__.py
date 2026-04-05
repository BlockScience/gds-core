"""gds-games — DEPRECATED: use gds_domains.games instead."""

import warnings

warnings.warn(
    "Import from gds_domains.games instead of ogs. "
    "The gds-games package will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "0.99.0"

from gds_domains.games import (  # noqa: F401, E402
    AtomicGame,
    CompositionType,
    DecisionGame,
    FeedbackFlow,
    Finding,
    FlowDirection,
    FlowIR,
    FlowType,
    GameType,
    HierarchyNodeIR,
    IRDocument,
    InputIR,
    InputType,
    OpenGame,
    OpenGameIR,
    Pattern,
    PatternIR,
    Severity,
    VerificationReport,
    compile_pattern_to_spec,
    compile_to_ir,
    discover_patterns,
    generate_reports,
    load_ir,
    save_ir,
    verify,
)

__all__ = [
    # DSL (re-exported for convenience)
    "OpenGame",
    "DecisionGame",
    "AtomicGame",
    "Pattern",
    "FeedbackFlow",
    # Compilation
    "compile_to_ir",
    "compile_pattern_to_spec",
    # Verification
    "verify",
    "VerificationReport",
    "Finding",
    "Severity",
    # Reports
    "generate_reports",
    # Serialization
    "save_ir",
    "load_ir",
    "IRDocument",
    # Registry
    "discover_patterns",
    # IR Models
    "PatternIR",
    "OpenGameIR",
    "FlowIR",
    "InputIR",
    "HierarchyNodeIR",
    # Enums
    "GameType",
    "FlowType",
    "FlowDirection",
    "InputType",
    "CompositionType",
]


def __getattr__(name: str) -> object:
    """Lazy import for optional equilibrium module."""
    if name in (
        "compute_nash",
        "extract_payoff_matrices",
        "NashResult",
        "PayoffMatrices",
    ):
        from gds_domains.games import equilibrium  # noqa: E402

        return getattr(equilibrium, name)
    raise AttributeError(f"module 'ogs' has no attribute {name!r}")

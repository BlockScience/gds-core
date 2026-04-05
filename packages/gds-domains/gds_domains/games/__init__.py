"""Open Games — Typed DSL for Compositional Game Theory."""


from gds_domains.games.dsl.base import OpenGame
from gds_domains.games.dsl.compile import compile_to_ir
from gds_domains.games.dsl.composition import FeedbackFlow
from gds_domains.games.dsl.games import AtomicGame, DecisionGame
from gds_domains.games.dsl.pattern import Pattern
from gds_domains.games.dsl.spec_bridge import compile_pattern_to_spec
from gds_domains.games.ir.models import (
    CompositionType,
    FlowDirection,
    FlowIR,
    FlowType,
    GameType,
    HierarchyNodeIR,
    InputIR,
    InputType,
    OpenGameIR,
    PatternIR,
)
from gds_domains.games.ir.serialization import IRDocument, load_ir, save_ir
from gds_domains.games.registry import discover_patterns
from gds_domains.games.reports.generator import generate_reports
from gds_domains.games.verification.engine import verify
from gds_domains.games.verification.findings import (
    Finding,
    Severity,
    VerificationReport,
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
        from gds_domains.games import equilibrium

        return getattr(equilibrium, name)
    raise AttributeError(f"module 'gds_domains.games' has no attribute {name!r}")

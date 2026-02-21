"""Open Games — Typed DSL for Compositional Game Theory."""

from ogs.dsl.base import OpenGame
from ogs.dsl.compile import compile_to_ir
from ogs.dsl.spec_bridge import compile_pattern_to_spec
from ogs.dsl.games import AtomicGame, DecisionGame
from ogs.dsl.pattern import Pattern
from ogs.ir.models import (
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
from ogs.ir.serialization import IRDocument, load_ir, save_ir
from ogs.reports.generator import generate_reports
from ogs.verification.engine import verify
from ogs.verification.findings import Finding, Severity, VerificationReport

__all__ = [
    # DSL (re-exported for convenience)
    "OpenGame",
    "DecisionGame",
    "AtomicGame",
    "Pattern",
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

"""Generalized Dynamical Systems — typed compositional specs.

GDS synthesizes ideas from GDS theory (Roxin, Zargham & Shorish),
MSML (BlockScience), BDP-lib (Block Diagram Protocol), and categorical
cybernetics (Ghani, Hedges et al.) into a single, dependency-light
Python framework.
"""

__version__ = "0.2.1"

# ── Composition algebra ─────────────────────────────────────
from gds.blocks.base import AtomicBlock, Block
from gds.blocks.composition import (
    FeedbackLoop,
    ParallelComposition,
    StackComposition,
    TemporalLoop,
    Wiring,
)
from gds.blocks.errors import GDSCompositionError, GDSError, GDSTypeError

# ── GDS block roles ─────────────────────────────────────────
from gds.blocks.roles import (
    BoundaryAction,
    ControlAction,
    HasConstraints,
    HasOptions,
    HasParams,
    Mechanism,
    Policy,
)

# ── Canonical projection ───────────────────────────────────
from gds.canonical import CanonicalGDS, project_canonical
from gds.compiler.compile import compile_system

# ── Convenience helpers ────────────────────────────────────
from gds.helpers import (
    all_checks,
    entity,
    gds_check,
    get_custom_checks,
    interface,
    space,
    state_var,
    typedef,
)

# ── IR and serialization ────────────────────────────────────
from gds.ir.models import (
    BlockIR,
    CompositionType,
    FlowDirection,
    HierarchyNodeIR,
    SystemIR,
    WiringIR,
)
from gds.ir.serialization import IRDocument, IRMetadata, load_ir, save_ir

# ── Parameters ─────────────────────────────────────────────
from gds.parameters import ParameterDef, ParameterSchema

# ── Query engine ────────────────────────────────────────────
from gds.query import SpecQuery
from gds.serialize import spec_to_dict, spec_to_json

# ── Typed spaces and state ──────────────────────────────────
from gds.spaces import EMPTY, TERMINAL, Space

# ── Specification registry ──────────────────────────────────
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.tagged import Tagged
from gds.types.interface import Interface, Port, port
from gds.types.tokens import tokenize, tokens_overlap, tokens_subset

# ── Type system ─────────────────────────────────────────────
from gds.types.typedef import (
    AgentID,
    NonNegativeFloat,
    PositiveInt,
    Probability,
    Timestamp,
    TokenAmount,
    TypeDef,
)

# ── Verification ────────────────────────────────────────────
from gds.verification.engine import verify
from gds.verification.findings import Finding, Severity, VerificationReport
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
    check_parameter_references,
    check_reachability,
    check_type_safety,
)

__all__ = [
    "EMPTY",
    "TERMINAL",
    "AgentID",
    "AtomicBlock",
    "Block",
    "BlockIR",
    "BoundaryAction",
    "CanonicalGDS",
    "CompositionType",
    "ControlAction",
    "Entity",
    "FeedbackLoop",
    "Finding",
    "FlowDirection",
    "GDSCompositionError",
    "GDSError",
    "GDSSpec",
    "GDSTypeError",
    "HasConstraints",
    "HasOptions",
    "HasParams",
    "HierarchyNodeIR",
    "IRDocument",
    "IRMetadata",
    "Interface",
    "Mechanism",
    "NonNegativeFloat",
    "ParallelComposition",
    "ParameterDef",
    "ParameterSchema",
    "Policy",
    "Port",
    "PositiveInt",
    "Probability",
    "Severity",
    "Space",
    "SpecQuery",
    "SpecWiring",
    "StackComposition",
    "StateVariable",
    "SystemIR",
    "Tagged",
    "TemporalLoop",
    "Timestamp",
    "TokenAmount",
    "TypeDef",
    "VerificationReport",
    "Wire",
    "Wiring",
    "WiringIR",
    "all_checks",
    "check_canonical_wellformedness",
    "check_completeness",
    "check_determinism",
    "check_parameter_references",
    "check_reachability",
    "check_type_safety",
    "compile_system",
    "entity",
    "gds_check",
    "get_custom_checks",
    "interface",
    "load_ir",
    "port",
    "project_canonical",
    "save_ir",
    "space",
    "spec_to_dict",
    "spec_to_json",
    "state_var",
    "tokenize",
    "tokens_overlap",
    "tokens_subset",
    "typedef",
    "verify",
]

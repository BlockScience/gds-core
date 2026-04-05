"""Typed DSL for Compositional Game Theory.

Public API — import everything needed to define patterns:

    from gds_domains.games.dsl import *

    agent = reactive_decision_agent()
    p = Pattern(name="My Pattern", game=agent, ...)
    ir = compile_to_ir(p)

Note: ``compile_to_ir`` and ``library`` factories are imported lazily to
avoid a circular dependency between ogs.dsl (types/enums) and ogs.ir
(models that use those enums).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gds_domains.games.dsl.compile import compile_to_ir as compile_to_ir
    from gds_domains.games.dsl.library import (
        context_builder as context_builder,
    )
    from gds_domains.games.dsl.library import (
        history as history,
    )
    from gds_domains.games.dsl.library import (
        multi_agent_composition as multi_agent_composition,
    )
    from gds_domains.games.dsl.library import (
        outcome as outcome,
    )
    from gds_domains.games.dsl.library import (
        parallel as parallel,
    )
    from gds_domains.games.dsl.library import (
        policy as policy,
    )
    from gds_domains.games.dsl.library import (
        reactive_decision as reactive_decision,
    )
    from gds_domains.games.dsl.library import (
        reactive_decision_agent as reactive_decision_agent,
    )

from gds_domains.games.dsl.base import OpenGame
from gds_domains.games.dsl.composition import (
    CorecursiveLoop,
    FeedbackFlow,
    FeedbackLoop,
    Flow,
    ParallelComposition,
    SequentialComposition,
)
from gds_domains.games.dsl.errors import DSLCompositionError, DSLError, DSLTypeError
from gds_domains.games.dsl.games import (
    AtomicGame,
    ContravariantFunction,
    CounitGame,
    CovariantFunction,
    DecisionGame,
    DeletionGame,
    DuplicationGame,
)
from gds_domains.games.dsl.pattern import (
    ActionSpace,
    Pattern,
    PatternInput,
    StateInitialization,
    TerminalCondition,
)
from gds_domains.games.dsl.types import (
    CompositionType,
    FlowType,
    GameType,
    InputType,
    Port,
    Signature,
    port,
)


def __getattr__(name: str):
    """Lazy imports for modules that depend on ogs.ir (avoids circular import)."""
    if name == "compile_to_ir":
        from gds_domains.games.dsl.compile import compile_to_ir

        return compile_to_ir

    _library_names = {
        "context_builder",
        "history",
        "multi_agent_composition",
        "outcome",
        "parallel",
        "policy",
        "reactive_decision",
        "reactive_decision_agent",
    }
    if name in _library_names:
        import gds_domains.games.dsl.library as _lib

        return getattr(_lib, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Types & Enums
    "Port",
    "Signature",
    "port",
    "CompositionType",
    "GameType",
    "FlowType",
    "InputType",
    # Base
    "OpenGame",
    # Games
    "AtomicGame",
    "DecisionGame",
    "CovariantFunction",
    "ContravariantFunction",
    "DeletionGame",
    "DuplicationGame",
    "CounitGame",
    # Composition
    "Flow",
    "FeedbackFlow",
    "SequentialComposition",
    "ParallelComposition",
    "FeedbackLoop",
    "CorecursiveLoop",
    # Pattern
    "Pattern",
    "PatternInput",
    "TerminalCondition",
    "ActionSpace",
    "StateInitialization",
    # Compiler (lazy)
    "compile_to_ir",
    # Library (lazy)
    "context_builder",
    "history",
    "multi_agent_composition",
    "outcome",
    "parallel",
    "policy",
    "reactive_decision",
    "reactive_decision_agent",
    # Errors
    "DSLError",
    "DSLTypeError",
    "DSLCompositionError",
]

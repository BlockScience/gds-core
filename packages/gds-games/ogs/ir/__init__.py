"""OGS Intermediate Representation — game-theoretic extension of GDS IR.

This package contains the flat, serializable data models that sit between
the typed DSL (``ogs.dsl``) and the verification/report/viz layers.

Relationship to GDS IR
----------------------
GDS (``gds-framework``) owns the generic IR concept: ``BlockIR``, ``WiringIR``,
``HierarchyNodeIR``, and ``SystemIR``. OGS extends this with game-theory
specific models:

- ``OpenGameIR`` — a block specialized for open games (adds ``game_type``,
  ``constraints``, ``tags``)
- ``FlowIR`` — a wiring specialized for information flows (adds ``flow_type``,
  ``is_corecursive``)
- ``HierarchyNodeIR`` — extends GDS ``HierarchyNodeIR`` with OGS's
  ``CompositionType`` (which includes CORECURSIVE, mapped to GDS TEMPORAL)
- ``PatternIR`` — the top-level unit (analogous to GDS ``SystemIR``), with
  ``to_system_ir()`` for projecting back to GDS for generic verification

Domain enums (``GameType``, ``FlowType``, ``CompositionType``, ``InputType``)
are canonically defined in ``ogs.dsl.types`` and re-exported here for
backwards compatibility.

Metadata models (``TerminalCondition``, ``ActionSpace``, ``StateInitialization``)
are canonically defined in ``ogs.dsl.pattern`` and aliased here as
``TerminalConditionIR``, ``ActionSpaceIR``, ``StateInitializationIR``.

Public API
----------
Most consumers should import from this module::

    from ogs.ir.models import PatternIR, OpenGameIR, FlowIR, ...
    from ogs.ir.serialization import save_ir, load_ir, IRDocument
"""

from ogs.ir.models import (
    ActionSpaceIR,
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
    StateInitializationIR,
    TerminalConditionIR,
)
from ogs.ir.serialization import IRDocument, load_ir, save_ir

__all__ = [
    # Domain enums (canonical: ogs.dsl.types)
    "CompositionType",
    "FlowType",
    "GameType",
    "InputType",
    # GDS re-exports
    "FlowDirection",
    # OGS IR models
    "OpenGameIR",
    "FlowIR",
    "InputIR",
    "HierarchyNodeIR",
    "PatternIR",
    # Metadata aliases (canonical: ogs.dsl.pattern)
    "TerminalConditionIR",
    "ActionSpaceIR",
    "StateInitializationIR",
    # Serialization
    "IRDocument",
    "save_ir",
    "load_ir",
]

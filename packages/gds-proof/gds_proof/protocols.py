"""Structural protocols for the gds-proof symbolic analysis engine.

Block formalism
---------------
Every block in a GDS wiring diagram is an open stateful system:

    for u ∈ U_{x_prev} ⊆ U:
        x = f(x_prev, u)      # state transition
        y = c(x, u)           # observable output

Where:

``x_prev``
    Internal state before the transition.  Carried as ``prev_state_symbols``.

``u``
    Input drawn from the admissible set ``U_{x_prev} ⊆ U``.  Carried as
    ``input_symbols``.  The admissible set is state-dependent — blocks are
    NOT assumed to be stateless.

``x``
    Internal state after the transition.  Defined by ``f(x_prev, u)``.
    Not directly observable by other blocks unless ``c`` reveals it.

``y``
    Observable output wired to downstream blocks.  ``y = c(x, u)``.
    ``c`` is an interface/port function — it determines what the outside
    world can measure.

In SymPy terms
--------------
Because ``x = f(x_prev, u)`` is known symbolically, ``c(x, u)`` composes
to ``c(f(x_prev, u), u)`` — a closed expression over
``prev_state_symbols union input_symbols``.

Concretely, ``output_expressions`` values are SymPy expressions already
stated in terms of ``prev_state_symbols union input_symbols`` (with ``x``
substituted away).  No separate post-state symbol set is needed.

Admissibility / predicates
--------------------------
The condition ``u ∈ U_{x_prev}`` is a state-dependent domain restriction.
Predicate free symbols must satisfy:

    pred.free_symbols ⊆ prev_state_symbols union input_symbols

Both the current state and the input are visible to the predicate.

Proof semantics
---------------
The proof obligation for one (invariant ``I``, block ``k``) pair is:

    ∀ x_prev, u ∈ U_{x_prev}:
        I(x_prev) ∧ P_1(x_prev, u) ∧ … ∧ P_m(x_prev, u)
        →  I(f(x_prev, u))

``substitution()`` provides the map ``x_prev_sym → f_expr`` to build
``I(f(x_prev, u))`` from ``I(x_prev)`` by SymPy substitution.

GDS framework integration
--------------------------
These protocols define the symbolic interface the proof engine requires.
GDS framework blocks (``AtomicBlock``, ``Mechanism``, etc.) are structural
(R1) and do not carry SymPy expressions natively.  The ``adapter`` module
provides concrete implementations that bridge GDS types to these protocols
by pairing an ``AtomicBlock`` with user-supplied symbolic expressions.

See ``gds_proof.adapter.GDSSymbolicBlock`` and ``gds_proof.adapter.GDSSymbolicModel``
for the recommended way to construct proof-ready objects from GDS specs.
"""

from __future__ import annotations

import warnings
from typing import Protocol, runtime_checkable

import sympy  # noqa: TC002

from gds_proof.invariant import Invariant  # noqa: TC001


@runtime_checkable
class SymbolicBlock(Protocol):
    """A block enriched with symbolic expressions for proof analysis.

    Provides the SymPy-level behavioral information (state transitions,
    output maps, predicates) that the proof engine needs to verify
    invariant preservation.

    Canonical form::

        for u ∈ U_{x_prev} ⊆ U:
            x = f(x_prev, u)     # state_transition
            y = c(x, u)          # output_expressions
    """

    @property
    def name(self) -> str:
        """Unique identifier for this block within the model."""
        ...

    # ------------------------------------------------------------------
    # Symbol sets
    # ------------------------------------------------------------------

    @property
    def prev_state_symbols(self) -> frozenset[sympy.Symbol]:
        """Symbols representing pre-transition internal state ``x_prev``.

        These appear as arguments to ``f`` and implicitly to ``c``
        (via ``x = f(x_prev, u)``).  Invariants are stated over these
        symbols before the transition.
        """
        ...

    @property
    def input_symbols(self) -> frozenset[sympy.Symbol]:
        """Symbols representing block input ``u ∈ U_{x_prev} ⊆ U``.

        Wired from upstream output ports or boundary inputs.
        """
        ...

    # ------------------------------------------------------------------
    # Admissibility — U_{x_prev}
    # ------------------------------------------------------------------

    @property
    def predicates(self) -> list[sympy.Basic]:
        """State-dependent domain restriction on inputs.

        Each predicate is a BooleanExpr over
        ``prev_state_symbols union input_symbols``.  A transition is admitted
        only when all predicates evaluate to True.

        Empty list means the block is unconditionally admissible
        (``U_{x_prev} = U`` for all ``x_prev``).
        """
        ...

    # ------------------------------------------------------------------
    # State transition — x = f(x_prev, u)
    # ------------------------------------------------------------------

    @property
    def state_transition(self) -> dict[str, sympy.Basic]:
        """Post-transition state expressions.

        Maps each state-component key to its SymPy expression
        ``f_k(x_prev, u)`` over ``prev_state_symbols union input_symbols``.

        Used by ``substitution()`` to build ``I(f(x_prev, u))`` for proof.
        """
        ...

    # ------------------------------------------------------------------
    # Output function — y = c(x, u)
    # ------------------------------------------------------------------

    @property
    def output_expressions(self) -> dict[str, sympy.Basic]:
        """Observable output expressions wired to downstream blocks.

        Maps each output port name to a SymPy expression encoding
        ``c(f(x_prev, u), u)`` — i.e., ``c(x, u)`` with ``x`` substituted
        via ``state_transition``.  Values are over
        ``prev_state_symbols union input_symbols``.
        """
        ...

    # ------------------------------------------------------------------
    # Substitution helper for proof engine
    # ------------------------------------------------------------------

    def substitution(self) -> dict[sympy.Basic, sympy.Basic]:
        """Combined symbol substitution for invariant proof.

        Returns a dict mapping block symbols to their post-transition
        expressions.  Two kinds of entries:

        **State symbols** (``x_prev → f(x_prev, u)``)
            Maps each pre-state symbol to its post-transition expression.

        **Output symbols** (``y → c(f(x_prev, u), u)``)
            Maps each output port symbol to its expression.

        Combined, ``invariant_expr.subs(block.substitution())`` correctly
        handles invariants over any combination of state and output symbols.
        """
        ...


@runtime_checkable
class SymbolicModel(Protocol):
    """A model enriched with symbolic information for proof analysis.

    Provides the proof engine with blocks (as ``SymbolicBlock`` instances),
    invariants to verify, assumption context for the Q-system strategy,
    and a canonical dict for deterministic hashing.

    For GDS-based models, use ``GDSSymbolicModel`` from ``gds_proof.adapter``
    which wraps a ``GDSSpec`` and derives structural information automatically.
    """

    def blocks(self) -> dict[str, SymbolicBlock]:
        """All blocks participating in proof analysis, keyed by block name."""
        ...

    def invariants(self) -> dict[str, Invariant]:
        """Model-level invariants keyed by name.

        Each invariant is a named BooleanExpr over symbols drawn from the
        blocks' ``prev_state_symbols``.  The proof engine attempts to show
        that every block's state transition preserves every invariant.
        """
        ...

    def assumption_context(self) -> dict[sympy.Symbol, dict]:
        """Symbol-to-assumption-dict for Q-system analysis (strategy 3).

        Example::

            {sympy.Symbol("fee_rate"): {"positive": True, "real": True}}

        Derived from parameter bounds and declared state properties.
        """
        ...

    def canonical_dict(self) -> dict:
        """Deterministic JSON-serializable dict of declared components.

        Excludes execution artifacts.  Implementors delegate to
        ``gds_proof.serialization.canonical.make_canonical_dict()``.
        Used as sole input to ``hash_model()``.
        """
        ...


# ---------------------------------------------------------------------------
# Deprecated aliases — remove in v1.0.0
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> type:
    _aliases = {
        "ProofableBlock": SymbolicBlock,
        "ProofableModel": SymbolicModel,
    }
    if name in _aliases:
        warnings.warn(
            f"gds_proof.protocols.{name} is deprecated, "
            f"use {_aliases[name].__name__} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return _aliases[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

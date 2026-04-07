"""Structural protocols for the gds-proof engine.

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
    world can measure.  Examples:

    - ``y = x``       — full post-state revealed
    - ``y = g(x)``    — any projection of the post-state
    - ``y = u``       — pure pass-through

    ``x_prev`` does NOT appear as an explicit argument to ``c``.  If a
    block needs to expose something like a difference (e.g. velocity), that
    quantity is modelled as its own state component in ``x`` — the state
    space is augmented rather than exposing the previous state directly.

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
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import sympy  # noqa: TC002

from gds_proof.invariant import Invariant  # noqa: TC001


@runtime_checkable
class ProofableBlock(Protocol):
    """An open stateful system block participating in symbolic proof analysis.

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

        Canonical construction
        ~~~~~~~~~~~~~~~~~~~~~~
        Predicates are typically constructed by choosing a desired post-state
        property ``check(x)`` and pulling it back through the state
        transition::

            U_{x_prev} = {u ∈ U : check(f(x_prev, u)) = True}

        Example: ``x = x_prev - u``, desired post-state ``x > 0`` gives
        predicate ``x_prev - u > 0``, i.e. ``u < x_prev``.

        Use ``gds_proof.predicate.predicate_from_post_check()`` to perform
        this substitution automatically and preserve the ``post_state_form``
        for auditors.

        Local invariants
        ~~~~~~~~~~~~~~~~
        The post-state check ``check(x)`` is the *local invariant* this
        block enforces: for every admitted transition, the post-state
        satisfies ``check(x)``.  These local guarantees compose across
        blocks through the wiring diagram to produce *emergent global
        invariants* — properties no single block owns but the composed
        system guarantees.
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

        ``x_prev`` does not appear as a distinct argument: if a block needs
        to expose a difference or velocity, that quantity is a dedicated
        state component in ``x``.
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
            Used to build ``I(f(x_prev, u))`` from ``I(x_prev)``.

        **Output symbols** (``y → c(f(x_prev, u), u)``)
            Maps each output port symbol to its expression, already stated
            in terms of ``prev_state_symbols union input_symbols`` (``x``
            substituted away).  Allows invariants to be stated over output
            symbols of blocks with unwired (open) output ports — the proof
            engine does not require outputs to be connected downstream.

        Combined, ``invariant_expr.subs(block.substitution())`` correctly
        handles invariants over any combination of state and output symbols
        that this block produces.

        Open-world inputs
        ~~~~~~~~~~~~~~~~~
        Input symbols need NOT be wired from an upstream block.  Open inputs
        are universally quantified over ``U_{x_prev}`` — the predicate is the
        type system.  The proof engine treats all inputs as universally
        quantified regardless of wiring status.
        """
        ...


@runtime_checkable
class ProofableModel(Protocol):
    """Interface the gds-proof engine requires of any model.

    Any model that implements these four methods — without importing any
    gds-proof types — satisfies the protocol via structural subtyping.
    """

    def blocks(self) -> dict[str, ProofableBlock]:
        """All blocks participating in proof analysis, keyed by block name.

        Includes any block whose state or output symbols appear in declared
        invariants, regardless of wiring status.  A block with unwired
        (open) output ports is still included if its outputs are referenced
        in invariants — the proof engine does not require port closure.

        Open-world interpretation
        ~~~~~~~~~~~~~~~~~~~~~~~~~
        The composed model is itself interpretable as a single block whose:

        - Inputs  = Cartesian product of all open (unwired) input ports.
        - Outputs = Cartesian product of ALL output ports (outputs may fan
          out to multiple downstream inputs unless cardinality is restricted).

        Open inputs are universally quantified over ``U_{x_prev}`` — the
        predicate defines the admissible set, not the wiring.  Port closure
        is a property of a specific instantiation, not a precondition for
        proof.
        """
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

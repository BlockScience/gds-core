"""Adapters bridging GDS framework types to gds-proof symbolic protocols.

GDS blocks are structural (R1) — they declare *what* state variables a
mechanism updates, but not *how* (no SymPy expressions).  These adapters
pair GDS types with user-supplied symbolic expressions to satisfy the
``SymbolicBlock`` and ``SymbolicModel`` protocols.

Typical usage::

    from gds import Mechanism, Entity, GDSSpec, interface, entity, state_var, typedef
    from gds_proof.adapter import GDSSymbolicBlock, GDSSymbolicModel
    from gds_proof import Invariant, predicate_from_post_check, analyze_invariants

    # 1. Build GDS structural spec as usual
    spec = GDSSpec(name="bank")
    spec.collect(Balance, account_entity, withdrawal_mechanism)

    # 2. Enrich with symbolic expressions
    block = GDSSymbolicBlock(
        block=withdrawal_mechanism,
        spec=spec,
        state_transition={"x_prev": X - U},
        output_expressions={"balance": X - U},
        predicates_list=[pred.expr],
    )

    # 3. Build model and analyze
    model = GDSSymbolicModel(
        spec=spec,
        enrichments={"withdrawal": block},
        invariants_dict={"balance_nonneg": Invariant(...)},
    )
    result = analyze_invariants(model)

Symbol derivation
-----------------
``GDSSymbolicBlock`` can optionally derive ``prev_state_symbols`` from
the mechanism's ``updates`` list and the spec's entity definitions.  For
each ``(entity_name, var_name)`` in ``Mechanism.updates``, it looks up
``Entity.variables[var_name].symbol`` — if set, creates
``sympy.Symbol(symbol)``; otherwise creates ``sympy.Symbol(f"{entity}_{var}")``.

Input symbols must always be explicitly provided since GDS blocks do not
carry enough information to derive them unambiguously.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sympy
from gds.blocks.base import AtomicBlock  # noqa: TC002
from gds.blocks.roles import Mechanism
from gds.spec import GDSSpec  # noqa: TC002

from gds_proof.invariant import Invariant  # noqa: TC001
from gds_proof.serialization.canonical import make_canonical_dict

if TYPE_CHECKING:
    from gds_proof.types import SympyBoolean, SympyExpr


def derive_state_symbols(
    mechanism: Mechanism,
    spec: GDSSpec,
) -> frozenset[sympy.Symbol]:
    """Derive pre-state symbols from a mechanism's updates and the spec's entities.

    For each ``(entity_name, var_name)`` in ``mechanism.updates``:
    - If ``Entity.variables[var_name].symbol`` is set, use that as the symbol name
    - Otherwise, use ``"{entity_name}_{var_name}"``

    All symbols are created plain (no assumptions baked in).

    Parameters
    ----------
    mechanism:
        The mechanism block whose updates define state variables.
    spec:
        The GDS spec containing entity definitions.

    Returns
    -------
    frozenset[sympy.Symbol]
        Plain SymPy symbols for pre-transition state.
    """
    symbols: set[sympy.Symbol] = set()
    for entity_name, var_name in mechanism.updates:
        ent = spec.entities.get(entity_name)
        if ent is not None:
            var = ent.variables.get(var_name)
            if var is not None and var.symbol:
                symbols.add(sympy.Symbol(var.symbol))
            else:
                symbols.add(sympy.Symbol(f"{entity_name}_{var_name}"))
        else:
            symbols.add(sympy.Symbol(f"{entity_name}_{var_name}"))
    return frozenset(symbols)


def derive_assumption_context(
    spec: GDSSpec,
) -> dict[sympy.Symbol, dict]:
    """Build SymPy assumption dict from spec parameter bounds.

    Examines ``ParameterDef.bounds`` in the spec's parameter schema.
    When bounds are ``(0, None)`` or ``(0, inf)``, infers ``nonnegative``.
    When bounds are ``(epsilon, None)`` with epsilon > 0, infers ``positive``.
    All parameters are assumed ``real`` and ``finite``.

    Parameters
    ----------
    spec:
        The GDS spec with a parameter schema.

    Returns
    -------
    dict[sympy.Symbol, dict]
        Suitable for ``SymbolicModel.assumption_context()``.
    """
    assumptions: dict[sympy.Symbol, dict] = {}
    for name, param_def in spec.parameter_schema.parameters.items():
        asm: dict[str, bool] = {"real": True, "finite": True}
        if param_def.bounds is not None:
            lower, _upper = param_def.bounds
            if lower is not None and lower > 0:
                asm["positive"] = True
            elif lower is not None and lower >= 0:
                asm["nonnegative"] = True
        assumptions[sympy.Symbol(name)] = asm
    return assumptions


class GDSSymbolicBlock:
    """Wraps a GDS ``AtomicBlock`` with symbolic expressions for proof.

    Satisfies the ``SymbolicBlock`` protocol by combining structural information
    from the GDS block/spec with user-supplied SymPy expressions.

    Parameters
    ----------
    block:
        The GDS block this enrichment is for.
    spec:
        The GDS spec containing entity definitions (used to derive state symbols
        if ``prev_state`` is not explicitly provided).
    state_transition:
        ``{state_key: f(x_prev, u)}`` — the behavioral content.
    output_expressions:
        ``{output_name: c(f(x_prev, u), u)}`` — observable outputs.
    predicates_list:
        List of SymPy BooleanExpr predicates gating admissible inputs.
    prev_state:
        Explicit pre-state symbols.  If ``None`` and block is a ``Mechanism``,
        derived from ``mechanism.updates`` + ``spec.entities``.
    inputs:
        Input symbols.  Must be provided explicitly.
    """

    def __init__(
        self,
        block: AtomicBlock,
        spec: GDSSpec,
        state_transition: dict[str, SympyExpr],
        output_expressions: dict[str, SympyExpr] | None = None,
        predicates_list: list[SympyBoolean] | None = None,
        prev_state: frozenset[sympy.Symbol] | None = None,
        inputs: frozenset[sympy.Symbol] | None = None,
    ) -> None:
        self._block = block
        self._spec = spec
        self._transition = state_transition
        self._outputs = output_expressions or {}
        self._predicates = predicates_list or []

        # Derive prev_state_symbols from Mechanism.updates if not provided
        if prev_state is not None:
            self._prev_state = prev_state
        elif isinstance(block, Mechanism):
            self._prev_state = derive_state_symbols(block, spec)
        else:
            self._prev_state = frozenset()

        self._inputs = inputs or frozenset()

    @property
    def block(self) -> AtomicBlock:
        """The underlying GDS block."""
        return self._block

    @property
    def spec(self) -> GDSSpec:
        """The GDS spec this block belongs to."""
        return self._spec

    @property
    def name(self) -> str:
        return self._block.name

    @property
    def prev_state_symbols(self) -> frozenset[sympy.Symbol]:
        return self._prev_state

    @property
    def input_symbols(self) -> frozenset[sympy.Symbol]:
        return self._inputs

    @property
    def predicates(self) -> list[sympy.Basic]:
        return list(self._predicates)

    @property
    def state_transition(self) -> dict[str, sympy.Basic]:
        return dict(self._transition)

    @property
    def output_expressions(self) -> dict[str, sympy.Basic]:
        return dict(self._outputs)

    def substitution(self) -> dict[sympy.Basic, sympy.Basic]:
        """Build combined substitution from state transitions and output expressions.

        Maps:
        - Each pre-state symbol to its post-transition expression
        - Each output symbol to its output expression
        """
        subs: dict[sympy.Basic, sympy.Basic] = {}
        # State symbols: x_prev → f(x_prev, u)
        for sym in self._prev_state:
            key = str(sym)
            if key in self._transition:
                subs[sym] = self._transition[key]
        # Output symbols: y → c(f(x_prev, u), u)
        for out_name, out_expr in self._outputs.items():
            subs[sympy.Symbol(out_name)] = out_expr
        return subs


class GDSSymbolicModel:
    """Concrete ``SymbolicModel`` wrapping a ``GDSSpec`` with symbolic enrichments.

    Satisfies the ``SymbolicModel`` protocol by combining structural information
    from a ``GDSSpec`` with ``GDSSymbolicBlock`` enrichments and invariants.

    Parameters
    ----------
    spec:
        The underlying GDS specification.
    enrichments:
        Blocks enriched with symbolic expressions, keyed by block name.
    invariants_dict:
        Model-level invariants to verify, keyed by name.
    assumptions:
        Symbol-to-assumption mapping.  If ``None``, derived from
        ``spec.parameter_schema`` via ``derive_assumption_context()``.
    """

    def __init__(
        self,
        spec: GDSSpec,
        enrichments: dict[str, GDSSymbolicBlock],
        invariants_dict: dict[str, Invariant],
        assumptions: dict[sympy.Symbol, dict] | None = None,
    ) -> None:
        self._spec = spec
        self._enrichments = enrichments
        self._invariants = invariants_dict
        self._assumptions = (
            assumptions if assumptions is not None else derive_assumption_context(spec)
        )

    @property
    def spec(self) -> GDSSpec:
        """The underlying GDS specification."""
        return self._spec

    def blocks(self) -> dict[str, GDSSymbolicBlock]:
        return dict(self._enrichments)

    def invariants(self) -> dict[str, Invariant]:
        return dict(self._invariants)

    def assumption_context(self) -> dict[sympy.Symbol, dict]:
        return dict(self._assumptions)

    def canonical_dict(self) -> dict:
        """Deterministic canonical dict including both structural and symbolic content.

        Includes:
        - Spec structural data (block names, entity names, wirings)
        - Symbolic enrichment data (state transitions, output expressions)
        - Invariant expressions
        """
        return make_canonical_dict(
            {
                "spec_name": self._spec.name,
                "entities": sorted(self._spec.entities.keys()),
                "blocks": {
                    name: {
                        "gds_block": blk.block.name,
                        "state_transition": {
                            k: str(v) for k, v in blk.state_transition.items()
                        },
                        "output_expressions": {
                            k: str(v) for k, v in blk.output_expressions.items()
                        },
                    }
                    for name, blk in sorted(self._enrichments.items())
                },
                "invariants": {
                    name: inv.expr for name, inv in sorted(self._invariants.items())
                },
            }
        )

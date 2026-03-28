"""Linearization: compute Jacobian matrices at an operating point."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from gds_symbolic._compat import require_sympy

if TYPE_CHECKING:
    from gds_symbolic.model import SymbolicControlModel


@dataclass(frozen=True)
class LinearizedSystem:
    """State-space matrices (A, B, C, D) at an operating point.

    All matrices are lists-of-lists (no numpy dependency required).
    """

    A: list[list[float]]
    B: list[list[float]]
    C: list[list[float]]
    D: list[list[float]]
    x0: list[float]
    u0: list[float]
    state_names: list[str] = field(default_factory=list)
    input_names: list[str] = field(default_factory=list)
    output_names: list[str] = field(default_factory=list)


def linearize(
    model: SymbolicControlModel,
    x0: list[float],
    u0: list[float],
    param_values: dict[str, float] | None = None,
) -> LinearizedSystem:
    """Compute linearization at operating point (x0, u0).

    Computes Jacobians of the state equations w.r.t. states (A)
    and inputs (B), and output equations w.r.t. states (C) and
    inputs (D), all evaluated at the given operating point.

    Parameters
    ----------
    model : SymbolicControlModel
    x0 : list[float]
        Operating point state values (ordered by model.states).
    u0 : list[float]
        Operating point input values (ordered by model.inputs).
    param_values : dict[str, float] | None
        Parameter values for substitution. Defaults to 0.0 for
        any unspecified parameter.
    """
    require_sympy()
    import sympy

    param_values = param_values or {}

    state_names = [s.name for s in model.states]
    input_names = [i.name for i in model.inputs]

    state_syms = {name: sympy.Symbol(name) for name in state_names}
    input_syms = {name: sympy.Symbol(name) for name in input_names}
    param_syms = {name: sympy.Symbol(name) for name in model.symbolic_params}

    all_syms: dict[str, Any] = {**state_syms, **input_syms, **param_syms}

    # Build substitution dict for operating point + params
    subs: dict[Any, float] = {}
    for i, name in enumerate(state_names):
        subs[state_syms[name]] = x0[i]
    for i, name in enumerate(input_names):
        subs[input_syms[name]] = u0[i]
    for name in model.symbolic_params:
        subs[param_syms[name]] = param_values.get(name, 0.0)

    # Parse state equations using safe parser (no eval, no builtins)
    from sympy.parsing.sympy_parser import parse_expr

    eq_map: dict[str, Any] = {}
    for eq in model.state_equations:
        eq_map[eq.state_name] = parse_expr(eq.expr_str, local_dict=all_syms)

    # A matrix: df_i/dx_j
    A = _jacobian(eq_map, state_names, state_syms, subs)

    # B matrix: df_i/du_j
    B = _jacobian(eq_map, state_names, input_syms, subs, col_names=input_names)

    # Parse output equations
    out_map: dict[str, Any] = {}
    output_names: list[str] = []
    for eq in model.output_equations:
        out_map[eq.sensor_name] = parse_expr(eq.expr_str, local_dict=all_syms)
        output_names.append(eq.sensor_name)

    # C matrix: dh_i/dx_j
    C = _jacobian(out_map, output_names, state_syms, subs, col_names=state_names)

    # D matrix: dh_i/du_j
    D = _jacobian(out_map, output_names, input_syms, subs, col_names=input_names)

    return LinearizedSystem(
        A=A,
        B=B,
        C=C,
        D=D,
        x0=list(x0),
        u0=list(u0),
        state_names=state_names,
        input_names=input_names,
        output_names=output_names,
    )


def _jacobian(
    eq_map: dict[str, Any],
    row_names: list[str],
    col_syms: dict[str, Any],
    subs: dict[Any, float],
    col_names: list[str] | None = None,
) -> list[list[float]]:
    """Compute a Jacobian matrix and evaluate at substitution point."""
    import sympy

    if col_names is None:
        col_names = list(col_syms.keys())

    rows: list[list[float]] = []
    for rname in row_names:
        expr = eq_map.get(rname, sympy.Integer(0))
        row: list[float] = []
        for cname in col_names:
            deriv = sympy.diff(expr, col_syms[cname])
            val = float(deriv.subs(subs))
            row.append(val)
        rows.append(row)
    return rows

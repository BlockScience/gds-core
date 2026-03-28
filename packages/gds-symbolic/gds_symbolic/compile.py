"""Compile symbolic equations to plain Python callables via sympy.lambdify."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_symbolic._compat import require_sympy

if TYPE_CHECKING:
    from gds_continuous.types import ODEFunction

    from gds_symbolic.model import SymbolicControlModel


def compile_to_ode(
    model: SymbolicControlModel,
) -> tuple[ODEFunction, list[str]]:
    """Compile a SymbolicControlModel's state equations to an ODEFunction.

    Returns
    -------
    ode_fn : ODEFunction
        Plain Python callable with signature ``(t, y, params) -> dy/dt``.
        No SymPy objects at runtime — fully lambdified.
    state_order : list[str]
        State variable names in the vector order used by ``ode_fn``.
    """
    require_sympy()
    import sympy

    state_order = [s.name for s in model.states]
    input_names = [i.name for i in model.inputs]

    # Build symbol table
    state_syms = {name: sympy.Symbol(name) for name in state_order}
    input_syms = {name: sympy.Symbol(name) for name in input_names}
    param_syms = {name: sympy.Symbol(name) for name in model.symbolic_params}

    all_syms = {**state_syms, **input_syms, **param_syms}

    # Parse expressions
    eq_map: dict[str, Any] = {}
    for eq in model.state_equations:
        expr = sympy.sympify(eq.expr_str, locals=all_syms)
        eq_map[eq.state_name] = expr

    # Build ordered RHS vector
    rhs_exprs = []
    for name in state_order:
        if name in eq_map:
            rhs_exprs.append(eq_map[name])
        else:
            # State with no equation: dx/dt = 0
            rhs_exprs.append(sympy.Integer(0))

    # Lambdify: args are ordered state vars + input vars + param vars
    ordered_symbols = (
        [state_syms[n] for n in state_order]
        + [input_syms[n] for n in input_names]
        + [param_syms[n] for n in model.symbolic_params]
    )
    rhs_lambda = sympy.lambdify(ordered_symbols, rhs_exprs, modules="math")

    n_states = len(state_order)

    def ode_fn(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
        # Unpack inputs from params dict
        input_vals = [params.get(name, 0.0) for name in input_names]
        param_vals = [params.get(name, 0.0) for name in model.symbolic_params]
        args = list(y[:n_states]) + input_vals + param_vals
        result = rhs_lambda(*args)
        if isinstance(result, (int, float)):
            return [float(result)]
        return [float(v) for v in result]

    return ode_fn, state_order

"""Hamiltonian mechanics and Pontryagin's Maximum Principle.

Derives the Hamiltonian H(x, p, u, t) = L(x, u) + p^T f(x, u) from
a SymbolicControlModel's state equations and a user-supplied Lagrangian.
Symbolically computes costate dynamics dp/dt = -dH/dx and produces an
augmented ODEModel for (x, p) integration.

This module connects GDS structural specification (ControlModel) to
optimal control theory via symbolic differentiation (SymPy).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from gds_domains.symbolic._compat import require_sympy


class HamiltonianSpec(BaseModel, frozen=True):
    """Specification for optimal control via Pontryagin's principle.

    Parameters
    ----------
    lagrangian
        Running cost L(x, u, t) as a SymPy-parseable string.
    terminal_cost
        Terminal cost Phi(x(T)) as a SymPy-parseable string.
        Empty string means no terminal cost.
    control_bounds
        Lower and upper bounds for each control input.
    free_final_time
        If True, H = 0 along optimal trajectories (transversality).
    """

    lagrangian: str
    terminal_cost: str = ""
    control_bounds: dict[str, tuple[float, float]] = {}
    free_final_time: bool = False


@dataclass(frozen=True)
class HamiltonianSystem:
    """Derived Hamiltonian system ready for integration.

    Produced by ``derive_hamiltonian()``. Contains the symbolic
    Hamiltonian, costate dynamics, and a compiled augmented ODE.

    Attributes
    ----------
    hamiltonian_expr
        Symbolic Hamiltonian H(x, p, u) as a string.
    costate_exprs
        Costate dynamics dp_i/dt = -dH/dx_i as strings.
    state_names
        Ordered state variable names.
    costate_names
        Ordered costate variable names (p_x1, p_x2, ...).
    augmented_ode
        Compiled ODE function for the augmented (x, p) system.
    augmented_names
        Full state vector names [x1, ..., xn, p_x1, ..., p_xn].
    """

    hamiltonian_expr: str
    costate_exprs: dict[str, str]
    state_names: list[str]
    costate_names: list[str]
    augmented_ode: Any  # ODEFunction
    augmented_names: list[str]


def derive_hamiltonian(
    state_equations: dict[str, str],
    state_names: list[str],
    input_names: list[str],
    param_names: list[str],
    spec: HamiltonianSpec,
) -> HamiltonianSystem:
    """Derive the Hamiltonian system from state dynamics and cost.

    Parameters
    ----------
    state_equations
        Map of state_name -> dx/dt expression string.
    state_names
        Ordered state variable names.
    input_names
        Control input variable names.
    param_names
        Parameter names (constants during integration).
    spec
        HamiltonianSpec with Lagrangian and constraints.

    Returns
    -------
    HamiltonianSystem with symbolic expressions and compiled ODE.
    """
    require_sympy()
    import sympy
    from sympy.parsing.sympy_parser import parse_expr

    # Build symbol tables
    state_syms = {n: sympy.Symbol(n) for n in state_names}
    costate_names = [f"p_{n}" for n in state_names]
    costate_syms = {n: sympy.Symbol(n) for n in costate_names}
    input_syms = {n: sympy.Symbol(n) for n in input_names}
    param_syms = {n: sympy.Symbol(n) for n in param_names}
    t_sym = sympy.Symbol("t")

    all_syms = {
        **state_syms,
        **costate_syms,
        **input_syms,
        **param_syms,
        "t": t_sym,
    }

    # Parse state dynamics f(x, u)
    f_exprs = {}
    for name in state_names:
        if name in state_equations:
            f_exprs[name] = parse_expr(state_equations[name], local_dict=all_syms)
        else:
            f_exprs[name] = sympy.Integer(0)

    # Parse Lagrangian L(x, u, t)
    lagrangian = parse_expr(spec.lagrangian, local_dict=all_syms)

    # Hamiltonian: H = L + p^T f
    hamiltonian = lagrangian
    for i, name in enumerate(state_names):
        hamiltonian += costate_syms[costate_names[i]] * f_exprs[name]

    # Costate dynamics: dp_i/dt = -dH/dx_i
    costate_dynamics = {}
    for i, name in enumerate(state_names):
        dp_dt = -sympy.diff(hamiltonian, state_syms[name])
        costate_dynamics[costate_names[i]] = dp_dt

    # Compile augmented ODE: [dx/dt, dp/dt]
    augmented_names = state_names + costate_names
    # Build ordered expression vector
    rhs_exprs = []
    for name in state_names:
        rhs_exprs.append(f_exprs[name])
    for cname in costate_names:
        rhs_exprs.append(costate_dynamics[cname])

    # Lambdify
    ordered_symbols = (
        [state_syms[n] for n in state_names]
        + [costate_syms[n] for n in costate_names]
        + [input_syms[n] for n in input_names]
        + [param_syms[n] for n in param_names]
    )
    rhs_lambda = sympy.lambdify(ordered_symbols, rhs_exprs, modules="math")

    def augmented_ode(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
        input_vals = [params.get(n, 0.0) for n in input_names]
        param_vals = [params.get(n, 0.0) for n in param_names]
        args = list(y) + input_vals + param_vals
        result = rhs_lambda(*args)
        if isinstance(result, (int, float)):
            return [float(result)]
        return [float(v) for v in result]

    return HamiltonianSystem(
        hamiltonian_expr=str(hamiltonian),
        costate_exprs={k: str(v) for k, v in costate_dynamics.items()},
        state_names=state_names,
        costate_names=costate_names,
        augmented_ode=augmented_ode,
        augmented_names=augmented_names,
    )


def derive_from_model(
    model: Any,
    spec: HamiltonianSpec,
) -> HamiltonianSystem:
    """Derive Hamiltonian from a SymbolicControlModel.

    Convenience wrapper that extracts state equations, names, and
    parameters from the model.
    """
    state_names = [s.name for s in model.states]
    input_names = [i.name for i in model.inputs]
    param_names = list(model.symbolic_params)
    state_equations = {eq.state_name: eq.expr_str for eq in model.state_equations}
    return derive_hamiltonian(
        state_equations=state_equations,
        state_names=state_names,
        input_names=input_names,
        param_names=param_names,
        spec=spec,
    )


def verify_conservation(
    times: list[float],
    states: list[list[float]],
    hamiltonian_fn: Any,
    params: dict[str, Any],
    *,
    tolerance: float = 1e-4,
) -> tuple[bool, float]:
    """Verify Hamiltonian conservation along a trajectory.

    For free-final-time problems, H should be 0.
    For fixed-final-time problems, H should be constant.

    Parameters
    ----------
    times
        Time points.
    states
        State vectors at each time point (augmented: [x, p]).
    hamiltonian_fn
        Callable: (t, y, params) -> H value.
    params
        Parameter dict.
    tolerance
        Maximum allowed variation in H.

    Returns
    -------
    (conserved, max_variation)
    """
    h_values = [
        hamiltonian_fn(t, y, params) for t, y in zip(times, states, strict=True)
    ]
    if not h_values:
        return True, 0.0
    h0 = h_values[0]
    max_var = max(abs(h - h0) for h in h_values)
    return max_var < tolerance, max_var

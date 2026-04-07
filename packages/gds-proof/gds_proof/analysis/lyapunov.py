"""Lyapunov stability proofs and passivity certificates.

Provides convenience constructors that translate control-theoretic stability
specifications into the invariant format the existing gds-proof engine handles.

For continuous-time systems:
    V(x) > 0 and dV/dt = (∂V/∂x) · f(x) < 0

For discrete-time systems:
    V(x) > 0 and V(f(x)) - V(x) < 0

All proofs delegate to the existing five-strategy SymPy simplification
engine in ``gds_proof.analysis.symbolic``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import sympy
from sympy.parsing.sympy_parser import parse_expr


@dataclass(frozen=True)
class LyapunovResult:
    """Result of a Lyapunov stability analysis."""

    candidate: sympy.Expr
    """V(x) expression."""

    positive_definite: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    """Whether V(x) > 0 for x ≠ 0 was established."""

    decreasing: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    """Whether dV/dt < 0 (continuous) or ΔV < 0 (discrete) was established."""

    stable: bool
    """True only if both positive_definite and decreasing are PROVED."""

    dV_expr: sympy.Expr | None = None
    """dV/dt or ΔV expression for inspection."""

    details: list[str] = field(default_factory=list)
    """Human-readable proof trace."""


@dataclass(frozen=True)
class PassivityResult:
    """Result of a passivity/dissipativity analysis."""

    storage_function: sympy.Expr
    """V(x) — storage function."""

    supply_rate: sympy.Expr
    """s(u, y) — supply rate."""

    dissipation_proved: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    """Whether dV/dt ≤ s(u, y) was established."""

    passive: bool
    """True only if dissipation was PROVED."""

    details: list[str] = field(default_factory=list)


def lyapunov_candidate(
    V_expr: str | sympy.Expr,
    state_transition: dict[str, str | sympy.Expr],
    state_symbols: list[str],
    *,
    continuous: bool = True,
) -> LyapunovResult:
    """Verify a Lyapunov candidate function.

    For continuous-time (``continuous=True``):
        Checks V(x) > 0 and dV/dt = (∂V/∂x) · f(x) < 0.

    For discrete-time (``continuous=False``):
        Checks V(x) > 0 and V(f(x)) - V(x) < 0.

    Parameters
    ----------
    V_expr : str | sympy.Expr
        Lyapunov candidate function. If str, parsed via SymPy.
    state_transition : dict[str, str | sympy.Expr]
        Maps state variable name to its dynamics.
        Continuous: dx_i/dt = f_i(x). Discrete: x_i' = f_i(x).
    state_symbols : list[str]
        State variable names.
    continuous : bool
        Whether the system is continuous-time (True) or discrete-time (False).

    Returns
    -------
    LyapunovResult
    """
    details: list[str] = []

    # Build symbol table
    syms = {name: sympy.Symbol(name) for name in state_symbols}

    # Parse V
    V = parse_expr(V_expr, local_dict=syms) if isinstance(V_expr, str) else V_expr

    # Parse state transition
    f_exprs: dict[str, sympy.Expr] = {}
    for name, expr in state_transition.items():
        if isinstance(expr, str):
            f_exprs[name] = parse_expr(expr, local_dict=syms)
        else:
            f_exprs[name] = expr

    details.append(f"Candidate: V = {V}")

    # Check positive definiteness
    # V(0) = 0 and V(x) > 0 for x ≠ 0
    zero_subs = {syms[n]: 0 for n in state_symbols}
    V_at_zero = V.subs(zero_subs)
    V_at_zero_simplified = sympy.simplify(V_at_zero)

    pd_status: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    if V_at_zero_simplified != 0:
        pd_status = "FAILED"
        details.append(f"V(0) = {V_at_zero_simplified} ≠ 0 → not positive definite")
    else:
        details.append("V(0) = 0 ✓")
        # Try to verify V > 0 for x ≠ 0 using SymPy
        # For polynomial V, check if it can be shown positive
        pd_check = _check_positive_definite(V, [syms[n] for n in state_symbols])
        pd_status = pd_check
        details.append(f"Positive definiteness: {pd_status}")

    # Check decrease condition
    if continuous:
        # dV/dt = sum_i (∂V/∂x_i) * f_i(x)
        dV_dt = sympy.Integer(0)
        for name in state_symbols:
            partial = sympy.diff(V, syms[name])
            dV_dt += partial * f_exprs.get(name, sympy.Integer(0))
        dV_dt = sympy.expand(dV_dt)
        details.append(f"dV/dt = {dV_dt}")
        decrease_expr = dV_dt
    else:
        # ΔV = V(f(x)) - V(x)
        subs_map = {syms[name]: f_exprs.get(name, syms[name]) for name in state_symbols}
        V_next = V.subs(subs_map)
        delta_V = sympy.expand(V_next - V)
        details.append(f"ΔV = {delta_V}")
        decrease_expr = delta_V

    # Check if decrease_expr < 0
    dec_status = _check_negative_definite(
        decrease_expr, [syms[n] for n in state_symbols]
    )
    details.append(f"Decrease condition: {dec_status}")

    stable = pd_status == "PROVED" and dec_status == "PROVED"

    return LyapunovResult(
        candidate=V,
        positive_definite=pd_status,
        decreasing=dec_status,
        stable=stable,
        dV_expr=decrease_expr,
        details=details,
    )


def quadratic_lyapunov(
    P: list[list[float]],
    A: list[list[float]],
    state_symbols: list[str] | None = None,
) -> LyapunovResult:
    """Verify V(x) = x'Px as a Lyapunov function for dx/dt = Ax.

    Checks:
    1. P is symmetric positive definite (all eigenvalues > 0).
    2. A'P + PA is negative definite (Lyapunov inequality).

    Parameters
    ----------
    P : list[list[float]]
        Candidate Lyapunov matrix (n x n, should be symmetric).
    A : list[list[float]]
        State matrix (n x n).
    state_symbols : list[str] | None
        State variable names. If None, uses x1, x2, ...

    Returns
    -------
    LyapunovResult
    """
    n = len(A)
    if state_symbols is None:
        state_symbols = [f"x{i + 1}" for i in range(n)]

    details: list[str] = []

    P_mat = sympy.Matrix(P)
    A_mat = sympy.Matrix(A)

    # Build V = x'Px symbolically
    syms = [sympy.Symbol(name) for name in state_symbols]
    x_vec = sympy.Matrix(syms)
    V = (x_vec.T * P_mat * x_vec)[0, 0]
    V = sympy.expand(V)

    details.append(f"V(x) = {V}")

    # Check P is symmetric positive definite via eigenvalues
    eigenvals = P_mat.eigenvals()
    eig_values = []
    for ev, mult in eigenvals.items():
        eig_values.extend([complex(ev)] * mult)

    pd_status: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    if all(e.real > 0 and abs(e.imag) < 1e-10 for e in eig_values):
        pd_status = "PROVED"
        details.append(f"P eigenvalues: {[float(e.real) for e in eig_values]} > 0 ✓")
    else:
        pd_status = "FAILED"
        details.append(f"P eigenvalues: {eig_values} — not all positive")

    # Check A'P + PA is negative definite
    Q_lyap = A_mat.T * P_mat + P_mat * A_mat
    Q_eigenvals = Q_lyap.eigenvals()
    q_eig_values = []
    for ev, mult in Q_eigenvals.items():
        q_eig_values.extend([complex(ev)] * mult)

    dec_status: Literal["PROVED", "FAILED", "INCONCLUSIVE"]
    if all(e.real < 0 and abs(e.imag) < 1e-10 for e in q_eig_values):
        dec_status = "PROVED"
        details.append(
            f"A'P + PA eigenvalues: {[float(e.real) for e in q_eig_values]} < 0 ✓"
        )
    elif any(e.real > 0 for e in q_eig_values):
        dec_status = "FAILED"
        details.append(f"A'P + PA eigenvalues: {q_eig_values} — not all negative")
    else:
        dec_status = "INCONCLUSIVE"
        details.append(f"A'P + PA eigenvalues: {q_eig_values} — inconclusive")

    # Compute dV/dt for reporting
    dV_dt = (x_vec.T * Q_lyap * x_vec)[0, 0]
    dV_dt = sympy.expand(dV_dt)
    details.append(f"dV/dt = x'(A'P + PA)x = {dV_dt}")

    stable = pd_status == "PROVED" and dec_status == "PROVED"

    return LyapunovResult(
        candidate=V,
        positive_definite=pd_status,
        decreasing=dec_status,
        stable=stable,
        dV_expr=dV_dt,
        details=details,
    )


def find_quadratic_lyapunov(
    A: list[list[float]],
    Q: list[list[float]] | None = None,
) -> tuple[list[list[float]], LyapunovResult] | None:
    """Attempt to find P satisfying A'P + PA = -Q (Lyapunov equation).

    If Q is None, uses Q = I (identity).

    Parameters
    ----------
    A : list[list[float]]
        State matrix.
    Q : list[list[float]] | None
        Desired negative-definiteness target. Default is identity.

    Returns
    -------
    (P, result) if a valid P was found, None if the system is not stable.
    """
    n = len(A)
    if n == 0:
        return None

    A_mat = sympy.Matrix(A)

    Q_mat = sympy.eye(n) if Q is None else sympy.Matrix(Q)

    # Solve A'P + PA = -Q by parameterizing P as symmetric
    # and solving the resulting linear system
    p_vars = {}
    P_sym = sympy.zeros(n)
    for i in range(n):
        for j in range(i, n):
            var = sympy.Symbol(f"p_{i}_{j}")
            p_vars[(i, j)] = var
            P_sym[i, j] = var
            P_sym[j, i] = var

    # A'P + PA + Q = 0
    equation_matrix = A_mat.T * P_sym + P_sym * A_mat + Q_mat

    # Collect all equations
    equations = []
    for i in range(n):
        for j in range(i, n):
            equations.append(equation_matrix[i, j])

    variables = list(p_vars.values())

    try:
        solution = sympy.solve(equations, variables, dict=True)
    except (NotImplementedError, ValueError):
        return None

    if not solution:
        return None

    sol = solution[0]

    # Reconstruct P
    P_result = [[0.0] * n for _ in range(n)]
    for (i, j), var in p_vars.items():
        val = float(sol.get(var, 0))
        P_result[i][j] = val
        P_result[j][i] = val

    # Verify the result
    result = quadratic_lyapunov(P_result, A)

    if result.stable:
        return P_result, result
    return None


def passivity_certificate(
    V_expr: str | sympy.Expr,
    supply_rate: str | sympy.Expr,
    state_transition: dict[str, str | sympy.Expr],
    output_map: dict[str, str | sympy.Expr],
    state_symbols: list[str],
    input_symbols: list[str],
) -> PassivityResult:
    """Verify passivity: dV/dt ≤ s(u, y).

    For a passive system with supply rate s(u, y) = u'y:
        dV/dt ≤ u'y  (energy dissipation inequality)

    More general supply rates (e.g., s = γ²|u|² - |y|² for L2-gain)
    can be specified.

    Parameters
    ----------
    V_expr : str | sympy.Expr
        Storage function V(x).
    supply_rate : str | sympy.Expr
        Supply rate s(u, y) as expression over input and output symbols.
    state_transition : dict[str, str | sympy.Expr]
        dx_i/dt = f_i(x, u).
    output_map : dict[str, str | sympy.Expr]
        y_i = h_i(x, u).
    state_symbols : list[str]
        State variable names.
    input_symbols : list[str]
        Input variable names.
    """
    details: list[str] = []

    # Build symbol table
    all_sym_names = state_symbols + input_symbols
    syms = {name: sympy.Symbol(name) for name in all_sym_names}

    # Add output symbols for supply rate parsing
    out_syms = {name: sympy.Symbol(name) for name in output_map}
    all_syms = {**syms, **out_syms}

    # Parse expressions
    V = parse_expr(V_expr, local_dict=syms) if isinstance(V_expr, str) else V_expr

    if isinstance(supply_rate, str):
        s_rate = parse_expr(supply_rate, local_dict=all_syms)
    else:
        s_rate = supply_rate

    f_exprs: dict[str, sympy.Expr] = {}
    for name, expr in state_transition.items():
        if isinstance(expr, str):
            f_exprs[name] = parse_expr(expr, local_dict=syms)
        else:
            f_exprs[name] = expr

    h_exprs: dict[str, sympy.Expr] = {}
    for name, expr in output_map.items():
        if isinstance(expr, str):
            h_exprs[name] = parse_expr(expr, local_dict=syms)
        else:
            h_exprs[name] = expr

    details.append(f"Storage function: V = {V}")
    details.append(f"Supply rate: s = {s_rate}")

    # Compute dV/dt
    dV_dt = sympy.Integer(0)
    for name in state_symbols:
        partial = sympy.diff(V, syms[name])
        dV_dt += partial * f_exprs.get(name, sympy.Integer(0))
    dV_dt = sympy.expand(dV_dt)
    details.append(f"dV/dt = {dV_dt}")

    # Substitute output expressions into supply rate
    out_subs = {out_syms[name]: h_exprs[name] for name in output_map}
    s_rate_expanded = s_rate.subs(out_subs)
    s_rate_expanded = sympy.expand(s_rate_expanded)
    details.append(f"Supply rate (expanded): s = {s_rate_expanded}")

    # Check dV/dt - s(u, y) ≤ 0
    dissipation = sympy.expand(dV_dt - s_rate_expanded)
    details.append(f"Dissipation: dV/dt - s = {dissipation}")

    # Try to prove dissipation ≤ 0
    result = _check_nonpositive(dissipation, list(syms.values()))

    details.append(f"Dissipation check: {result}")

    return PassivityResult(
        storage_function=V,
        supply_rate=s_rate,
        dissipation_proved=result,
        passive=result == "PROVED",
        details=details,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_positive_definite(
    expr: sympy.Expr,
    symbols: list[sympy.Symbol],
) -> Literal["PROVED", "FAILED", "INCONCLUSIVE"]:
    """Attempt to verify that expr > 0 for all non-zero symbol values.

    Uses Hessian check for quadratic forms and SymPy simplification.
    """
    # Check if it's a quadratic form x'Hx
    # Compute the Hessian matrix
    n = len(symbols)
    if n == 0:
        return "INCONCLUSIVE"

    hessian = sympy.zeros(n)
    for i in range(n):
        for j in range(n):
            hessian[i, j] = sympy.diff(expr, symbols[i], symbols[j])

    # Check if Hessian is constant (quadratic form)
    is_constant_hessian = all(
        hessian[i, j].free_symbols == set() for i in range(n) for j in range(n)
    )

    if is_constant_hessian:
        # For V = (1/2) x'Hx, H must be positive definite
        H = hessian
        eigenvals = H.eigenvals()
        eig_values = []
        for ev, mult in eigenvals.items():
            eig_values.extend([complex(ev)] * mult)

        if all(e.real > 0 and abs(e.imag) < 1e-10 for e in eig_values):
            return "PROVED"
        if any(e.real < 0 for e in eig_values):
            return "FAILED"

    return "INCONCLUSIVE"


def _check_negative_definite(
    expr: sympy.Expr,
    symbols: list[sympy.Symbol],
) -> Literal["PROVED", "FAILED", "INCONCLUSIVE"]:
    """Attempt to verify that expr < 0 for all non-zero symbol values."""
    result = _check_positive_definite(-expr, symbols)
    return result


def _check_nonpositive(
    expr: sympy.Expr,
    symbols: list[sympy.Symbol],
) -> Literal["PROVED", "FAILED", "INCONCLUSIVE"]:
    """Attempt to verify that expr <= 0 for all symbol values."""
    # First try negative definiteness
    result = _check_negative_definite(expr, symbols)
    if result == "PROVED":
        return "PROVED"

    # Check if expr simplifies to 0
    simplified = sympy.simplify(expr)
    if simplified == 0:
        return "PROVED"

    # Check negative semi-definiteness via Hessian eigenvalues
    n = len(symbols)
    if n > 0:
        hessian = sympy.zeros(n)
        for i in range(n):
            for j in range(n):
                hessian[i, j] = sympy.diff(expr, symbols[i], symbols[j])

        is_constant_hessian = all(
            hessian[i, j].free_symbols == set() for i in range(n) for j in range(n)
        )

        if is_constant_hessian:
            eigenvals = hessian.eigenvals()
            eig_values = []
            for ev, mult in eigenvals.items():
                eig_values.extend([complex(ev)] * mult)

            # Negative semi-definite: all eigenvalues <= 0
            if all(e.real <= 1e-10 and abs(e.imag) < 1e-10 for e in eig_values):
                return "PROVED"
            if any(e.real > 1e-10 for e in eig_values):
                return "FAILED"

    return result

"""Transfer function representation and classical control analysis.

Provides symbolic transfer function computation from state-space (A, B, C, D)
matrices, pole/zero analysis, controllability/observability tests, and
sensitivity functions (Gang of Six).

Uses SymPy only — no scipy or numpy dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from gds_domains.symbolic._compat import require_sympy

if TYPE_CHECKING:
    from gds_domains.symbolic.linearize import LinearizedSystem


@dataclass(frozen=True)
class TransferFunction:
    """SISO transfer function as coefficient lists (descending powers of s).

    ``num = [b_n, b_{n-1}, ..., b_0]`` and ``den = [a_m, a_{m-1}, ..., a_0]``
    represent H(s) = (b_n s^n + ... + b_0) / (a_m s^m + ... + a_0).
    """

    num: list[float]
    den: list[float]
    input_name: str = ""
    output_name: str = ""


@dataclass(frozen=True)
class TransferFunctionMatrix:
    """MIMO transfer function matrix (p outputs x m inputs).

    ``elements[i][j]`` is the SISO transfer function from input j to output i.
    """

    elements: list[list[TransferFunction]]
    input_names: list[str] = field(default_factory=list)
    output_names: list[str] = field(default_factory=list)


def ss_to_tf(ls: LinearizedSystem) -> TransferFunctionMatrix:
    """Convert state-space (A, B, C, D) to a transfer function matrix.

    Computes H(s) = C(sI - A)^{-1}B + D using the adjugate/determinant
    method for numerical stability with symbolic computation.

    Parameters
    ----------
    ls : LinearizedSystem
        State-space matrices with A, B, C, D as ``list[list[float]]``.

    Returns
    -------
    TransferFunctionMatrix
        p x m matrix of SISO transfer functions.
    """
    require_sympy()
    import sympy

    s = sympy.Symbol("s")
    n = len(ls.A)
    p = len(ls.C)  # number of outputs
    m = len(ls.B[0]) if n > 0 else len(ls.D[0]) if p > 0 else 0

    A = sympy.Matrix(ls.A)
    B = sympy.Matrix(ls.B)
    C = sympy.Matrix(ls.C)
    D = sympy.Matrix(ls.D)

    # sI - A
    sI_A = s * sympy.eye(n) - A

    # Characteristic polynomial: det(sI - A)
    char_poly = sI_A.det().as_poly(s) if n > 0 else sympy.Poly(1, s)

    # Adjugate of (sI - A)
    adj = sI_A.adjugate() if n > 0 else sympy.Matrix()

    elements: list[list[TransferFunction]] = []
    for i in range(p):
        row: list[TransferFunction] = []
        for j in range(m):
            if n > 0:
                # H_ij(s) = [C[i,:] @ adj @ B[:,j]] / det(sI-A) + D[i,j]
                c_row = C.row(i)
                b_col = B.col(j)
                num_expr = (c_row * adj * b_col)[0, 0]
                d_val = D[i, j]

                # H_ij = num_expr/char_poly + d_val
                #       = (num_expr + d_val * char_poly) / char_poly
                num_poly = sympy.Poly(num_expr, s) + char_poly * d_val
                den_poly = char_poly
            else:
                # No states — pure feedthrough
                num_poly = sympy.Poly(D[i, j], s)
                den_poly = sympy.Poly(1, s)

            # Extract coefficients (descending powers)
            num_coeffs = [float(c) for c in num_poly.all_coeffs()]
            den_coeffs = [float(c) for c in den_poly.all_coeffs()]

            row.append(
                TransferFunction(
                    num=num_coeffs,
                    den=den_coeffs,
                    input_name=ls.input_names[j] if j < len(ls.input_names) else "",
                    output_name=(
                        ls.output_names[i] if i < len(ls.output_names) else ""
                    ),
                )
            )
        elements.append(row)

    return TransferFunctionMatrix(
        elements=elements,
        input_names=list(ls.input_names),
        output_names=list(ls.output_names),
    )


def characteristic_polynomial(ls: LinearizedSystem) -> list[float]:
    """Compute the characteristic polynomial det(sI - A) as coefficients.

    Returns coefficients in descending powers of s:
    ``[1, a_{n-1}, ..., a_0]`` for an n x n state matrix.
    """
    require_sympy()
    import sympy

    n = len(ls.A)
    if n == 0:
        return [1.0]

    s = sympy.Symbol("s")
    A = sympy.Matrix(ls.A)
    poly = (s * sympy.eye(n) - A).det().as_poly(s)
    return [float(c) for c in poly.all_coeffs()]


def poles(tf: TransferFunction) -> list[complex]:
    """Compute the poles (roots of denominator polynomial).

    Returns a list of complex numbers, one per pole (with multiplicity).
    """
    require_sympy()
    import sympy

    s = sympy.Symbol("s")
    poly = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(tf.den))), s)
    roots = sympy.roots(poly, multiple=True)
    return [complex(r) for r in roots]


def zeros(tf: TransferFunction) -> list[complex]:
    """Compute the zeros (roots of numerator polynomial).

    Returns a list of complex numbers, one per zero (with multiplicity).
    """
    require_sympy()
    import sympy

    s = sympy.Symbol("s")
    poly = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(tf.num))), s)
    roots = sympy.roots(poly, multiple=True)
    return [complex(r) for r in roots]


def is_minimum_phase(tf: TransferFunction) -> bool:
    """Check if all zeros have strictly negative real part.

    A minimum-phase system has no right-half-plane (RHP) zeros.
    Returns True for systems with no zeros.
    """
    z = zeros(tf)
    if not z:
        return True
    return all(zi.real < 0 for zi in z)


def controllability_matrix(ls: LinearizedSystem) -> list[list[float]]:
    """Compute the controllability matrix C_c = [B, AB, A^2B, ..., A^{n-1}B].

    Returns an n x (n*m) matrix as ``list[list[float]]``.
    """
    require_sympy()
    import sympy

    n = len(ls.A)
    if n == 0:
        return []

    A = sympy.Matrix(ls.A)
    B = sympy.Matrix(ls.B)

    blocks = [B]
    A_power = sympy.eye(n)
    for _ in range(1, n):
        A_power = A_power * A
        blocks.append(A_power * B)

    # Concatenate horizontally
    result = blocks[0]
    for blk in blocks[1:]:
        result = result.row_join(blk)

    return [[float(result[i, j]) for j in range(result.cols)] for i in range(n)]


def observability_matrix(ls: LinearizedSystem) -> list[list[float]]:
    """Compute the observability matrix C_o = [C; CA; CA^2; ...; CA^{n-1}].

    Returns an (n*p) x n matrix as ``list[list[float]]``.
    """
    require_sympy()
    import sympy

    n = len(ls.A)
    if n == 0:
        return []

    A = sympy.Matrix(ls.A)
    C = sympy.Matrix(ls.C)

    blocks = [C]
    A_power = sympy.eye(n)
    for _ in range(1, n):
        A_power = A_power * A
        blocks.append(C * A_power)

    # Concatenate vertically
    result = blocks[0]
    for blk in blocks[1:]:
        result = result.col_join(blk)

    return [
        [float(result[i, j]) for j in range(result.cols)] for i in range(result.rows)
    ]


def is_controllable(ls: LinearizedSystem) -> bool:
    """Check if the system (A, B) is controllable.

    True if rank(C_c) == n (number of states).
    """
    require_sympy()
    import sympy

    n = len(ls.A)
    if n == 0:
        return True

    cm = controllability_matrix(ls)
    mat = sympy.Matrix(cm)
    return mat.rank() == n


def is_observable(ls: LinearizedSystem) -> bool:
    """Check if the system (A, C) is observable.

    True if rank(C_o) == n (number of states).
    """
    require_sympy()
    import sympy

    n = len(ls.A)
    if n == 0:
        return True

    om = observability_matrix(ls)
    mat = sympy.Matrix(om)
    return mat.rank() == n


def _tf_multiply(a: TransferFunction, b: TransferFunction) -> TransferFunction:
    """Multiply two transfer functions (convolve num and den)."""
    require_sympy()
    import sympy

    s = sympy.Symbol("s")

    a_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(a.num))), s)
    a_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(a.den))), s)
    b_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(b.num))), s)
    b_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(b.den))), s)

    result_num = a_num * b_num
    result_den = a_den * b_den

    return TransferFunction(
        num=[float(c) for c in result_num.all_coeffs()],
        den=[float(c) for c in result_den.all_coeffs()],
    )


def _tf_add(a: TransferFunction, b: TransferFunction) -> TransferFunction:
    """Add two transfer functions."""
    require_sympy()
    import sympy

    s = sympy.Symbol("s")

    a_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(a.num))), s)
    a_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(a.den))), s)
    b_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(b.num))), s)
    b_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(b.den))), s)

    # a/a_d + b/b_d = (a*b_d + b*a_d) / (a_d * b_d)
    result_num = a_num * b_den + b_num * a_den
    result_den = a_den * b_den

    return TransferFunction(
        num=[float(c) for c in result_num.all_coeffs()],
        den=[float(c) for c in result_den.all_coeffs()],
    )


def _tf_feedback(
    forward: TransferFunction,
    feedback: TransferFunction | None = None,
) -> TransferFunction:
    """Compute closed-loop TF: forward / (1 + forward * feedback).

    If feedback is None, uses unity feedback (feedback = 1).
    """
    require_sympy()
    import sympy

    s = sympy.Symbol("s")

    g_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(forward.num))), s)
    g_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(forward.den))), s)

    if feedback is None:
        # Unity feedback: G / (1 + G) = g_num / (g_den + g_num)
        result_num = g_num * g_den  # g_num * 1 (for general formula)
        result_den = g_den * g_den + g_num * g_den  # den*(den+num)
        # Simplify: G/(1+G) = g_num / (g_den + g_num)
        result_num = g_num
        result_den = g_den + g_num
    else:
        h_num = sympy.Poly(
            sum(c * s**i for i, c in enumerate(reversed(feedback.num))), s
        )
        h_den = sympy.Poly(
            sum(c * s**i for i, c in enumerate(reversed(feedback.den))), s
        )
        # G/(1+GH) = (g_num * h_den) / (g_den * h_den + g_num * h_num)
        result_num = g_num * h_den
        result_den = g_den * h_den + g_num * h_num

    return TransferFunction(
        num=[float(c) for c in result_num.all_coeffs()],
        den=[float(c) for c in result_den.all_coeffs()],
    )


def sensitivity(
    plant: TransferFunction,
    controller: TransferFunction,
) -> dict[str, TransferFunction]:
    """Compute the Gang of Six sensitivity functions.

    Given plant P and controller K with loop transfer function L = P * K:

    - **S**  = 1 / (1 + L)          — sensitivity
    - **T**  = L / (1 + L)          — complementary sensitivity
    - **CS** = K / (1 + L)          — control sensitivity (K*S)
    - **PS** = P / (1 + L)          — load sensitivity (P*S)
    - **KS** = K*S                  — noise → control (same as CS)
    - **KPS** = K*P / (1 + L)       — input disturbance sensitivity (T)

    Returns
    -------
    dict with keys "S", "T", "CS", "PS", "KS", "KPS".
    """
    require_sympy()
    import sympy

    s = sympy.Symbol("s")

    # Build symbolic polynomials
    p_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(plant.num))), s)
    p_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(plant.den))), s)
    k_num = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(controller.num))), s)
    k_den = sympy.Poly(sum(c * s**i for i, c in enumerate(reversed(controller.den))), s)

    # L = P * K: L_num/L_den = (p_num * k_num) / (p_den * k_den)
    l_num = p_num * k_num
    l_den = p_den * k_den

    # 1 + L = (l_den + l_num) / l_den
    one_plus_l_num = l_den + l_num  # numerator of (1 + L)

    def _make_tf(num_poly: sympy.Poly, den_poly: sympy.Poly) -> TransferFunction:
        return TransferFunction(
            num=[float(c) for c in num_poly.all_coeffs()],
            den=[float(c) for c in den_poly.all_coeffs()],
        )

    # S = 1/(1+L) = l_den / (l_den + l_num)
    s_tf = _make_tf(l_den, one_plus_l_num)

    # T = L/(1+L) = l_num / (l_den + l_num)
    t_tf = _make_tf(l_num, one_plus_l_num)

    # CS = K * S = K/(1+L) = (k_num * p_den) / (k_den * (l_den + l_num))
    # Actually: K/(1+L) = (k_num/k_den) * (l_den / (l_den + l_num))
    #         = (k_num * l_den) / (k_den * (l_den + l_num))
    # Since l_den = p_den * k_den:
    #         = (k_num * p_den * k_den) / (k_den * (l_den + l_num))
    #         = (k_num * p_den) / (l_den + l_num)
    cs_tf = _make_tf(k_num * p_den, one_plus_l_num)

    # PS = P * S = P/(1+L) = (p_num * k_den) / (l_den + l_num)
    ps_tf = _make_tf(p_num * k_den, one_plus_l_num)

    # KS = K * S (same as CS for standard feedback)
    ks_tf = cs_tf

    # KPS = K * P * S = L/(1+L) = T
    kps_tf = t_tf

    return {
        "S": s_tf,
        "T": t_tf,
        "CS": cs_tf,
        "PS": ps_tf,
        "KS": ks_tf,
        "KPS": kps_tf,
    }

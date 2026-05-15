"""Padé approximation for time delay modeling.

Provides rational polynomial approximations of pure time delays e^{-sτ},
enabling frequency-domain analysis of systems with transport delays.

Uses SymPy only — no scipy or numpy dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_domains.symbolic._compat import require_sympy

if TYPE_CHECKING:
    from gds_domains.symbolic.transfer import TransferFunction


def pade_approximation(delay: float, order: int = 3) -> TransferFunction:
    """Compute an (N, N) Padé approximation of e^{-sτ}.

    The Padé approximant is an all-pass rational function that matches
    the Taylor expansion of e^{-sτ} up to order 2N+1. It has N zeros
    in the right half-plane and N poles in the left half-plane.

    Parameters
    ----------
    delay : float
        Time delay τ in seconds. Must be > 0.
    order : int
        Approximation order N (1..8 typical). Higher order = more accurate
        but adds RHP zeros that complicate root locus analysis.

    Returns
    -------
    TransferFunction
        Rational approximation with ``num`` and ``den`` coefficient lists.

    Raises
    ------
    ValueError
        If delay <= 0 or order < 1.
    """
    from gds_domains.symbolic.transfer import TransferFunction

    if delay <= 0:
        raise ValueError(f"delay must be > 0, got {delay}")
    if order < 1:
        raise ValueError(f"order must be >= 1, got {order}")

    require_sympy()
    import sympy

    s = sympy.Symbol("s")
    tau = sympy.Rational(delay).limit_denominator(10**12)

    # Padé coefficients using the closed form:
    # P_n(s) = sum_{k=0}^{n} (-1)^k * C(n,k) * (s*tau)^k * (2n-k)! * n!
    #          / ((2n)! * k!)
    # Q_n(s) = sum_{k=0}^{n} C(n,k) * (s*tau)^k * (2n-k)! * n!
    #          / ((2n)! * k!)
    #
    # Simplified: coefficient of (s*tau)^k in numerator and denominator:
    #   a_k = (2n - k)! * n! / ((2n)! * k! * (n - k)!)
    # Numerator has alternating signs.

    n = order
    num_poly = sympy.Integer(0)
    den_poly = sympy.Integer(0)

    for k in range(n + 1):
        coeff = (
            sympy.factorial(2 * n - k)
            * sympy.factorial(n)
            / (sympy.factorial(2 * n) * sympy.factorial(k) * sympy.factorial(n - k))
        )
        term = coeff * (s * tau) ** k
        den_poly += term
        num_poly += (-1) ** k * term

    num_sympy = sympy.Poly(num_poly, s)
    den_sympy = sympy.Poly(den_poly, s)

    return TransferFunction(
        num=[float(c) for c in num_sympy.all_coeffs()],
        den=[float(c) for c in den_sympy.all_coeffs()],
    )


def delay_system(
    tf: TransferFunction,
    delay: float,
    order: int = 3,
) -> TransferFunction:
    """Cascade a transfer function with a Padé-approximated delay.

    Computes H_delayed(s) = H(s) * Padé(s, τ) by multiplying
    the numerator and denominator polynomials.

    Parameters
    ----------
    tf : TransferFunction
        Original transfer function.
    delay : float
        Time delay τ in seconds.
    order : int
        Padé approximation order.

    Returns
    -------
    TransferFunction
        H(s) * Padé(s, τ) as a single transfer function.
    """
    from gds_domains.symbolic.transfer import _tf_multiply

    if delay <= 0:
        raise ValueError(f"delay must be > 0, got {delay}")

    pade_tf = pade_approximation(delay, order)
    return _tf_multiply(tf, pade_tf)

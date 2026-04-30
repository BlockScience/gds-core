"""Numerical linear systems analysis, discretization, and controller synthesis.

Provides eigenvalue stability checks, frequency response computation,
stability margins, continuous-to-discrete conversion, LQR/Kalman synthesis,
and gain scheduling.

All functions accept ``list[list[float]]`` matrices (matching
``LinearizedSystem`` field types from gds-domains/symbolic) and return
plain Python types. Numpy/scipy are internal implementation details.

Requires ``gds-analysis[continuous]`` (scipy + numpy).
"""

from __future__ import annotations

from typing import Any

_IMPORT_MSG = (
    "gds_analysis.linear requires scipy and numpy. "
    "Install with: uv add gds-analysis[continuous]"
)


def _require_deps() -> None:
    """Raise ImportError if scipy/numpy are absent."""
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        raise ImportError(_IMPORT_MSG) from exc


# ---------------------------------------------------------------------------
# Stability analysis
# ---------------------------------------------------------------------------


def eigenvalues(A: list[list[float]]) -> list[complex]:
    """Eigenvalues of state matrix A.

    Parameters
    ----------
    A : list[list[float]]
        Square state matrix.

    Returns
    -------
    list[complex]
        Eigenvalues (may have zero imaginary part for real eigenvalues).
    """
    _require_deps()
    import numpy as np

    if not A:
        return []
    return [complex(e) for e in np.linalg.eigvals(np.array(A, dtype=float))]


def is_stable(A: list[list[float]], *, continuous: bool = True) -> bool:
    """Check asymptotic stability of the state matrix.

    Parameters
    ----------
    A : list[list[float]]
        Square state matrix.
    continuous : bool
        If True (default), checks continuous-time stability: all Re(λ) < 0.
        If False, checks discrete-time stability: all |λ| < 1.

    Returns
    -------
    bool
        True if the system is asymptotically stable.
    """
    eigs = eigenvalues(A)
    if not eigs:
        return True  # vacuously stable

    if continuous:
        return all(e.real < 0 for e in eigs)
    return all(abs(e) < 1.0 for e in eigs)


def is_marginally_stable(A: list[list[float]], *, continuous: bool = True) -> bool:
    """Check marginal stability.

    A system is marginally stable if no eigenvalue is in the unstable
    region and at least one is on the stability boundary.

    Parameters
    ----------
    A : list[list[float]]
        Square state matrix.
    continuous : bool
        If True, boundary is Re(λ) = 0. If False, boundary is |λ| = 1.
    """
    eigs = eigenvalues(A)
    if not eigs:
        return False

    tol = 1e-10
    if continuous:
        if any(e.real > tol for e in eigs):
            return False
        return any(abs(e.real) <= tol for e in eigs)
    else:
        if any(abs(e) > 1.0 + tol for e in eigs):
            return False
        return any(abs(abs(e) - 1.0) <= tol for e in eigs)


# ---------------------------------------------------------------------------
# Frequency response
# ---------------------------------------------------------------------------


def frequency_response(
    A: list[list[float]],
    B: list[list[float]],
    C: list[list[float]],
    D: list[list[float]],
    omega: list[float] | None = None,
    *,
    n_points: int = 500,
    omega_range: tuple[float, float] = (1e-2, 1e2),
) -> tuple[list[float], list[float], list[float]]:
    """Compute frequency response H(jω) numerically.

    Parameters
    ----------
    A, B, C, D : list[list[float]]
        State-space matrices (SISO or first input/output for MIMO).
    omega : list[float] | None
        Frequency points (rad/s). If None, auto-generates from omega_range.
    n_points : int
        Number of frequency points if omega is None.
    omega_range : tuple[float, float]
        Log-spaced frequency range if omega is None.

    Returns
    -------
    (omega, magnitude_db, phase_deg)
        All as plain ``list[float]``.
    """
    _require_deps()
    import numpy as np
    from scipy import signal

    sys = signal.StateSpace(
        np.array(A, dtype=float),
        np.array(B, dtype=float),
        np.array(C, dtype=float),
        np.array(D, dtype=float),
    )

    if omega is None:
        w = np.logspace(np.log10(omega_range[0]), np.log10(omega_range[1]), n_points)
    else:
        w = np.array(omega, dtype=float)

    w_out, H = signal.freqresp(sys, w)

    # For MIMO, take [0,0] element
    if H.ndim > 1:
        H = H[0, 0, :]

    mag_db = (20 * np.log10(np.abs(H))).tolist()
    phase_deg = (np.degrees(np.unwrap(np.angle(H)))).tolist()

    return w_out.tolist(), mag_db, phase_deg


def gain_margin(num: list[float], den: list[float]) -> tuple[float, float]:
    """Compute gain margin.

    Parameters
    ----------
    num : list[float]
        Transfer function numerator coefficients (descending powers).
    den : list[float]
        Transfer function denominator coefficients (descending powers).

    Returns
    -------
    (gm_db, gm_freq)
        Gain margin in dB and the frequency (rad/s) where phase = -180°.
        Returns (float('inf'), float('nan')) if phase never crosses -180°.
    """
    _require_deps()
    import numpy as np
    from scipy import signal

    sys = signal.TransferFunction(
        np.array(num, dtype=float),
        np.array(den, dtype=float),
    )
    w = np.logspace(-4, 4, 10000)
    w_out, H = signal.freqresp(sys, w)

    phase = np.unwrap(np.angle(H))

    # Find -180° crossing
    target = -np.pi
    crossings = []
    for i in range(1, len(phase)):
        if (phase[i - 1] - target) * (phase[i] - target) < 0:
            # Interpolate
            frac = (target - phase[i - 1]) / (phase[i] - phase[i - 1])
            w_cross = w_out[i - 1] + frac * (w_out[i] - w_out[i - 1])
            mag_at_cross = np.abs(H[i - 1]) + frac * (np.abs(H[i]) - np.abs(H[i - 1]))
            crossings.append((w_cross, mag_at_cross))

    if not crossings:
        return float("inf"), float("nan")

    # Take the first crossing
    w_cross, mag_at_cross = crossings[0]
    gm_db = float(-20 * np.log10(mag_at_cross)) if mag_at_cross > 0 else float("inf")

    return gm_db, float(w_cross)


def phase_margin(num: list[float], den: list[float]) -> tuple[float, float]:
    """Compute phase margin.

    Parameters
    ----------
    num : list[float]
        Transfer function numerator coefficients (descending powers).
    den : list[float]
        Transfer function denominator coefficients (descending powers).

    Returns
    -------
    (pm_deg, pm_freq)
        Phase margin in degrees and the gain crossover frequency (rad/s).
        Returns (float('inf'), float('nan')) if gain never crosses 0 dB.
    """
    _require_deps()
    import numpy as np
    from scipy import signal

    sys = signal.TransferFunction(
        np.array(num, dtype=float),
        np.array(den, dtype=float),
    )
    w = np.logspace(-4, 4, 10000)
    w_out, H = signal.freqresp(sys, w)

    mag = np.abs(H)
    phase = np.unwrap(np.angle(H))

    # Find 0 dB crossing (|H| = 1)
    crossings = []
    for i in range(1, len(mag)):
        if (mag[i - 1] - 1.0) * (mag[i] - 1.0) < 0:
            frac = (1.0 - mag[i - 1]) / (mag[i] - mag[i - 1])
            w_cross = w_out[i - 1] + frac * (w_out[i] - w_out[i - 1])
            phase_at_cross = phase[i - 1] + frac * (phase[i] - phase[i - 1])
            crossings.append((w_cross, phase_at_cross))

    if not crossings:
        return float("inf"), float("nan")

    # Take the first crossing
    w_cross, phase_at_cross = crossings[0]
    pm_deg = float(np.degrees(phase_at_cross) + 180.0)

    return pm_deg, float(w_cross)


# ---------------------------------------------------------------------------
# Discretization
# ---------------------------------------------------------------------------


def discretize(
    A: list[list[float]],
    B: list[list[float]],
    C: list[list[float]],
    D: list[list[float]],
    dt: float,
    *,
    method: str = "tustin",
) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[list[float]]]:
    """Convert continuous state-space to discrete: (A, B, C, D) → (Ad, Bd, Cd, Dd).

    Parameters
    ----------
    A, B, C, D : list[list[float]]
        Continuous-time state-space matrices.
    dt : float
        Sampling period in seconds.
    method : str
        Discretization method: ``"tustin"`` (bilinear), ``"zoh"``
        (zero-order hold), ``"euler"`` (forward Euler).

    Returns
    -------
    (Ad, Bd, Cd, Dd) as ``list[list[float]]``.
    """
    _require_deps()
    import numpy as np
    from scipy import signal

    method_map = {
        "tustin": "bilinear",
        "bilinear": "bilinear",
        "zoh": "zoh",
        "euler": "euler",
        "forward_euler": "euler",
        "backward_euler": "backward_diff",
        "backward_diff": "backward_diff",
    }

    scipy_method = method_map.get(method.lower())
    if scipy_method is None:
        raise ValueError(
            f"Unknown discretization method '{method}'. "
            f"Valid methods: {sorted(method_map.keys())}"
        )

    sys_c = signal.StateSpace(
        np.array(A, dtype=float),
        np.array(B, dtype=float),
        np.array(C, dtype=float),
        np.array(D, dtype=float),
    )

    sys_d = sys_c.to_discrete(dt, method=scipy_method)

    return (
        sys_d.A.tolist(),
        sys_d.B.tolist(),
        sys_d.C.tolist(),
        sys_d.D.tolist(),
    )


# ---------------------------------------------------------------------------
# Controller synthesis
# ---------------------------------------------------------------------------


def lqr(
    A: list[list[float]],
    B: list[list[float]],
    Q: list[list[float]],
    R: list[list[float]],
    N: list[list[float]] | None = None,
) -> tuple[list[list[float]], list[list[float]], list[complex]]:
    """Continuous-time Linear Quadratic Regulator.

    Minimizes J = ∫(x'Qx + u'Ru + 2x'Nu) dt by solving the continuous
    algebraic Riccati equation.

    Parameters
    ----------
    A : list[list[float]]
        State matrix (n x n).
    B : list[list[float]]
        Input matrix (n x m).
    Q : list[list[float]]
        State cost matrix (n x n, positive semi-definite).
    R : list[list[float]]
        Input cost matrix (m x m, positive definite).
    N : list[list[float]] | None
        Cross-term matrix (n x m). Default is zero.

    Returns
    -------
    (K, P, E)
        K — optimal gain matrix (u = -Kx), shape (m x n).
        P — solution to the Riccati equation, shape (n x n).
        E — closed-loop eigenvalues.

    Raises
    ------
    ValueError
        If the system is not stabilizable.
    """
    _require_deps()
    import numpy as np
    from scipy import linalg

    a = np.array(A, dtype=float)
    b = np.array(B, dtype=float)
    q = np.array(Q, dtype=float)
    r = np.array(R, dtype=float)

    if N is not None:
        n_mat = np.array(N, dtype=float)
        # Transform: A_bar = A - B R^{-1} N', Q_bar = Q - N R^{-1} N'
        r_inv = np.linalg.inv(r)
        a_bar = a - b @ r_inv @ n_mat.T
        q_bar = q - n_mat @ r_inv @ n_mat.T
    else:
        a_bar = a
        q_bar = q
        n_mat = np.zeros((a.shape[0], b.shape[1]))

    try:
        P = linalg.solve_continuous_are(a_bar, b, q_bar, r)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Failed to solve Riccati equation. "
            "Check that (A, B) is stabilizable and Q >= 0, R > 0."
        ) from exc

    r_inv = np.linalg.inv(r)
    K = r_inv @ (b.T @ P + n_mat.T)

    # Closed-loop eigenvalues
    A_cl = a - b @ K
    E = np.linalg.eigvals(A_cl)

    return K.tolist(), P.tolist(), [complex(e) for e in E]


def dlqr(
    Ad: list[list[float]],
    Bd: list[list[float]],
    Q: list[list[float]],
    R: list[list[float]],
) -> tuple[list[list[float]], list[list[float]], list[complex]]:
    """Discrete-time Linear Quadratic Regulator.

    Minimizes J = Σ(x'Qx + u'Ru) by solving the discrete algebraic
    Riccati equation.

    Parameters
    ----------
    Ad : list[list[float]]
        Discrete state matrix (n x n).
    Bd : list[list[float]]
        Discrete input matrix (n x m).
    Q : list[list[float]]
        State cost (n x n, positive semi-definite).
    R : list[list[float]]
        Input cost (m x m, positive definite).

    Returns
    -------
    (K, P, E)
        K — optimal gain, P — Riccati solution, E — closed-loop eigenvalues.
    """
    _require_deps()
    import numpy as np
    from scipy import linalg

    a = np.array(Ad, dtype=float)
    b = np.array(Bd, dtype=float)
    q = np.array(Q, dtype=float)
    r = np.array(R, dtype=float)

    try:
        P = linalg.solve_discrete_are(a, b, q, r)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Failed to solve discrete Riccati equation. "
            "Check that (Ad, Bd) is stabilizable."
        ) from exc

    K = np.linalg.inv(r + b.T @ P @ b) @ (b.T @ P @ a)

    A_cl = a - b @ K
    E = np.linalg.eigvals(A_cl)

    return K.tolist(), P.tolist(), [complex(e) for e in E]


def kalman(
    A: list[list[float]],
    C: list[list[float]],
    Q_process: list[list[float]],
    R_measurement: list[list[float]],
) -> tuple[list[list[float]], list[list[float]]]:
    """Steady-state Kalman filter (observer) gain.

    Dual of LQR: solves the continuous algebraic Riccati equation for
    the observer problem.

    Parameters
    ----------
    A : list[list[float]]
        State matrix (n x n).
    C : list[list[float]]
        Output matrix (p x n).
    Q_process : list[list[float]]
        Process noise covariance (n x n).
    R_measurement : list[list[float]]
        Measurement noise covariance (p x p).

    Returns
    -------
    (L, P)
        L — observer gain matrix (n x p), such that x̂' = Ax̂ + Bu + L(y - Cx̂).
        P — error covariance matrix (n x n).

    Raises
    ------
    ValueError
        If (A, C) is not detectable.
    """
    _require_deps()
    import numpy as np
    from scipy import linalg

    a = np.array(A, dtype=float)
    c = np.array(C, dtype=float)
    q = np.array(Q_process, dtype=float)
    r = np.array(R_measurement, dtype=float)

    # Dual of LQR: solve ARE for A', C', Q, R
    try:
        P = linalg.solve_continuous_are(a.T, c.T, q, r)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Failed to solve observer Riccati equation. "
            "Check that (A, C) is detectable."
        ) from exc

    L = P @ c.T @ np.linalg.inv(r)

    return L.tolist(), P.tolist()


def gain_schedule(
    linearize_fn: Any,
    operating_points: list[dict[str, float]],
    Q: list[list[float]],
    R: list[list[float]],
) -> list[tuple[dict[str, float], list[list[float]], list[complex]]]:
    """Compute LQR gains at multiple operating points.

    Parameters
    ----------
    linearize_fn : callable
        Takes an operating point dict, returns
        ``(A, B, C, D)`` as a tuple of ``list[list[float]]``.
    operating_points : list[dict]
        Operating point parameter dicts.
    Q : list[list[float]]
        State cost matrix (same for all points).
    R : list[list[float]]
        Input cost matrix (same for all points).

    Returns
    -------
    list of (operating_point, K, closed_loop_eigenvalues) tuples.
    """
    results = []
    for point in operating_points:
        A_op, B_op, _C_op, _D_op = linearize_fn(point)
        K, _P, E = lqr(A_op, B_op, Q, R)
        results.append((point, K, E))
    return results

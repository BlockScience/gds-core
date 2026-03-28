"""Homicidal Chauffeur Differential Game — gds-symbolic + gds-continuous.

Isaacs' foundational pursuit-evasion problem (1951): Can a fast but clumsy
car catch a slow but agile pedestrian?

This example demonstrates the full symbolic-to-numerical pipeline:
1. Declare the game dynamics symbolically using gds-symbolic
2. Derive optimal controls from the Hamiltonian using SymPy
3. Compile the closed-loop 4D ODE via sympy.lambdify
4. Integrate trajectories using gds-continuous
5. Verify conservation laws (Hamiltonian, costate norm)

The 4D characteristic ODE (optimal feedback form):
    x1_dot = -phi_star * x2 + w * sin(psi_star)
    x2_dot =  phi_star * x1 + w * cos(psi_star) - 1
    p1_dot = -phi_star * p2
    p2_dot =  phi_star * p1

where:
    phi_star = -sign(sigma),  sigma = p2*x1 - p1*x2  (bang-bang pursuer)
    psi_star = atan2(p1, p2)                           (gradient-aligned evader)

Parameters:
    w = v_E / v_P          -- evader-to-pursuer speed ratio (0 < w < 1)
    ell_tilde = ell / R_min -- normalized capture radius

GDS Decomposition:
    X = (x1, x2, p1, p2) -- relative position + costates (4D)
    U = (w, ell_tilde)    -- game parameters
    h = f                 -- pure dynamics, no policy/mechanism split
                            (the optimal controls are derived analytically
                            and substituted into the RHS)

References:
    R. Isaacs, *Differential Games*, Wiley (1965), pp. 297-350
    A.W. Merz, PhD Thesis, Stanford (1971)
    github.com/mzargham/hc-marimo
"""

from __future__ import annotations

import math
from typing import Any

from gds_continuous import ODEModel, ODESimulation

# ---------------------------------------------------------------------------
# Symbolic derivation (requires sympy)
# ---------------------------------------------------------------------------


def derive_optimal_rhs() -> tuple[Any, list[str]]:
    """Derive the 4D characteristic ODE symbolically.

    Uses SymPy to:
    1. Define the reduced kinematics (Isaacs' body-fixed frame)
    2. Construct the Hamiltonian H = p1*f1 + p2*f2 + 1
    3. Solve for optimal controls (bang-bang phi, gradient-aligned psi)
    4. Derive costate equations from dH/dx
    5. Lambdify the full 4D system

    Returns
    -------
    rhs_fn : callable
        Lambdified (t, y, params) -> dy/dt
    state_order : list[str]
        ["x1", "x2", "p1", "p2"]
    """
    import sympy as sp

    x1, x2 = sp.symbols("x_1 x_2", real=True)
    p1, p2 = sp.symbols("p_1 p_2", real=True)
    phi = sp.Symbol("phi", real=True)
    psi = sp.Symbol("psi", real=True)
    w = sp.Symbol("w", positive=True)

    # Reduced dynamics (Isaacs' canonical form)
    f1 = -phi * x2 + w * sp.sin(psi)
    f2 = phi * x1 + w * sp.cos(psi) - 1

    # Hamiltonian (minimizing time => +1)
    H = p1 * f1 + p2 * f2 + 1

    # Optimal pursuer: phi* = -sign(sigma), sigma = dH/dphi coefficient
    sigma = sp.expand(H).coeff(phi)  # = p2*x1 - p1*x2
    phi_star = -sp.sign(sigma)

    # Optimal evader: psi* = atan2(p1, p2) maximizes w*(p1*sin + p2*cos)
    psi_star = sp.atan2(p1, p2)

    # Substitute optimal controls
    rhs_x1 = f1.subs([(phi, phi_star), (psi, psi_star)])
    rhs_x2 = f2.subs([(phi, phi_star), (psi, psi_star)])

    # Costate equations: dp/dt = -dH/dx
    rhs_p1 = -phi_star * p2
    rhs_p2 = phi_star * p1

    # Lambdify
    _fn = sp.lambdify(
        [x1, x2, p1, p2, w],
        [rhs_x1, rhs_x2, rhs_p1, rhs_p2],
        modules=["numpy"],
    )

    def rhs_fn(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
        result = _fn(y[0], y[1], y[2], y[3], params["w"])
        return [float(v) for v in result]

    return rhs_fn, ["x1", "x2", "p1", "p2"]


# ---------------------------------------------------------------------------
# Hand-coded dynamics (no SymPy dependency)
# ---------------------------------------------------------------------------


def hc_forward(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """Forward 4D characteristic ODE — hand-coded numpy version."""
    x1, x2, p1, p2 = y
    w = params["w"]

    norm_p = math.sqrt(p1**2 + p2**2)
    if norm_p < 1e-15:
        return [0.0, 0.0, 0.0, 0.0]

    sigma = p2 * x1 - p1 * x2
    phi_star = -1.0 if sigma > 0 else (1.0 if sigma < 0 else 0.0)

    x1d = -phi_star * x2 + w * p1 / norm_p
    x2d = phi_star * x1 + w * p2 / norm_p - 1.0
    p1d = -phi_star * p2
    p2d = phi_star * p1
    return [x1d, x2d, p1d, p2d]


def hc_backward(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """Backward integration (negate forward dynamics)."""
    fwd = hc_forward(t, y, params)
    return [-v for v in fwd]


# ---------------------------------------------------------------------------
# Terminal conditions
# ---------------------------------------------------------------------------


def terminal_conditions(alpha: float, w: float, ell_tilde: float) -> dict[str, float]:
    """Compute initial conditions on the capture circle for backward integration.

    Parameters
    ----------
    alpha : float
        Angle on the terminal circle. Usable part requires sin(alpha) > w.
    w : float
        Evader-to-pursuer speed ratio.
    ell_tilde : float
        Normalized capture radius.

    Returns
    -------
    dict mapping state names to values.
    """
    x1_T = ell_tilde * math.cos(alpha)
    x2_T = ell_tilde * math.sin(alpha)
    lam = -1.0 / (ell_tilde * (w - math.sin(alpha)))
    p1_T = lam * x1_T
    p2_T = lam * x2_T
    return {"x1": x1_T, "x2": x2_T, "p1": p1_T, "p2": p2_T}


# ---------------------------------------------------------------------------
# Conservation laws
# ---------------------------------------------------------------------------


def hamiltonian_star(state: dict[str, float], w: float) -> float:
    """Optimal Hamiltonian H* = -|sigma| + w*||p|| - p2 + 1.

    Should be ~0 along optimal trajectories.
    """
    x1, x2 = state["x1"], state["x2"]
    p1, p2 = state["p1"], state["p2"]
    sigma = p2 * x1 - p1 * x2
    norm_p = math.sqrt(p1**2 + p2**2)
    return -abs(sigma) + w * norm_p - p2 + 1.0


def costate_norm_sq(state: dict[str, float]) -> float:
    """||p||^2 = p1^2 + p2^2. Should be conserved along trajectories."""
    return state["p1"] ** 2 + state["p2"] ** 2


# ---------------------------------------------------------------------------
# Simulation builders
# ---------------------------------------------------------------------------


def build_backward_model(
    alpha: float = math.pi / 2,
    w: float = 0.25,
    ell_tilde: float = 0.5,
) -> ODEModel:
    """Build an ODEModel for backward integration from the capture circle."""
    ic = terminal_conditions(alpha, w, ell_tilde)
    return ODEModel(
        state_names=["x1", "x2", "p1", "p2"],
        initial_state=ic,
        rhs=hc_backward,
        params={"w": [w]},
    )


def build_backward_simulation(
    alpha: float = math.pi / 2,
    w: float = 0.25,
    ell_tilde: float = 0.5,
    t_final: float = 10.0,
) -> ODESimulation:
    """Build an ODESimulation for backward reachable set computation."""
    model = build_backward_model(alpha, w, ell_tilde)
    return ODESimulation(
        model=model,
        t_span=(0.0, t_final),
        solver="RK45",
        rtol=1e-10,
        atol=1e-12,
        max_step=0.02,
    )


def compute_isochrone(
    w: float = 0.25,
    ell_tilde: float = 0.5,
    t_final: float = 5.0,
    n_rays: int = 40,
) -> list[tuple[float, float]]:
    """Compute a backward reachable set boundary (isochrone).

    Integrates backward from multiple points on the usable part of the
    terminal circle, each for time t_final. Returns the endpoints as
    (x1, x2) pairs forming the isochrone contour.
    """
    # Usable part: sin(alpha) > w
    alpha_min = math.asin(w) + 0.01
    alpha_max = math.pi - math.asin(w) - 0.01
    alphas = [
        alpha_min + i * (alpha_max - alpha_min) / (n_rays - 1) for i in range(n_rays)
    ]

    points: list[tuple[float, float]] = []
    for alpha in alphas:
        sim = build_backward_simulation(alpha, w, ell_tilde, t_final)
        results = sim.run()
        x1_final = results.state_array("x1")[-1]
        x2_final = results.state_array("x2")[-1]
        points.append((x1_final, x2_final))

    return points

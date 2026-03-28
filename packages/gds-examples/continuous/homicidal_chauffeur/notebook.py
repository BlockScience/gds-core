import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def imports():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import sympy as sp
    from sympy import (
        atan2,
        cos,
        diff,
        expand,
        latex,
        sign,
        simplify,
        sin,
        sqrt,
        symbols,
        trigsimp,
    )

    from gds_continuous import ODEModel, ODESimulation

    return (
        ODEModel,
        ODESimulation,
        atan2,
        cos,
        diff,
        expand,
        latex,
        mo,
        np,
        plt,
        sign,
        simplify,
        sin,
        sp,
        sqrt,
        symbols,
        trigsimp,
    )


@app.cell
def title(mo):
    mo.md(
        r"""
    # The Homicidal Chauffeur: A Differential Game

    ## Symbolic Derivation & Interactive Simulation with gds-continuous

    ---

    *An interactive notebook exploring Rufus Isaacs' foundational
    pursuit-evasion problem (1951) through the
    [GDS](https://github.com/BlockScience/gds-core) ecosystem.*

    Every equation is derived symbolically with SymPy, then integrated
    numerically through `gds-continuous` (wrapping `scipy.integrate.solve_ivp`).

    **The problem:** Can a fast but clumsy car catch a slow but agile
    pedestrian? A pursuer (high speed, minimum turning radius) chases an
    evader (low speed, unlimited maneuverability) on an unbounded plane.

    **References:**
    - R. Isaacs, *Differential Games*, Wiley (1965), pp. 297--350
    - A.W. Merz, PhD Thesis, Stanford (1971)
    - [mzargham/hc-marimo](https://github.com/mzargham/hc-marimo)
      (reference implementation)
    """
    )
    return


@app.cell
def define_symbols(symbols):
    x1, x2 = symbols("x_1 x_2", real=True)
    p1, p2 = symbols("p_1 p_2", real=True)
    phi = symbols("phi", real=True)
    psi = symbols("psi", real=True)
    w = symbols("w", positive=True)
    return p1, p2, phi, psi, w, x1, x2


@app.cell
def reduced_dynamics(cos, latex, mo, phi, psi, sin, w, x1, x2):
    f1 = -phi * x2 + w * sin(psi)
    f2 = phi * x1 + w * cos(psi) - 1

    mo.md(
        rf"""
    ## Reduced Kinematics (Isaacs' Body-Fixed Frame)

    After reducing from 5-DOF absolute coordinates to a 2-DOF system
    in the pursuer's rotating frame (normalizing $v_P = 1$, $R_{{\min}} = 1$):

    $$
    \dot{{x}}_1 = {latex(f1)}, \qquad \dot{{x}}_2 = {latex(f2)}
    $$

    where $\phi \in [-1, +1]$ is the pursuer's turn rate (control),
    $\psi$ is the evader's heading (control), and $w = v_E / v_P < 1$.
    """
    )
    return f1, f2


@app.cell
def hamiltonian(expand, f1, f2, latex, mo, p1, p2, phi, psi, w):
    H = p1 * f1 + p2 * f2 + 1
    _H_expanded = expand(H)

    sigma = _H_expanded.coeff(phi)

    mo.md(
        rf"""
    ## Hamiltonian & Optimal Controls

    The time-optimal Hamiltonian:

    $$H = p_1 f_1 + p_2 f_2 + 1$$

    Expanding: $H$ is **linear in $\phi$** with switching function
    $\sigma = {latex(sigma)}$.

    **Pursuer** (minimizes $H$): $\phi^* = -\text{{sign}}(\sigma)$ (bang-bang)

    **Evader** (maximizes $H$): $\psi^* = \text{{atan2}}(p_1, p_2)$
    (gradient-aligned)
    """
    )
    return H, sigma


@app.cell
def costate_equations(H, diff, latex, mo, phi, p1, p2, simplify, x1, x2):
    p1_dot = -diff(H, x1)
    p2_dot = -diff(H, x2)

    _d_norm_sq = simplify(2 * (p1 * p1_dot + p2 * p2_dot))

    mo.md(
        rf"""
    ## Costate (Adjoint) Equations

    $$\dot{{p}}_1 = -{{\partial H}}/{{\partial x_1}} = {latex(p1_dot)}$$
    $$\dot{{p}}_2 = -{{\partial H}}/{{\partial x_2}} = {latex(p2_dot)}$$

    **Conservation:** $\frac{{d}}{{dt}}(p_1^2 + p_2^2) = {latex(_d_norm_sq)}$
    — the costate norm is constant along optimal trajectories.
    """
    )
    return p1_dot, p2_dot


@app.cell
def lambdify_rhs(atan2, f1, f2, p1, p2, phi, psi, sign, sp, w, x1, x2):
    _sigma = p2 * x1 - p1 * x2
    _phi_star = -sign(_sigma)
    _psi_star = atan2(p1, p2)

    _rhs_x1 = f1.subs([(phi, _phi_star), (psi, _psi_star)])
    _rhs_x2 = f2.subs([(phi, _phi_star), (psi, _psi_star)])
    _rhs_p1 = -_phi_star * p2
    _rhs_p2 = _phi_star * p1

    _fn = sp.lambdify(
        [x1, x2, p1, p2, w],
        [_rhs_x1, _rhs_x2, _rhs_p1, _rhs_p2],
        modules=["numpy"],
    )

    def rhs_forward(t, y, params):
        _result = _fn(y[0], y[1], y[2], y[3], params["w"])
        return [float(_v) for _v in _result]

    def rhs_backward(t, y, params):
        _fwd = rhs_forward(t, y, params)
        return [-_v for _v in _fwd]

    return rhs_backward, rhs_forward


@app.cell
def parameter_sliders(mo):
    mo.md("## Interactive Parameters")

    v_E_slider = mo.ui.slider(
        start=0.05,
        stop=0.50,
        step=0.01,
        value=0.25,
        label=r"Evader speed $v_E$ (pursuer $v_P = 1$)",
    )
    omega_max_slider = mo.ui.slider(
        start=0.5,
        stop=3.0,
        step=0.1,
        value=1.0,
        label=r"Max angular velocity $\omega_{\max}$",
    )
    ell_slider = mo.ui.slider(
        start=0.1, stop=1.5, step=0.05, value=0.5, label=r"Capture radius $\ell$"
    )

    mo.vstack([v_E_slider, omega_max_slider, ell_slider])
    return ell_slider, omega_max_slider, v_E_slider


@app.cell
def derived_parameters(ell_slider, mo, omega_max_slider, v_E_slider):
    v_E_val = v_E_slider.value
    _v_P_val = 1.0
    _omega_val = omega_max_slider.value
    _ell_val = ell_slider.value

    _R_min_val = _v_P_val / _omega_val
    w_val = v_E_val / _v_P_val
    ell_tilde_val = _ell_val / _R_min_val

    mo.md(
        rf"""
    ### Dimensionless Parameters

    | Symbol | Meaning | Value |
    |--------|---------|-------|
    | $w = v_E / v_P$ | speed ratio | ${w_val:.3f}$ |
    | $\tilde{{\ell}} = \ell / R_{{\min}}$ | capture radius | ${ell_tilde_val:.3f}$ |
    """
    )
    return ell_tilde_val, w_val


@app.cell
def terminal_conditions_fn(np):
    def compute_terminal_conditions(alpha_arr, _w_val, _ell_tilde_val):
        """Compute (x1, x2, p1, p2) at the terminal surface."""
        _x1_T = _ell_tilde_val * np.cos(alpha_arr)
        _x2_T = _ell_tilde_val * np.sin(alpha_arr)
        _lam = -1.0 / (_ell_tilde_val * (_w_val - np.sin(alpha_arr)))
        _p1_T = _lam * _x1_T
        _p2_T = _lam * _x2_T
        return np.column_stack([_x1_T, _x2_T, _p1_T, _p2_T])

    return (compute_terminal_conditions,)


@app.cell
def trajectory_sliders(mo):
    n_traj_slider = mo.ui.slider(
        start=5, stop=50, step=5, value=20, label="Number of trajectories"
    )
    T_horizon_slider = mo.ui.slider(
        start=1.0, stop=20.0, step=0.5, value=8.0, label=r"Backward time horizon $T$"
    )
    mo.vstack([mo.md("### Trajectory Controls"), n_traj_slider, T_horizon_slider])
    return T_horizon_slider, n_traj_slider


@app.cell
def backward_trajectories(
    ODEModel,
    ODESimulation,
    T_horizon_slider,
    compute_terminal_conditions,
    ell_tilde_val,
    n_traj_slider,
    np,
    rhs_backward,
    w_val,
):
    _n_traj = n_traj_slider.value
    _T_horizon = T_horizon_slider.value

    _alpha_min = np.arcsin(min(w_val, 0.999))
    _alpha_max = np.pi - _alpha_min
    _eps = 1e-3
    _alphas = np.linspace(_alpha_min + _eps, _alpha_max - _eps, _n_traj)

    _terminal = compute_terminal_conditions(_alphas, w_val, ell_tilde_val)

    trajectories = []
    for _i in range(_n_traj):
        _ic = _terminal[_i]
        _model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state={
                "x1": float(_ic[0]),
                "x2": float(_ic[1]),
                "p1": float(_ic[2]),
                "p2": float(_ic[3]),
            },
            rhs=rhs_backward,
            params={"w": [w_val]},
        )
        _sim = ODESimulation(
            model=_model,
            t_span=(0.0, _T_horizon),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
            max_step=0.05,
        )
        _results = _sim.run()
        trajectories.append(_results)
    return (trajectories,)


@app.cell
def trajectory_plot(ell_tilde_val, mo, np, plt, trajectories, w_val):
    _fig, _ax = plt.subplots(1, 1, figsize=(8, 8))

    # Terminal circle
    _theta = np.linspace(0, 2 * np.pi, 200)
    _ax.plot(
        ell_tilde_val * np.cos(_theta),
        ell_tilde_val * np.sin(_theta),
        "k--",
        linewidth=1,
        alpha=0.5,
        label="Terminal circle",
    )

    # Usable part
    _alpha_min = np.arcsin(min(w_val, 0.999))
    _alpha_max = np.pi - _alpha_min
    _usable = np.linspace(_alpha_min, _alpha_max, 100)
    _ax.plot(
        ell_tilde_val * np.cos(_usable),
        ell_tilde_val * np.sin(_usable),
        "r-",
        linewidth=3,
        alpha=0.8,
        label="Usable part",
    )

    # Plot trajectories
    _cmap = plt.cm.viridis
    _mid = (len(trajectories) - 1) / 2.0
    for _i, _res in enumerate(trajectories):
        _color = _cmap(abs(_i - _mid) / max(_mid, 1))
        _x1s = _res.state_array("x1")
        _x2s = _res.state_array("x2")
        _ax.plot(_x1s, _x2s, "-", color=_color, linewidth=0.8, alpha=0.7)
        _ax.plot(_x1s[-1], _x2s[-1], "o", color=_color, markersize=3)

    _ax.plot(0, 0, "k+", markersize=12, markeredgewidth=2)
    _ax.set_xlabel(r"$x_1$ (perpendicular)")
    _ax.set_ylabel(r"$x_2$ (along heading)")
    _ax.set_aspect("equal")
    _ax.set_title(
        rf"Optimal Trajectories ($w = {w_val:.3f}$, "
        rf"$\tilde{{\ell}} = {ell_tilde_val:.3f}$)"
    )
    _ax.legend(loc="lower right", fontsize=9)
    _ax.grid(True, alpha=0.3)
    plt.tight_layout()

    mo.vstack(
        [
            _fig,
            mo.md(
                r"""
        **Backward characteristics** from the usable part of the terminal
        circle. Each curve starts on the capture boundary at $\tau = 0$
        and extends outward as backward time $\tau$ increases. In forward
        time, these are optimal pursuit paths.

        Sharp kinks are **bang-bang switching points** where the pursuer's
        control jumps between $\phi = +1$ and $\phi = -1$.

        *Integrated via `gds-continuous.ODESimulation`.*
        """
            ),
        ]
    )
    return


@app.cell
def isochrone_controls(mo):
    iso_T_slider = mo.ui.slider(
        start=1.0, stop=15.0, step=0.5, value=5.0, label=r"Isochrone time $T$"
    )
    iso_n_slider = mo.ui.slider(
        start=20, stop=100, step=10, value=60, label="Isochrone resolution"
    )
    mo.vstack(
        [
            mo.md("### Isochrone (Backward Reachable Set)"),
            iso_T_slider,
            iso_n_slider,
        ]
    )
    return iso_T_slider, iso_n_slider


@app.cell
def isochrone_plot(
    ODEModel,
    ODESimulation,
    compute_terminal_conditions,
    ell_tilde_val,
    iso_T_slider,
    iso_n_slider,
    mo,
    np,
    plt,
    rhs_backward,
    w_val,
):
    _T_iso = iso_T_slider.value
    _n_rays = iso_n_slider.value

    _alpha_min = np.arcsin(min(w_val, 0.999))
    _alpha_max = np.pi - _alpha_min
    _eps = 1e-3
    _alphas = np.linspace(_alpha_min + _eps, _alpha_max - _eps, _n_rays)
    _terminal = compute_terminal_conditions(_alphas, w_val, ell_tilde_val)

    _endpoints_x1 = []
    _endpoints_x2 = []
    for _i in range(_n_rays):
        _ic = _terminal[_i]
        _model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state={
                "x1": float(_ic[0]),
                "x2": float(_ic[1]),
                "p1": float(_ic[2]),
                "p2": float(_ic[3]),
            },
            rhs=rhs_backward,
            params={"w": [w_val]},
        )
        _sim = ODESimulation(
            model=_model,
            t_span=(0.0, _T_iso),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
            max_step=0.05,
        )
        _res = _sim.run()
        _endpoints_x1.append(_res.state_array("x1")[-1])
        _endpoints_x2.append(_res.state_array("x2")[-1])

    _fig, _ax = plt.subplots(1, 1, figsize=(8, 8))

    # Terminal circle
    _theta = np.linspace(0, 2 * np.pi, 200)
    _ax.plot(
        ell_tilde_val * np.cos(_theta),
        ell_tilde_val * np.sin(_theta),
        "k--",
        linewidth=1,
        alpha=0.5,
    )

    # Isochrone boundary
    _ax.plot(
        _endpoints_x1,
        _endpoints_x2,
        "b-",
        linewidth=2,
        label=rf"$T = {_T_iso:.1f}$",
    )
    _ax.fill(_endpoints_x1, _endpoints_x2, color="blue", alpha=0.05)

    _ax.plot(0, 0, "k+", markersize=12, markeredgewidth=2)
    _ax.set_xlabel(r"$x_1$")
    _ax.set_ylabel(r"$x_2$")
    _ax.set_aspect("equal")
    _ax.set_title(
        rf"Backward Reachable Set ($w = {w_val:.3f}$, "
        rf"$\tilde{{\ell}} = {ell_tilde_val:.3f}$)"
    )
    _ax.legend(fontsize=10)
    _ax.grid(True, alpha=0.3)
    plt.tight_layout()

    mo.vstack(
        [
            _fig,
            mo.md(
                rf"""
        The **isochrone** at $T = {_T_iso:.1f}$: the boundary of the set of
        initial positions from which the pursuer can guarantee capture within
        time $T$ under optimal play. Computed by integrating {_n_rays} backward
        characteristics from the usable part of the terminal circle, each for
        time $T$, using `gds-continuous.ODESimulation`.
        """
            ),
        ]
    )
    return


@app.cell
def conservation_check(mo, np, trajectories, w_val):
    _max_H = 0.0
    _max_p = 0.0
    for _res in trajectories:
        _x1s = _res.state_array("x1")
        _x2s = _res.state_array("x2")
        _p1s = _res.state_array("p1")
        _p2s = _res.state_array("p2")
        for _j in range(len(_res)):
            _sigma = _p2s[_j] * _x1s[_j] - _p1s[_j] * _x2s[_j]
            _norm_p = np.sqrt(_p1s[_j] ** 2 + _p2s[_j] ** 2)
            _H = -abs(_sigma) + w_val * _norm_p - _p2s[_j] + 1.0
            _max_H = max(_max_H, abs(_H))

        _p_norms = [_p1s[_j] ** 2 + _p2s[_j] ** 2 for _j in range(len(_res))]
        _p0 = _p_norms[0]
        _max_p = max(_max_p, max(abs(_pn - _p0) for _pn in _p_norms))

    mo.md(
        rf"""
    ## Verification

    | Conservation law | Max drift | Tolerance |
    |-----------------|-----------|-----------|
    | $H^* \approx 0$ | ${_max_H:.2e}$ | $< 10^{{-6}}$ |
    | $\|\|p\|\|^2$ constant | ${_max_p:.2e}$ | $< 10^{{-8}}$ |

    {
            "All conservation laws satisfied."
            if _max_H < 1e-6 and _max_p < 1e-8
            else "**WARNING:** Conservation law violation detected."
        }
    """
    )
    return


@app.cell
def references(mo):
    mo.md(
        r"""
    ## References

    - R. Isaacs, *Games of Pursuit*, RAND Corporation P-257 (1951)
    - R. Isaacs, *Differential Games*, John Wiley & Sons (1965), pp. 297--350
    - A.W. Merz, *The Homicidal Chauffeur -- a Differential Game*,
      PhD Thesis, Stanford (1971)
    - V.S. Patsko & V.L. Turova, "Homicidal Chauffeur Game: History and
      Modern Studies," *Advances in Dynamic Games*, ISDG Vol. 11 (2011)
    - [mzargham/hc-marimo](https://github.com/mzargham/hc-marimo) --
      reference SymPy implementation
    - [gds-core](https://github.com/BlockScience/gds-core) --
      GDS ecosystem (`gds-continuous` for ODE integration)
    """
    )
    return


if __name__ == "__main__":
    app.run()

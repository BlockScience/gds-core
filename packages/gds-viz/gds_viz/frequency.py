"""Frequency response visualization: Bode, Nyquist, Nichols, root locus.

All functions accept plain ``list[float]`` or numpy arrays as input data.
No imports from gds-domains or gds-analysis — the caller computes the data,
the viz just plots it.

Requires ``gds-viz[control]`` (matplotlib + numpy).
"""

from __future__ import annotations

from typing import Any


def _require_control_deps() -> None:
    """Raise ImportError if matplotlib/numpy are absent."""
    try:
        import matplotlib  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Frequency response visualization requires matplotlib and numpy. "
            "Install with: uv add gds-viz[control]"
        ) from exc


def bode_plot(
    omega: list[float],
    mag_db: list[float],
    phase_deg: list[float],
    *,
    title: str = "Bode Plot",
    gain_margin: tuple[float, float] | None = None,
    phase_margin: tuple[float, float] | None = None,
    ax: tuple[Any, Any] | None = None,
    figsize: tuple[float, float] = (10, 8),
) -> Any:
    """Bode magnitude and phase plot.

    Two vertically stacked subplots:
    - Top: magnitude (dB) vs. frequency (rad/s, log scale)
    - Bottom: phase (degrees) vs. frequency (rad/s, log scale)

    Parameters
    ----------
    omega : list[float]
        Frequency values in rad/s.
    mag_db : list[float]
        Magnitude in dB.
    phase_deg : list[float]
        Phase in degrees.
    title : str
        Plot title.
    gain_margin : tuple[float, float] | None
        If provided, ``(gm_db, gm_freq)`` — annotates gain margin.
    phase_margin : tuple[float, float] | None
        If provided, ``(pm_deg, pm_freq)`` — annotates phase margin.
    ax : tuple[Axes, Axes] | None
        Existing (mag_ax, phase_ax) to plot into. Creates new if None.
    figsize : tuple[float, float]
        Figure size.

    Returns
    -------
    matplotlib Figure
    """
    _require_control_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    w = np.array(omega)
    mag = np.array(mag_db)
    phase = np.array(phase_deg)

    if ax is None:
        fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=figsize, sharex=True)
    else:
        ax_mag, ax_phase = ax
        fig = ax_mag.get_figure()

    # Magnitude plot
    ax_mag.semilogx(w, mag, "b-", linewidth=1.5)
    ax_mag.axhline(y=0, color="k", linewidth=0.5, linestyle="--", alpha=0.5)
    ax_mag.set_ylabel("Magnitude (dB)")
    ax_mag.set_title(title)
    ax_mag.grid(True, which="both", alpha=0.3)

    # Phase plot
    ax_phase.semilogx(w, phase, "r-", linewidth=1.5)
    ax_phase.axhline(y=-180, color="k", linewidth=0.5, linestyle="--", alpha=0.5)
    ax_phase.set_xlabel("Frequency (rad/s)")
    ax_phase.set_ylabel("Phase (deg)")
    ax_phase.grid(True, which="both", alpha=0.3)

    # Annotate margins
    if gain_margin is not None:
        gm_db, gm_freq = gain_margin
        if np.isfinite(gm_db) and np.isfinite(gm_freq):
            ax_mag.axvline(x=gm_freq, color="g", linestyle=":", alpha=0.7)
            ax_mag.annotate(
                f"GM = {gm_db:.1f} dB",
                xy=(gm_freq, 0),
                xytext=(gm_freq * 2, 5),
                fontsize=9,
                color="g",
                arrowprops={"arrowstyle": "->", "color": "g"},
            )

    if phase_margin is not None:
        pm_deg_val, pm_freq = phase_margin
        if np.isfinite(pm_deg_val) and np.isfinite(pm_freq):
            ax_phase.axvline(x=pm_freq, color="m", linestyle=":", alpha=0.7)
            ax_phase.annotate(
                f"PM = {pm_deg_val:.1f}°",
                xy=(pm_freq, -180),
                xytext=(pm_freq * 2, -180 + pm_deg_val / 2),
                fontsize=9,
                color="m",
                arrowprops={"arrowstyle": "->", "color": "m"},
            )

    plt.tight_layout()
    return fig


def nyquist_plot(
    real: list[float],
    imag: list[float],
    *,
    title: str = "Nyquist Plot",
    unit_circle: bool = True,
    critical_point: bool = True,
    ax: Any | None = None,
    figsize: tuple[float, float] = (8, 8),
) -> Any:
    """Nyquist diagram (polar frequency response).

    Plots H(jω) in the complex plane.

    Parameters
    ----------
    real : list[float]
        Real part of H(jω).
    imag : list[float]
        Imaginary part of H(jω).
    title : str
        Plot title.
    unit_circle : bool
        If True, draw the unit circle.
    critical_point : bool
        If True, mark the critical point (-1, 0).
    ax : Axes | None
        Existing axes. Creates new if None.
    figsize : tuple[float, float]
        Figure size.

    Returns
    -------
    matplotlib Figure
    """
    _require_control_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    re = np.array(real)
    im = np.array(imag)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    # Positive frequencies
    ax.plot(re, im, "b-", linewidth=1.5, label="ω > 0")
    # Mirror (negative frequencies)
    ax.plot(re, -im, "b--", linewidth=0.8, alpha=0.5, label="ω < 0")

    if unit_circle:
        theta = np.linspace(0, 2 * np.pi, 200)
        ax.plot(np.cos(theta), np.sin(theta), "k--", linewidth=0.5, alpha=0.3)

    if critical_point:
        ax.plot(-1, 0, "rx", markersize=10, markeredgewidth=2, label="(-1, 0)")

    # Mark start and end
    ax.plot(re[0], im[0], "go", markersize=6, label=f"ω={0}")
    if len(re) > 1:
        ax.annotate(
            "",
            xy=(re[len(re) // 2], im[len(re) // 2]),
            xytext=(re[len(re) // 2 - 1], im[len(re) // 2 - 1]),
            arrowprops={"arrowstyle": "->", "color": "b"},
        )

    ax.set_xlabel("Real")
    ax.set_ylabel("Imaginary")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    return fig


def nichols_plot(
    phase_deg: list[float],
    mag_db: list[float],
    *,
    title: str = "Nichols Chart",
    m_circles: bool = True,
    n_circles: bool = False,
    ax: Any | None = None,
    figsize: tuple[float, float] = (10, 8),
) -> Any:
    """Nichols chart: open-loop phase (x) vs. open-loop gain (y).

    Parameters
    ----------
    phase_deg : list[float]
        Open-loop phase in degrees.
    mag_db : list[float]
        Open-loop magnitude in dB.
    title : str
        Plot title.
    m_circles : bool
        If True, draw M-circles (constant closed-loop magnitude contours).
    n_circles : bool
        If True, draw N-circles (constant closed-loop phase contours).
    ax : Axes | None
        Existing axes.
    figsize : tuple[float, float]
        Figure size.

    Returns
    -------
    matplotlib Figure
    """
    _require_control_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    phase = np.array(phase_deg)
    mag = np.array(mag_db)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.plot(phase, mag, "b-", linewidth=1.5)
    ax.plot(phase[0], mag[0], "go", markersize=6)
    ax.plot(phase[-1], mag[-1], "rs", markersize=5)

    # Mark critical point (-180°, 0 dB)
    ax.plot(-180, 0, "rx", markersize=10, markeredgewidth=2)

    if m_circles:
        # Draw M-circles at standard dB levels
        m_values_db = [-12, -6, -3, -1, 0.5, 1, 3, 6, 12]
        theta = np.linspace(-359, 0, 1000)

        for m_db in m_values_db:
            M = 10 ** (m_db / 20)
            if abs(M - 1.0) < 1e-10:
                continue
            # M-circle in Nichols coordinates
            # |T| = M where T = L/(1+L), L = G*e^{j*phase}
            # Parametric: for each open-loop phase, compute the gain
            # that gives |T| = M
            phase_rad = np.radians(theta)
            # |L / (1+L)| = M => |L|^2 = M^2 |1+L|^2
            # Let g = |L|: g^2 = M^2(1 + 2g*cos(phi) + g^2)
            # g^2(1-M^2) = M^2(1 + 2g*cos(phi))
            # This is quadratic in g
            cos_phi = np.cos(phase_rad)
            a_coeff = 1 - M**2
            b_coeff = -2 * M**2 * cos_phi
            c_coeff = -(M**2)

            discriminant = b_coeff**2 - 4 * a_coeff * c_coeff
            valid = discriminant >= 0
            g = np.full_like(theta, np.nan)
            if abs(a_coeff) > 1e-10:
                g[valid] = (-b_coeff[valid] + np.sqrt(discriminant[valid])) / (
                    2 * a_coeff
                )
                g_db = 20 * np.log10(np.maximum(g, 1e-15))
                mask = (g > 0) & np.isfinite(g_db) & (np.abs(g_db) < 40)
                if np.any(mask):
                    ax.plot(
                        theta[mask],
                        g_db[mask],
                        "k-",
                        linewidth=0.3,
                        alpha=0.3,
                    )

    ax.set_xlabel("Open-Loop Phase (deg)")
    ax.set_ylabel("Open-Loop Gain (dB)")
    ax.set_title(title)
    ax.set_xlim(-360, 0)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def root_locus_plot(
    num: list[float],
    den: list[float],
    *,
    gains: list[float] | None = None,
    title: str = "Root Locus",
    mark_poles: bool = True,
    mark_zeros: bool = True,
    ax: Any | None = None,
    figsize: tuple[float, float] = (8, 8),
) -> Any:
    """Root locus diagram.

    Shows pole migration as gain K varies from 0 to max.

    Parameters
    ----------
    num : list[float]
        Transfer function numerator coefficients (descending powers).
    den : list[float]
        Transfer function denominator coefficients (descending powers).
    gains : list[float] | None
        Gain values to evaluate. If None, auto-selects 500 values.
    title : str
        Plot title.
    mark_poles : bool
        If True, mark open-loop poles with x.
    mark_zeros : bool
        If True, mark open-loop zeros with o.
    ax : Axes | None
        Existing axes.
    figsize : tuple[float, float]
        Figure size.

    Returns
    -------
    matplotlib Figure
    """
    _require_control_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    num_arr = np.array(num, dtype=float)
    den_arr = np.array(den, dtype=float)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    if gains is None:
        # Auto-select gains: logarithmic sweep
        gains_arr = np.concatenate(
            [
                np.array([0.0]),
                np.logspace(-3, 3, 500),
            ]
        )
    else:
        gains_arr = np.array(gains, dtype=float)

    # Compute closed-loop poles for each gain
    n_poles = len(den_arr) - 1
    all_poles = np.zeros((len(gains_arr), n_poles), dtype=complex)

    for i, k in enumerate(gains_arr):
        # Closed-loop characteristic polynomial: den + K * num
        # Pad num to same length as den
        num_padded = np.zeros(len(den_arr))
        num_padded[-len(num_arr) :] = num_arr
        cl_poly = den_arr + k * num_padded
        roots = np.roots(cl_poly)

        # Sort roots to maintain continuity
        if i > 0:
            roots = _sort_poles_by_proximity(all_poles[i - 1], roots)
        all_poles[i] = roots

    # Plot pole trajectories
    cmap = plt.get_cmap("viridis")
    for j in range(n_poles):
        trajectory = all_poles[:, j]
        colors = [cmap(i / max(len(gains_arr) - 1, 1)) for i in range(len(gains_arr))]
        for k in range(1, len(trajectory)):
            ax.plot(
                [trajectory[k - 1].real, trajectory[k].real],
                [trajectory[k - 1].imag, trajectory[k].imag],
                "-",
                color=colors[k],
                linewidth=0.8,
                alpha=0.7,
            )

    # Mark open-loop poles and zeros
    if mark_poles:
        ol_poles = np.roots(den_arr)
        ax.plot(
            ol_poles.real,
            ol_poles.imag,
            "x",
            color="red",
            markersize=10,
            markeredgewidth=2,
            label="Open-loop poles",
        )

    if mark_zeros and len(num_arr) > 1:
        ol_zeros = np.roots(num_arr)
        ax.plot(
            ol_zeros.real,
            ol_zeros.imag,
            "o",
            color="blue",
            markersize=8,
            markerfacecolor="none",
            markeredgewidth=2,
            label="Open-loop zeros",
        )

    # Imaginary axis
    ax.axvline(x=0, color="k", linewidth=0.5, alpha=0.3)
    ax.axhline(y=0, color="k", linewidth=0.5, alpha=0.3)

    ax.set_xlabel("Real")
    ax.set_ylabel("Imaginary")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_aspect("equal")
    plt.tight_layout()
    return fig


def _sort_poles_by_proximity(prev_poles: Any, new_poles: Any) -> Any:
    """Sort new_poles to minimize distance from prev_poles (greedy matching)."""
    import numpy as np

    result = np.zeros_like(new_poles)
    available = list(range(len(new_poles)))

    for i in range(len(prev_poles)):
        if not available:
            break
        distances = [abs(new_poles[j] - prev_poles[i]) for j in available]
        best_idx = available[int(np.argmin(distances))]
        result[i] = new_poles[best_idx]
        available.remove(best_idx)

    return result

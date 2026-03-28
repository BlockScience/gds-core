"""Phase portrait visualization for continuous-time ODE systems.

Produces matplotlib figures: vector fields, trajectories, nullclines,
and backward reachable set boundaries (isochrones).

Requires ``gds-viz[phase]`` (matplotlib + numpy + gds-continuous).

Example::

    from gds_continuous import ODEModel
    from gds_viz.phase import phase_portrait

    model = ODEModel(
        state_names=["x", "v"],
        initial_state={"x": 1.0, "v": 0.0},
        rhs=my_ode_fn,
    )
    fig = phase_portrait(model, x_var="x", y_var="v", x_range=(-3, 3), y_range=(-3, 3))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds_continuous import ODEModel
    from gds_continuous.results import ODEResults


def _require_phase_deps() -> None:
    """Raise ImportError if matplotlib/numpy are absent."""
    try:
        import matplotlib  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Phase portrait visualization requires matplotlib and numpy. "
            "Install with: uv add gds-viz[phase]"
        ) from exc


@dataclass(frozen=True)
class PhasePlotConfig:
    """Configuration for a phase portrait."""

    x_var: str
    y_var: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    resolution: int = 20
    fixed_states: dict[str, float] = field(default_factory=dict)
    params: dict[str, float] = field(default_factory=dict)
    title: str = ""


def compute_vector_field(
    model: ODEModel,
    config: PhasePlotConfig,
    *,
    t: float = 0.0,
) -> tuple[Any, Any, Any, Any]:
    """Compute a 2D vector field over a grid.

    Parameters
    ----------
    model
        ODE model with the RHS function.
    config
        Grid specification (axes, ranges, resolution).
    t
        Time value for evaluating the RHS (default 0).

    Returns
    -------
    X, Y, dX, dY : numpy arrays
        Meshgrid coordinates and derivative components.
    """
    _require_phase_deps()
    import numpy as np

    x_idx = model.state_names.index(config.x_var)
    y_idx = model.state_names.index(config.y_var)

    xs = np.linspace(config.x_range[0], config.x_range[1], config.resolution)
    ys = np.linspace(config.y_range[0], config.y_range[1], config.resolution)
    X, Y = np.meshgrid(xs, ys)

    dX = np.zeros_like(X)
    dY = np.zeros_like(Y)

    # Build base state from fixed values
    base = [config.fixed_states.get(n, 0.0) for n in model.state_names]

    for i in range(config.resolution):
        for j in range(config.resolution):
            state = list(base)
            state[x_idx] = X[i, j]
            state[y_idx] = Y[i, j]
            deriv = model.rhs(t, state, config.params)
            dX[i, j] = deriv[x_idx]
            dY[i, j] = deriv[y_idx]

    return X, Y, dX, dY


def compute_trajectories(
    model: ODEModel,
    initial_conditions: list[dict[str, float]],
    *,
    t_span: tuple[float, float] = (0.0, 10.0),
    params: dict[str, float] | None = None,
    solver: str = "RK45",
    max_step: float = 0.05,
) -> list[ODEResults]:
    """Integrate multiple trajectories from different initial conditions.

    Parameters
    ----------
    model
        ODE model (``rhs`` is used, ``initial_state`` is overridden).
    initial_conditions
        List of state dicts, one per trajectory.
    t_span
        Integration time interval.
    params
        Parameter values (single set, not a sweep).
    solver
        SciPy solver name.
    max_step
        Maximum integration step size.

    Returns
    -------
    List of ODEResults, one per initial condition.
    """
    from gds_continuous import ODEModel as _ODEModel
    from gds_continuous import ODESimulation

    results = []
    p = params or {}
    for ic in initial_conditions:
        m = _ODEModel(
            state_names=model.state_names,
            initial_state=ic,
            rhs=model.rhs,
            params={k: [v] for k, v in p.items()},
        )
        sim = ODESimulation(
            model=m,
            t_span=t_span,
            solver=solver,  # type: ignore[arg-type]
            max_step=max_step,
        )
        results.append(sim.run())
    return results


def vector_field_plot(
    model: ODEModel,
    config: PhasePlotConfig,
    *,
    ax: Any | None = None,
    normalize: bool = True,
    color: str = "gray",
    alpha: float = 0.6,
) -> Any:
    """Plot a 2D vector field (quiver plot).

    Returns the matplotlib Figure.
    """
    _require_phase_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    X, Y, dX, dY = compute_vector_field(model, config)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    else:
        fig = ax.get_figure()

    if normalize:
        mag = np.sqrt(dX**2 + dY**2)
        mag = np.where(mag > 0, mag, 1.0)
        dX = dX / mag
        dY = dY / mag

    ax.quiver(X, Y, dX, dY, color=color, alpha=alpha, scale=25)
    ax.set_xlabel(config.x_var)
    ax.set_ylabel(config.y_var)
    ax.set_aspect("equal")
    if config.title:
        ax.set_title(config.title)
    ax.grid(True, alpha=0.3)
    return fig


def trajectory_plot(
    results_list: list[ODEResults],
    x_var: str,
    y_var: str,
    *,
    ax: Any | None = None,
    colormap: str = "viridis",
    linewidth: float = 1.0,
    show_start: bool = True,
    show_end: bool = True,
) -> Any:
    """Plot trajectories in phase space.

    Returns the matplotlib Figure.
    """
    _require_phase_deps()
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    else:
        fig = ax.get_figure()

    cmap = plt.get_cmap(colormap)
    n = max(len(results_list), 1)

    for i, res in enumerate(results_list):
        c = cmap(i / n)
        xs = res.state_array(x_var)
        ys = res.state_array(y_var)
        ax.plot(xs, ys, "-", color=c, linewidth=linewidth, alpha=0.8)
        if show_start:
            ax.plot(xs[0], ys[0], "o", color=c, markersize=5)
        if show_end:
            ax.plot(xs[-1], ys[-1], "s", color=c, markersize=4)

    ax.set_xlabel(x_var)
    ax.set_ylabel(y_var)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    return fig


def phase_portrait(
    model: ODEModel,
    x_var: str,
    y_var: str,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    initial_conditions: list[dict[str, float]] | None = None,
    params: dict[str, float] | None = None,
    fixed_states: dict[str, float] | None = None,
    t_span: tuple[float, float] = (0.0, 10.0),
    resolution: int = 20,
    title: str = "",
    show_nullclines: bool = False,
    figsize: tuple[float, float] = (10, 10),
) -> Any:
    """Full phase portrait: vector field + optional trajectories + nullclines.

    Parameters
    ----------
    model
        ODE model.
    x_var, y_var
        State variable names for the two axes.
    x_range, y_range
        Plot ranges for each axis.
    initial_conditions
        List of state dicts for trajectory integration. None = no trajectories.
    params
        Parameter values for RHS evaluation.
    fixed_states
        Values for state variables not on the axes (for >2D systems).
    t_span
        Integration time for trajectories.
    resolution
        Grid density for vector field.
    title
        Plot title.
    show_nullclines
        If True, draw zero-contours of dx/dt=0 and dy/dt=0.
    figsize
        Figure size.

    Returns
    -------
    matplotlib Figure.
    """
    _require_phase_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    config = PhasePlotConfig(
        x_var=x_var,
        y_var=y_var,
        x_range=x_range,
        y_range=y_range,
        resolution=resolution,
        fixed_states=fixed_states or {},
        params=params or {},
        title=title,
    )

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Vector field
    X, Y, dX, dY = compute_vector_field(model, config)
    mag = np.sqrt(dX**2 + dY**2)
    mag = np.where(mag > 0, mag, 1.0)
    ax.quiver(X, Y, dX / mag, dY / mag, color="gray", alpha=0.4, scale=25)

    # Nullclines
    if show_nullclines:
        ax.contour(X, Y, dX, levels=[0], colors=["blue"], linewidths=[1.5], alpha=0.6)
        ax.contour(X, Y, dY, levels=[0], colors=["red"], linewidths=[1.5], alpha=0.6)

    # Trajectories
    if initial_conditions:
        trajs = compute_trajectories(
            model, initial_conditions, t_span=t_span, params=params
        )
        cmap = plt.get_cmap("viridis")
        n = max(len(trajs), 1)
        for i, res in enumerate(trajs):
            c = cmap(i / n)
            xs = res.state_array(x_var)
            ys = res.state_array(y_var)
            ax.plot(xs, ys, "-", color=c, linewidth=1.2, alpha=0.8)
            ax.plot(xs[0], ys[0], "o", color=c, markersize=5)

    ax.set_xlabel(x_var)
    ax.set_ylabel(y_var)
    ax.set_xlim(x_range)
    ax.set_ylim(y_range)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

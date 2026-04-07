"""Step and impulse response visualization.

Provides annotated step response plots with performance metric annotations
(rise time, settling time, overshoot bands) and multi-response comparison.

All functions accept plain ``list[float]`` data. No imports from
gds-domains or gds-analysis — the caller computes data, the viz plots it.

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
            "Response visualization requires matplotlib and numpy. "
            "Install with: uv add gds-viz[control]"
        ) from exc


def step_response_plot(
    times: list[float],
    values: list[float],
    *,
    setpoint: float | None = None,
    metrics: Any | None = None,
    title: str = "Step Response",
    ax: Any | None = None,
    figsize: tuple[float, float] = (10, 6),
) -> Any:
    """Step response plot with optional metric annotations.

    Parameters
    ----------
    times : list[float]
        Time values.
    values : list[float]
        Response values.
    setpoint : float | None
        Desired final value. If provided, draws a reference line.
    metrics : StepMetrics | None
        If provided (from ``gds_analysis.response``), annotates:
        - Rise time (shaded region)
        - Settling time (vertical dashed line)
        - Overshoot (horizontal dashed line at peak)
        - ±2% settling band (shaded horizontal band)
    title : str
        Plot title.
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

    t = np.array(times)
    y = np.array(values)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.plot(t, y, "b-", linewidth=1.5, label="Response")

    if setpoint is not None:
        ax.axhline(
            y=setpoint,
            color="k",
            linewidth=0.8,
            linestyle="--",
            alpha=0.5,
            label=f"Setpoint = {setpoint}",
        )

    if metrics is not None:
        _annotate_metrics(ax, t, y, metrics)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    return fig


def _annotate_metrics(ax: Any, t: Any, y: Any, metrics: Any) -> None:
    """Add metric annotations to a step response plot."""
    ss = metrics.steady_state_value

    # Settling band (±2%)
    band = 0.02 * abs(ss) if abs(ss) > 1e-15 else 0.02
    ax.axhspan(
        ss - band,
        ss + band,
        color="green",
        alpha=0.08,
        label="±2% band",
    )

    # Settling time
    if metrics.settling_time > t[0]:
        ax.axvline(
            x=metrics.settling_time,
            color="green",
            linewidth=1,
            linestyle="--",
            alpha=0.7,
            label=f"Settling: {metrics.settling_time:.2f}s",
        )

    # Rise time
    if metrics.rise_time > 0:
        v0 = y[0]
        v_range = ss - v0
        t_low = _find_crossing_time(t, y, v0 + 0.1 * v_range)
        t_high = _find_crossing_time(t, y, v0 + 0.9 * v_range)
        if t_low < t_high:
            ax.axvspan(
                t_low,
                t_high,
                color="orange",
                alpha=0.1,
                label=f"Rise: {metrics.rise_time:.2f}s",
            )

    # Overshoot
    if metrics.overshoot_pct > 0:
        ax.axhline(
            y=metrics.peak_value,
            color="red",
            linewidth=0.8,
            linestyle=":",
            alpha=0.6,
        )
        ax.plot(
            metrics.peak_time,
            metrics.peak_value,
            "rv",
            markersize=8,
            label=f"Overshoot: {metrics.overshoot_pct:.1f}%",
        )

    # Steady-state error
    if metrics.steady_state_error > 0.001:
        ax.annotate(
            f"SS error: {metrics.steady_state_error:.4f}",
            xy=(t[-1] * 0.8, ss),
            fontsize=8,
            color="gray",
        )


def _find_crossing_time(t: Any, y: Any, threshold: float) -> float:
    """Find first time where y crosses threshold via linear interpolation.

    Note: identical logic exists in ``gds_analysis.response._interpolate_crossing``.
    Duplicated here to avoid a hard dependency on gds-analysis from gds-viz.
    """
    for i in range(1, len(y)):
        if (y[i - 1] <= threshold <= y[i]) or (y[i - 1] >= threshold >= y[i]):
            dv = y[i] - y[i - 1]
            if abs(dv) < 1e-15:
                return float(t[i])
            frac = (threshold - y[i - 1]) / dv
            return float(t[i - 1] + frac * (t[i] - t[i - 1]))
    return float(t[-1])


def impulse_response_plot(
    times: list[float],
    values: list[float],
    *,
    title: str = "Impulse Response",
    ax: Any | None = None,
    figsize: tuple[float, float] = (10, 6),
) -> Any:
    """Impulse response plot.

    Parameters
    ----------
    times : list[float]
        Time values.
    values : list[float]
        Impulse response values.
    title : str
        Plot title.
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

    t = np.array(times)
    y = np.array(values)

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.plot(t, y, "b-", linewidth=1.5)
    ax.axhline(y=0, color="k", linewidth=0.5, alpha=0.3)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def compare_responses(
    responses: list[tuple[list[float], list[float], str]],
    *,
    title: str = "Response Comparison",
    figsize: tuple[float, float] = (10, 6),
) -> Any:
    """Overlay multiple step/impulse responses for comparison.

    Parameters
    ----------
    responses : list[tuple[list[float], list[float], str]]
        Each tuple is ``(times, values, label)``.
    title : str
        Plot title.
    figsize : tuple[float, float]
        Figure size.

    Returns
    -------
    matplotlib Figure
    """
    _require_control_deps()
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    cmap = plt.get_cmap("tab10")
    n = max(len(responses), 1)

    for i, (times, values, label) in enumerate(responses):
        t = np.array(times)
        y = np.array(values)
        color = cmap(i / n)
        ax.plot(t, y, "-", color=color, linewidth=1.5, label=label)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    return fig

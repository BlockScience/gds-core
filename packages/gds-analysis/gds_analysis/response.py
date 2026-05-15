"""Step and impulse response computation with time-domain metrics.

Provides step/impulse response generation from state-space models and
extraction of standard performance metrics (rise time, settling time,
overshoot, steady-state error).

Requires ``gds-analysis[continuous]`` for response generation.
Metrics computation (``step_response_metrics``) works on any time-series
data and has no optional dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepMetrics:
    """Standard time-domain performance metrics for a step response.

    All time values are in the same units as the input time array.
    """

    rise_time: float
    """Time from ``rise_lower`` to ``rise_upper`` fraction of final value."""

    settling_time: float
    """Time to permanently enter the ±settling_band around final value."""

    overshoot_pct: float
    """Peak overshoot as a percentage of the final value. Zero if none."""

    peak_time: float
    """Time at which the first peak occurs."""

    peak_value: float
    """Response value at the first peak."""

    steady_state_value: float
    """Estimated final value (mean of last 5% of samples)."""

    steady_state_error: float
    """Absolute difference between setpoint and steady-state value."""


def step_response_metrics(
    times: list[float],
    values: list[float],
    setpoint: float = 1.0,
    *,
    settling_band: float = 0.02,
    rise_lower: float = 0.1,
    rise_upper: float = 0.9,
) -> StepMetrics:
    """Extract standard performance metrics from a step response.

    Works on any time-series data — can be fed from:

    - ``step_response()`` output (this module)
    - ``ODEResults.state_array()`` (gds-continuous)
    - gds-sim ``Results`` column extraction

    Parameters
    ----------
    times : list[float]
        Monotonically increasing time values.
    values : list[float]
        Response values at each time point.
    setpoint : float
        Desired final value (default 1.0 for unit step).
    settling_band : float
        Fractional band for settling time (default ±2%).
    rise_lower : float
        Lower fraction for rise time (default 10%).
    rise_upper : float
        Upper fraction for rise time (default 90%).

    Returns
    -------
    StepMetrics
        Computed performance metrics.
    """
    if len(times) < 2:
        raise ValueError("Need at least 2 data points")
    if len(times) != len(values):
        raise ValueError("times and values must have the same length")

    n = len(values)

    # Steady-state value: mean of last 5% of samples
    tail_count = max(1, n // 20)
    ss_value = sum(values[-tail_count:]) / tail_count
    ss_error = abs(setpoint - ss_value)

    # Initial value
    v0 = values[0]

    # Range from initial to steady-state
    v_range = ss_value - v0
    if abs(v_range) < 1e-15:
        # No change — return degenerate metrics
        return StepMetrics(
            rise_time=0.0,
            settling_time=0.0,
            overshoot_pct=0.0,
            peak_time=times[0],
            peak_value=values[0],
            steady_state_value=ss_value,
            steady_state_error=ss_error,
        )

    # Rise time: time from rise_lower to rise_upper fraction of final value
    low_threshold = v0 + rise_lower * v_range
    high_threshold = v0 + rise_upper * v_range

    t_low = _interpolate_crossing(times, values, low_threshold)
    t_high = _interpolate_crossing(times, values, high_threshold)
    rise_time = t_high - t_low if t_high > t_low else 0.0

    # Peak value and time
    if v_range > 0:
        peak_idx = max(range(n), key=lambda i: values[i])
    else:
        peak_idx = min(range(n), key=lambda i: values[i])
    peak_value = values[peak_idx]
    peak_time = times[peak_idx]

    # Overshoot percentage
    overshoot = (peak_value - ss_value) / abs(v_range) * 100.0
    overshoot_pct = max(0.0, overshoot) if v_range > 0 else max(0.0, -overshoot)

    # Settling time: backward scan
    band = settling_band * abs(ss_value) if abs(ss_value) > 1e-15 else settling_band
    settling_time = times[0]
    for i in range(n - 1, -1, -1):
        if abs(values[i] - ss_value) > band:
            settling_time = times[min(i + 1, n - 1)]
            break

    return StepMetrics(
        rise_time=rise_time,
        settling_time=settling_time,
        overshoot_pct=overshoot_pct,
        peak_time=peak_time,
        peak_value=peak_value,
        steady_state_value=ss_value,
        steady_state_error=ss_error,
    )


def _interpolate_crossing(
    times: list[float],
    values: list[float],
    threshold: float,
) -> float:
    """Find the first time at which values crosses threshold, with interpolation."""
    for i in range(1, len(values)):
        v_prev, v_curr = values[i - 1], values[i]
        if (v_prev <= threshold <= v_curr) or (v_prev >= threshold >= v_curr):
            # Linear interpolation
            dv = v_curr - v_prev
            if abs(dv) < 1e-15:
                return times[i]
            frac = (threshold - v_prev) / dv
            return times[i - 1] + frac * (times[i] - times[i - 1])
    # Threshold never crossed — return last time
    return times[-1]


def step_response(
    A: list[list[float]],
    B: list[list[float]],
    C: list[list[float]],
    D: list[list[float]],
    t_span: tuple[float, float] = (0.0, 10.0),
    n_points: int = 1000,
    *,
    input_index: int = 0,
) -> tuple[list[float], list[list[float]]]:
    """Compute unit step response from a state-space model.

    Applies a unit step to the specified input and simulates.

    Parameters
    ----------
    A, B, C, D : list[list[float]]
        State-space matrices.
    t_span : tuple[float, float]
        Simulation time interval.
    n_points : int
        Number of evaluation points.
    input_index : int
        Which input channel receives the step (default 0).

    Returns
    -------
    (times, outputs)
        ``times`` is a list of float. ``outputs[i]`` is the response
        of output i as a list of float.

    Requires
    --------
    ``gds-analysis[continuous]`` (scipy + numpy).
    """
    try:
        import numpy as np
        from scipy import signal
    except ImportError as exc:
        raise ImportError(
            "step_response requires scipy and numpy. "
            "Install with: uv add gds-analysis[continuous]"
        ) from exc

    sys = signal.StateSpace(
        np.array(A, dtype=float),
        np.array(B, dtype=float),
        np.array(C, dtype=float),
        np.array(D, dtype=float),
    )
    t_eval = np.linspace(t_span[0], t_span[1], n_points)

    # Use lsim with step input
    n_inputs = np.array(B).shape[1] if len(A) > 0 else np.array(D).shape[1]
    u_input = np.zeros((n_points, n_inputs))
    u_input[:, input_index] = 1.0

    tout, yout, _ = signal.lsim(sys, U=u_input, T=t_eval)

    times = tout.tolist()
    if yout.ndim == 1:
        outputs = [yout.tolist()]
    else:
        outputs = [yout[:, i].tolist() for i in range(yout.shape[1])]

    return times, outputs


def impulse_response(
    A: list[list[float]],
    B: list[list[float]],
    C: list[list[float]],
    D: list[list[float]],
    t_span: tuple[float, float] = (0.0, 10.0),
    n_points: int = 1000,
    *,
    input_index: int = 0,
) -> tuple[list[float], list[list[float]]]:
    """Compute impulse response from a state-space model.

    Parameters
    ----------
    A, B, C, D : list[list[float]]
        State-space matrices.
    t_span : tuple[float, float]
        Simulation time interval.
    n_points : int
        Number of evaluation points.
    input_index : int
        Which input channel receives the impulse (default 0).

    Returns
    -------
    (times, outputs)
        ``times`` is a list of float. ``outputs[i]`` is the response
        of output i as a list of float.

    Requires
    --------
    ``gds-analysis[continuous]`` (scipy + numpy).
    """
    try:
        import numpy as np
        from scipy import signal
    except ImportError as exc:
        raise ImportError(
            "impulse_response requires scipy and numpy. "
            "Install with: uv add gds-analysis[continuous]"
        ) from exc

    a = np.array(A, dtype=float)
    b = np.array(B, dtype=float)
    c = np.array(C, dtype=float)
    d = np.array(D, dtype=float)

    # Extract SISO for the specified input
    b_col = b[:, input_index : input_index + 1] if len(A) > 0 else np.array([[0.0]])
    d_col = d[:, input_index : input_index + 1]

    sys = signal.StateSpace(a, b_col, c, d_col)
    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    tout, yout = signal.impulse(sys, T=t_eval)

    times = tout.tolist()
    if yout.ndim == 1:
        outputs = [yout.tolist()]
    else:
        outputs = [yout[:, i].tolist() for i in range(yout.shape[1])]

    return times, outputs


def metrics_from_ode_results(
    results: Any,
    state_name: str,
    setpoint: float = 1.0,
    **kwargs: Any,
) -> StepMetrics:
    """Extract step metrics from an ``ODEResults`` object.

    Convenience wrapper: calls ``results.times`` and
    ``results.state_array(state_name)``, then delegates to
    ``step_response_metrics()``.

    Parameters
    ----------
    results
        An ``ODEResults`` object from gds-continuous.
    state_name : str
        Name of the state variable to analyze.
    setpoint : float
        Desired final value.
    **kwargs
        Passed through to ``step_response_metrics()``.
    """
    times = results.times
    values = results.state_array(state_name)
    return step_response_metrics(times, values, setpoint, **kwargs)

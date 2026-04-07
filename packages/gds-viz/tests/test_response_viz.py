"""Tests for step/impulse response visualization."""

import math

import pytest

from gds_viz.response import (
    compare_responses,
    impulse_response_plot,
    step_response_plot,
)


@pytest.fixture(autouse=True)
def _mpl_backend():
    """Use non-interactive backend for CI."""
    import matplotlib

    matplotlib.use("Agg")


@pytest.fixture()
def sample_step_data() -> tuple[list[float], list[float]]:
    """First-order step response: y = 1 - e^{-t}."""
    n = 200
    t_max = 8.0
    times = [i * t_max / (n - 1) for i in range(n)]
    values = [1.0 - math.exp(-t) for t in times]
    return times, values


class TestStepResponsePlot:
    def test_returns_figure(self, sample_step_data: tuple) -> None:
        times, values = sample_step_data
        fig = step_response_plot(times, values)
        assert fig is not None

    def test_with_setpoint(self, sample_step_data: tuple) -> None:
        times, values = sample_step_data
        fig = step_response_plot(times, values, setpoint=1.0)
        ax = fig.get_axes()[0]
        # Should have response line + setpoint line
        assert len(ax.lines) >= 2

    def test_with_metrics_annotation(self, sample_step_data: tuple) -> None:
        """Verify metrics annotations don't crash and add artists."""
        from gds_analysis.response import StepMetrics

        times, values = sample_step_data
        metrics = StepMetrics(
            rise_time=2.2,
            settling_time=4.0,
            overshoot_pct=0.0,
            peak_time=8.0,
            peak_value=0.999,
            steady_state_value=1.0,
            steady_state_error=0.0,
        )
        fig = step_response_plot(times, values, setpoint=1.0, metrics=metrics)
        assert fig is not None
        # Should have patches (settling band, rise time span)
        ax = fig.get_axes()[0]
        assert len(ax.patches) >= 1  # At least the settling band

    def test_with_overshoot_metrics(self) -> None:
        """Verify overshoot annotation renders."""
        from gds_analysis.response import StepMetrics

        times = [0.0, 0.5, 1.0, 1.5, 2.0, 5.0]
        values = [0.0, 0.8, 1.2, 1.05, 1.0, 1.0]
        metrics = StepMetrics(
            rise_time=0.6,
            settling_time=2.0,
            overshoot_pct=20.0,
            peak_time=1.0,
            peak_value=1.2,
            steady_state_value=1.0,
            steady_state_error=0.0,
        )
        fig = step_response_plot(times, values, metrics=metrics)
        assert fig is not None

    def test_custom_title(self, sample_step_data: tuple) -> None:
        times, values = sample_step_data
        fig = step_response_plot(times, values, title="My Step")
        ax = fig.get_axes()[0]
        assert ax.get_title() == "My Step"

    def test_existing_axes(self, sample_step_data: tuple) -> None:
        import matplotlib.pyplot as plt

        times, values = sample_step_data
        fig, ax = plt.subplots()
        result = step_response_plot(times, values, ax=ax)
        assert result is fig


class TestImpulseResponsePlot:
    def test_returns_figure(self) -> None:
        times = [0.0, 1.0, 2.0, 3.0, 4.0]
        values = [1.0, 0.37, 0.14, 0.05, 0.02]
        fig = impulse_response_plot(times, values)
        assert fig is not None

    def test_has_zero_line(self) -> None:
        fig = impulse_response_plot([0.0, 1.0], [1.0, 0.0])
        ax = fig.get_axes()[0]
        # Should have the response line + zero reference line
        assert len(ax.lines) >= 2


class TestCompareResponses:
    def test_returns_figure_with_multiple_lines(self) -> None:
        responses = [
            ([0.0, 1.0, 2.0], [0.0, 0.6, 0.9], "Slow"),
            ([0.0, 1.0, 2.0], [0.0, 0.9, 1.0], "Fast"),
            ([0.0, 1.0, 2.0], [0.0, 1.2, 1.0], "Overshoot"),
        ]
        fig = compare_responses(responses)
        ax = fig.get_axes()[0]
        assert len(ax.lines) == 3

    def test_single_response(self) -> None:
        fig = compare_responses(
            [
                ([0.0, 1.0], [0.0, 1.0], "Only one"),
            ]
        )
        assert fig is not None

    def test_legend_present(self) -> None:
        fig = compare_responses(
            [
                ([0.0, 1.0], [0.0, 1.0], "A"),
                ([0.0, 1.0], [0.0, 0.5], "B"),
            ]
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None

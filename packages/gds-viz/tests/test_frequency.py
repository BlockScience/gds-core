"""Tests for frequency response and root locus plots."""

import pytest

from gds_viz.frequency import (
    bode_plot,
    nichols_plot,
    nyquist_plot,
    root_locus_plot,
)


@pytest.fixture(autouse=True)
def _mpl_backend():
    """Use non-interactive backend for CI."""
    import matplotlib

    matplotlib.use("Agg")


class TestBodePlot:
    def test_returns_figure_with_two_axes(self) -> None:
        omega = [0.1, 1.0, 10.0, 100.0]
        mag_db = [0.0, -3.0, -20.0, -40.0]
        phase_deg = [0.0, -45.0, -90.0, -90.0]

        fig = bode_plot(omega, mag_db, phase_deg)

        assert fig is not None
        axes = fig.get_axes()
        assert len(axes) == 2

    def test_magnitude_axis_is_semilog(self) -> None:
        fig = bode_plot([0.1, 10.0], [-3.0, -20.0], [-45.0, -90.0])
        ax_mag = fig.get_axes()[0]
        assert ax_mag.get_xscale() == "log"

    def test_with_margin_annotations(self) -> None:
        fig = bode_plot(
            [0.1, 1.0, 10.0],
            [20.0, 0.0, -20.0],
            [-90.0, -135.0, -180.0],
            gain_margin=(6.0, 5.0),
            phase_margin=(45.0, 1.0),
        )
        assert fig is not None

    def test_with_existing_axes(self) -> None:
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1)
        result = bode_plot([0.1, 10.0], [-3.0, -20.0], [-45.0, -90.0], ax=(ax1, ax2))
        assert result is fig

    def test_custom_title(self) -> None:
        fig = bode_plot([1.0], [0.0], [-90.0], title="My Custom Bode")
        ax = fig.get_axes()[0]
        assert ax.get_title() == "My Custom Bode"


class TestNyquistPlot:
    def test_returns_figure(self) -> None:
        real = [1.0, 0.5, 0.0, -0.5]
        imag = [0.0, -0.5, -1.0, -0.5]

        fig = nyquist_plot(real, imag)
        assert fig is not None

    def test_has_critical_point_marker(self) -> None:
        fig = nyquist_plot([1.0, 0.0], [0.0, -1.0])
        ax = fig.get_axes()[0]
        # Should have line artists for the curve + mirror + unit circle + critical point
        assert len(ax.lines) >= 3

    def test_equal_aspect(self) -> None:
        fig = nyquist_plot([1.0, 0.0], [0.0, -1.0])
        ax = fig.get_axes()[0]
        # matplotlib may return "equal", "equalxy", or 1.0 depending on version
        assert ax.get_aspect() in ("equal", "equalxy", 1.0)


class TestNicholsPlot:
    def test_returns_figure(self) -> None:
        phase = [-90.0, -135.0, -180.0, -225.0]
        mag = [20.0, 6.0, 0.0, -6.0]

        fig = nichols_plot(phase, mag)
        assert fig is not None

    def test_x_axis_limits(self) -> None:
        fig = nichols_plot([-100.0, -200.0], [10.0, -10.0])
        ax = fig.get_axes()[0]
        xlim = ax.get_xlim()
        assert xlim[0] == -360
        assert xlim[1] == 0

    def test_without_m_circles(self) -> None:
        fig = nichols_plot([-90.0, -180.0], [0.0, -10.0], m_circles=False)
        assert fig is not None


class TestRootLocusPlot:
    def test_returns_figure(self) -> None:
        # 1/(s^2 + s + 1): two poles
        num = [1.0]
        den = [1.0, 1.0, 1.0]

        fig = root_locus_plot(num, den)
        assert fig is not None

    def test_marks_poles_and_zeros(self) -> None:
        # (s+2)/(s^2+3s+2) = (s+2)/((s+1)(s+2)): 2 poles, 1 zero
        num = [1.0, 2.0]
        den = [1.0, 3.0, 2.0]

        fig = root_locus_plot(num, den, mark_poles=True, mark_zeros=True)
        ax = fig.get_axes()[0]
        # Should have line artists for trajectories + poles marker + zeros marker
        assert len(ax.lines) >= 3

    def test_custom_gains(self) -> None:
        fig = root_locus_plot([1.0], [1.0, 2.0, 1.0], gains=[0.0, 0.5, 1.0, 5.0, 10.0])
        assert fig is not None

    def test_equal_aspect(self) -> None:
        fig = root_locus_plot([1.0], [1.0, 1.0])
        ax = fig.get_axes()[0]
        # matplotlib may return "equal", "equalxy", or 1.0 depending on version
        assert ax.get_aspect() in ("equal", "equalxy", 1.0)

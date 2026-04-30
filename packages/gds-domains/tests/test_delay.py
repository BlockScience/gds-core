"""Tests for Padé approximation of time delays."""

import math

import pytest

from gds_domains.symbolic.delay import delay_system, pade_approximation
from gds_domains.symbolic.transfer import TransferFunction, poles, zeros


class TestPadeApproximation:
    def test_order_1_coefficients(self) -> None:
        """Order-1 Padé of 1s delay: (-s/2 + 1)/(s/2 + 1)."""
        tf = pade_approximation(1.0, order=1)
        # num and den should be order 1 polynomials
        assert len(tf.num) == 2
        assert len(tf.den) == 2

    def test_allpass_property(self) -> None:
        """Padé approximation should be approximately all-pass: |H(jw)| ≈ 1."""
        tf = pade_approximation(0.5, order=3)

        # Evaluate |H(jw)| at several frequencies using polynomial evaluation
        for omega in [0.1, 1.0, 5.0, 10.0]:
            jw = complex(0, omega)
            num_val = sum(
                c * jw**i for i, c in enumerate(reversed(tf.num))
            )
            den_val = sum(
                c * jw**i for i, c in enumerate(reversed(tf.den))
            )
            mag = abs(num_val / den_val)
            assert mag == pytest.approx(1.0, abs=0.01), (
                f"|H(j{omega})| = {mag}, expected ≈ 1.0"
            )

    def test_rhp_zeros(self) -> None:
        """Order-N Padé should have N zeros in the right half-plane."""
        for order in [1, 2, 3]:
            tf = pade_approximation(0.5, order=order)
            z = zeros(tf)
            rhp_zeros = [zi for zi in z if zi.real > 0]
            assert len(rhp_zeros) == order

    def test_lhp_poles(self) -> None:
        """Order-N Padé should have N poles in the left half-plane."""
        for order in [1, 2, 3]:
            tf = pade_approximation(0.5, order=order)
            p = poles(tf)
            lhp_poles = [pi for pi in p if pi.real < 0]
            assert len(lhp_poles) == order

    def test_phase_accuracy_low_frequency(self) -> None:
        """At low frequencies, Padé phase should match -w*tau."""
        tau = 0.5
        tf = pade_approximation(tau, order=3)

        for omega in [0.1, 0.5, 1.0]:
            jw = complex(0, omega)
            num_val = sum(
                c * jw**i for i, c in enumerate(reversed(tf.num))
            )
            den_val = sum(
                c * jw**i for i, c in enumerate(reversed(tf.den))
            )
            H = num_val / den_val
            pade_phase = math.atan2(H.imag, H.real)
            exact_phase = -omega * tau

            assert pade_phase == pytest.approx(exact_phase, abs=0.05), (
                f"At w={omega}: Padé phase={pade_phase:.4f}, "
                f"exact={exact_phase:.4f}"
            )

    def test_invalid_delay(self) -> None:
        with pytest.raises(ValueError, match="delay must be > 0"):
            pade_approximation(0.0)
        with pytest.raises(ValueError, match="delay must be > 0"):
            pade_approximation(-1.0)

    def test_invalid_order(self) -> None:
        with pytest.raises(ValueError, match="order must be >= 1"):
            pade_approximation(1.0, order=0)


class TestDelaySystem:
    def test_pole_count(self) -> None:
        """Delayed system should have original poles + Padé poles."""
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])  # 1/(s+1)
        delayed = delay_system(plant, delay=0.5, order=2)

        p = poles(delayed)
        # Original: 1 pole. Padé order 2: 2 poles. Total: 3.
        assert len(p) == 3

    def test_invalid_delay(self) -> None:
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])
        with pytest.raises(ValueError, match="delay must be > 0"):
            delay_system(plant, delay=0.0)

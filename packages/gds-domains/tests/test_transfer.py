"""Tests for symbolic transfer function analysis."""

import pytest

from gds_domains.symbolic.linearize import LinearizedSystem
from gds_domains.symbolic.transfer import (
    TransferFunction,
    characteristic_polynomial,
    controllability_matrix,
    is_controllable,
    is_minimum_phase,
    is_observable,
    observability_matrix,
    poles,
    sensitivity,
    ss_to_tf,
    zeros,
)

# ---------------------------------------------------------------------------
# Fixtures: canonical test systems
# ---------------------------------------------------------------------------


@pytest.fixture()
def first_order_system() -> LinearizedSystem:
    """1/(s+1): A=[-1], B=[1], C=[1], D=[0]."""
    return LinearizedSystem(
        A=[[-1.0]],
        B=[[1.0]],
        C=[[1.0]],
        D=[[0.0]],
        x0=[0.0],
        u0=[0.0],
        state_names=["x"],
        input_names=["u"],
        output_names=["y"],
    )


@pytest.fixture()
def double_integrator() -> LinearizedSystem:
    """1/s^2: two poles at origin."""
    return LinearizedSystem(
        A=[[0.0, 1.0], [0.0, 0.0]],
        B=[[0.0], [1.0]],
        C=[[1.0, 0.0]],
        D=[[0.0]],
        x0=[0.0, 0.0],
        u0=[0.0],
        state_names=["position", "velocity"],
        input_names=["force"],
        output_names=["position_out"],
    )


@pytest.fixture()
def second_order_underdamped() -> LinearizedSystem:
    """wn=1, zeta=0.5: poles at -0.5 +/- j*sqrt(3)/2."""
    return LinearizedSystem(
        A=[[0.0, 1.0], [-1.0, -1.0]],
        B=[[0.0], [1.0]],
        C=[[1.0, 0.0]],
        D=[[0.0]],
        x0=[0.0, 0.0],
        u0=[0.0],
        state_names=["x", "v"],
        input_names=["u"],
        output_names=["y"],
    )


@pytest.fixture()
def non_minimum_phase() -> LinearizedSystem:
    """System with a RHP zero: H(s) = (s-1)/((s+1)(s+2))."""
    return LinearizedSystem(
        A=[[0.0, 1.0], [-2.0, -3.0]],
        B=[[0.0], [1.0]],
        C=[[-1.0, 1.0]],
        D=[[0.0]],
        x0=[0.0, 0.0],
        u0=[0.0],
        state_names=["x1", "x2"],
        input_names=["u"],
        output_names=["y"],
    )


@pytest.fixture()
def uncontrollable_system() -> LinearizedSystem:
    """System where B doesn't span the state space."""
    return LinearizedSystem(
        A=[[-1.0, 0.0], [0.0, -2.0]],
        B=[[1.0], [0.0]],
        C=[[1.0, 1.0]],
        D=[[0.0]],
        x0=[0.0, 0.0],
        u0=[0.0],
        state_names=["x1", "x2"],
        input_names=["u"],
        output_names=["y"],
    )


# ---------------------------------------------------------------------------
# Transfer function conversion
# ---------------------------------------------------------------------------


class TestSsToTf:
    def test_first_order(self, first_order_system: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(first_order_system)
        assert len(tf_mat.elements) == 1
        assert len(tf_mat.elements[0]) == 1
        tf = tf_mat.elements[0][0]

        # H(s) = 1/(s+1) → num=[1], den=[1, 1]
        assert len(tf.num) == 1
        assert len(tf.den) == 2
        assert tf.num[0] == pytest.approx(1.0, abs=1e-10)
        assert tf.den[0] == pytest.approx(1.0, abs=1e-10)
        assert tf.den[1] == pytest.approx(1.0, abs=1e-10)

    def test_double_integrator(self, double_integrator: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(double_integrator)
        tf = tf_mat.elements[0][0]

        # H(s) = 1/s^2 → num=[1], den=[1, 0, 0]
        assert tf.num[-1] == pytest.approx(1.0, abs=1e-10)
        assert tf.den[0] == pytest.approx(1.0, abs=1e-10)
        assert tf.den[1] == pytest.approx(0.0, abs=1e-10)
        assert tf.den[2] == pytest.approx(0.0, abs=1e-10)

    def test_preserves_names(self, first_order_system: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(first_order_system)
        assert tf_mat.input_names == ["u"]
        assert tf_mat.output_names == ["y"]
        assert tf_mat.elements[0][0].input_name == "u"
        assert tf_mat.elements[0][0].output_name == "y"


# ---------------------------------------------------------------------------
# Characteristic polynomial
# ---------------------------------------------------------------------------


class TestCharacteristicPolynomial:
    def test_first_order(self, first_order_system: LinearizedSystem) -> None:
        cp = characteristic_polynomial(first_order_system)
        # det(sI - [-1]) = s + 1
        assert len(cp) == 2
        assert cp[0] == pytest.approx(1.0, abs=1e-10)
        assert cp[1] == pytest.approx(1.0, abs=1e-10)

    def test_double_integrator(self, double_integrator: LinearizedSystem) -> None:
        cp = characteristic_polynomial(double_integrator)
        # det(sI - [[0,1],[0,0]]) = s^2
        assert len(cp) == 3
        assert cp[0] == pytest.approx(1.0, abs=1e-10)
        assert cp[1] == pytest.approx(0.0, abs=1e-10)
        assert cp[2] == pytest.approx(0.0, abs=1e-10)

    def test_empty_system(self) -> None:
        ls = LinearizedSystem(A=[], B=[], C=[], D=[], x0=[], u0=[])
        cp = characteristic_polynomial(ls)
        assert cp == [1.0]


# ---------------------------------------------------------------------------
# Poles and zeros
# ---------------------------------------------------------------------------


class TestPolesZeros:
    def test_first_order_pole(self, first_order_system: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(first_order_system)
        tf = tf_mat.elements[0][0]
        p = poles(tf)
        assert len(p) == 1
        assert p[0].real == pytest.approx(-1.0, abs=1e-6)
        assert abs(p[0].imag) < 1e-6

    def test_double_integrator_poles(self, double_integrator: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(double_integrator)
        tf = tf_mat.elements[0][0]
        p = poles(tf)
        assert len(p) == 2
        for pi in p:
            assert abs(pi) < 1e-6  # Both at origin

    def test_underdamped_poles(
        self, second_order_underdamped: LinearizedSystem
    ) -> None:
        tf_mat = ss_to_tf(second_order_underdamped)
        tf = tf_mat.elements[0][0]
        p = poles(tf)
        assert len(p) == 2
        # Both should have negative real part
        for pi in p:
            assert pi.real < 0

    def test_first_order_no_zeros(self, first_order_system: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(first_order_system)
        tf = tf_mat.elements[0][0]
        z = zeros(tf)
        assert len(z) == 0

    def test_minimum_phase(self, first_order_system: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(first_order_system)
        assert is_minimum_phase(tf_mat.elements[0][0])

    def test_non_minimum_phase(self, non_minimum_phase: LinearizedSystem) -> None:
        tf_mat = ss_to_tf(non_minimum_phase)
        tf = tf_mat.elements[0][0]
        z = zeros(tf)
        # Should have at least one RHP zero
        assert any(zi.real > 0 for zi in z)
        assert not is_minimum_phase(tf)


# ---------------------------------------------------------------------------
# Controllability / Observability
# ---------------------------------------------------------------------------


class TestControllabilityObservability:
    def test_double_integrator_controllable(
        self, double_integrator: LinearizedSystem
    ) -> None:
        assert is_controllable(double_integrator)

    def test_double_integrator_observable(
        self, double_integrator: LinearizedSystem
    ) -> None:
        assert is_observable(double_integrator)

    def test_uncontrollable(self, uncontrollable_system: LinearizedSystem) -> None:
        assert not is_controllable(uncontrollable_system)

    def test_controllability_matrix_shape(
        self, double_integrator: LinearizedSystem
    ) -> None:
        cm = controllability_matrix(double_integrator)
        assert len(cm) == 2  # n rows
        assert len(cm[0]) == 2  # n*m columns (2 states, 1 input)

    def test_observability_matrix_shape(
        self, double_integrator: LinearizedSystem
    ) -> None:
        om = observability_matrix(double_integrator)
        assert len(om) == 2  # n*p rows (2 states, 1 output)
        assert len(om[0]) == 2  # n columns

    def test_empty_system(self) -> None:
        ls = LinearizedSystem(A=[], B=[], C=[], D=[], x0=[], u0=[])
        assert is_controllable(ls)
        assert is_observable(ls)


# ---------------------------------------------------------------------------
# Sensitivity (Gang of Six)
# ---------------------------------------------------------------------------


class TestSensitivity:
    def test_s_plus_t_equals_one(self) -> None:
        """S + T = 1 is a fundamental identity."""
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])  # 1/(s+1)
        controller = TransferFunction(num=[2.0], den=[1.0])  # K=2

        gang = sensitivity(plant, controller)

        # Verify S + T = 1 by checking that num_S * den_T + num_T * den_S
        # equals den_S * den_T (all should be the same denominator)
        s_tf = gang["S"]
        t_tf = gang["T"]

        # S and T should have the same denominator
        assert len(s_tf.den) == len(t_tf.den)
        for a, b in zip(s_tf.den, t_tf.den, strict=False):
            assert a == pytest.approx(b, abs=1e-10)

        # S_num + T_num should equal the denominator
        # Pad shorter one
        max_len = max(len(s_tf.num), len(t_tf.num))
        s_padded = [0.0] * (max_len - len(s_tf.num)) + s_tf.num
        t_padded = [0.0] * (max_len - len(t_tf.num)) + t_tf.num
        d_padded = [0.0] * (max_len - len(s_tf.den)) + s_tf.den

        summed = [a + b for a, b in zip(s_padded, t_padded, strict=False)]
        for a, b in zip(summed, d_padded, strict=False):
            assert a == pytest.approx(b, abs=1e-10)

    def test_returns_all_six(self) -> None:
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])
        controller = TransferFunction(num=[1.0], den=[1.0])

        gang = sensitivity(plant, controller)
        assert set(gang.keys()) == {"S", "T", "CS", "PS", "KS", "KPS"}

    def test_sensitivity_dc_values(self) -> None:
        """Verify S(0) and T(0) at DC for P=1/(s+1), K=2.

        L(0) = P(0)*K(0) = 1*2 = 2
        S(0) = 1/(1+L(0)) = 1/3
        T(0) = L(0)/(1+L(0)) = 2/3
        """
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])
        controller = TransferFunction(num=[2.0], den=[1.0])

        gang = sensitivity(plant, controller)

        # Evaluate S at s=0: ratio of constant terms
        s_tf = gang["S"]
        s_dc = s_tf.num[-1] / s_tf.den[-1]
        assert s_dc == pytest.approx(1.0 / 3.0, abs=1e-10)

        t_tf = gang["T"]
        t_dc = t_tf.num[-1] / t_tf.den[-1]
        assert t_dc == pytest.approx(2.0 / 3.0, abs=1e-10)

    def test_cs_is_controller_times_s(self) -> None:
        """CS = K*S: verify CS(0) = K(0)*S(0) = 2*(1/3) = 2/3."""
        plant = TransferFunction(num=[1.0], den=[1.0, 1.0])
        controller = TransferFunction(num=[2.0], den=[1.0])

        gang = sensitivity(plant, controller)
        cs_tf = gang["CS"]
        cs_dc = cs_tf.num[-1] / cs_tf.den[-1]
        assert cs_dc == pytest.approx(2.0 / 3.0, abs=1e-10)


# ---------------------------------------------------------------------------
# MIMO transfer functions
# ---------------------------------------------------------------------------


class TestMIMO:
    def test_2x2_system(self) -> None:
        """2-input, 2-output system: verify matrix dimensions."""
        ls = LinearizedSystem(
            A=[[-1.0, 0.0], [0.0, -2.0]],
            B=[[1.0, 0.0], [0.0, 1.0]],
            C=[[1.0, 0.0], [0.0, 1.0]],
            D=[[0.0, 0.0], [0.0, 0.0]],
            x0=[0.0, 0.0],
            u0=[0.0, 0.0],
            state_names=["x1", "x2"],
            input_names=["u1", "u2"],
            output_names=["y1", "y2"],
        )
        tf_mat = ss_to_tf(ls)

        # Should be 2x2
        assert len(tf_mat.elements) == 2
        assert len(tf_mat.elements[0]) == 2
        assert len(tf_mat.elements[1]) == 2

    def test_2x2_diagonal_system_dc_gains(self) -> None:
        """Diagonal A, identity B and C: verify DC gains.

        H11(s) = (s+2)/((s+1)(s+2)) → H11(0) = 2/2 = 1.0
        H22(s) = (s+1)/((s+1)(s+2)) → H22(0) = 1/2 = 0.5
        Note: denominator is the full characteristic polynomial for all elements.
        """
        ls = LinearizedSystem(
            A=[[-1.0, 0.0], [0.0, -2.0]],
            B=[[1.0, 0.0], [0.0, 1.0]],
            C=[[1.0, 0.0], [0.0, 1.0]],
            D=[[0.0, 0.0], [0.0, 0.0]],
            x0=[0.0, 0.0],
            u0=[0.0, 0.0],
            state_names=["x1", "x2"],
            input_names=["u1", "u2"],
            output_names=["y1", "y2"],
        )
        tf_mat = ss_to_tf(ls)

        # DC gain = num(0)/den(0) = constant_term_num / constant_term_den
        h11 = tf_mat.elements[0][0]
        h11_dc = h11.num[-1] / h11.den[-1]
        assert h11_dc == pytest.approx(1.0, abs=1e-8)

        h22 = tf_mat.elements[1][1]
        h22_dc = h22.num[-1] / h22.den[-1]
        assert h22_dc == pytest.approx(0.5, abs=1e-8)

    def test_nonzero_D_feedthrough(self) -> None:
        """System with D != 0: verify DC gain includes feedthrough."""
        ls = LinearizedSystem(
            A=[[-1.0]],
            B=[[1.0]],
            C=[[1.0]],
            D=[[2.0]],
            x0=[0.0],
            u0=[0.0],
            state_names=["x"],
            input_names=["u"],
            output_names=["y"],
        )
        tf_mat = ss_to_tf(ls)
        tf = tf_mat.elements[0][0]

        # H(s) = 1/(s+1) + 2 = (2s + 3)/(s + 1)
        # DC gain H(0) = 3/1 = 3
        dc_gain = tf.num[-1] / tf.den[-1]
        assert dc_gain == pytest.approx(3.0, abs=1e-8)

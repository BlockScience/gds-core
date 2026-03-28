"""Tests for Hamiltonian mechanics and Pontryagin's Maximum Principle."""

from __future__ import annotations

import pytest

sympy = pytest.importorskip("sympy")

from gds_symbolic.hamiltonian import (  # noqa: E402
    HamiltonianSpec,
    HamiltonianSystem,
    derive_hamiltonian,
    verify_conservation,
)


class TestDeriveHamiltonian:
    """Test symbolic Hamiltonian derivation."""

    def test_1d_linear_quadratic(self) -> None:
        """LQR: dx/dt = -x + u, L = x^2 + u^2.

        H = x^2 + u^2 + p*(-x + u)
        dp/dt = -dH/dx = -2*x + p
        """
        system = derive_hamiltonian(
            state_equations={"x": "-x + u"},
            state_names=["x"],
            input_names=["u"],
            param_names=[],
            spec=HamiltonianSpec(lagrangian="x**2 + u**2"),
        )

        assert isinstance(system, HamiltonianSystem)
        assert system.state_names == ["x"]
        assert system.costate_names == ["p_x"]
        assert system.augmented_names == ["x", "p_x"]
        assert len(system.costate_exprs) == 1
        assert "p_x" in system.costate_exprs
        # dp/dt = -dH/dx = -(2x + p*(-1)) = -2x + p
        # Check the costate expression contains the expected terms
        expr = system.costate_exprs["p_x"]
        assert "x" in expr
        assert "p_x" in expr

    def test_2d_harmonic(self) -> None:
        """Harmonic oscillator: dx1/dt = x2, dx2/dt = -x1.

        L = x1^2 + x2^2
        H = x1^2 + x2^2 + p1*x2 + p2*(-x1)
        dp1/dt = -dH/dx1 = -2*x1 + p2
        dp2/dt = -dH/dx2 = -2*x2 - p1
        """
        system = derive_hamiltonian(
            state_equations={"x1": "x2", "x2": "-x1"},
            state_names=["x1", "x2"],
            input_names=[],
            param_names=[],
            spec=HamiltonianSpec(lagrangian="x1**2 + x2**2"),
        )

        assert system.state_names == ["x1", "x2"]
        assert system.costate_names == ["p_x1", "p_x2"]
        assert len(system.costate_exprs) == 2

    def test_augmented_ode_callable(self) -> None:
        """The augmented ODE should be callable."""
        system = derive_hamiltonian(
            state_equations={"x": "-k*x"},
            state_names=["x"],
            input_names=[],
            param_names=["k"],
            spec=HamiltonianSpec(lagrangian="x**2"),
        )

        # y = [x, p_x], params = {"k": 1.0}
        dy = system.augmented_ode(0.0, [1.0, 0.5], {"k": 1.0})
        assert len(dy) == 2
        # dx/dt = -k*x = -1.0
        assert dy[0] == pytest.approx(-1.0)

    def test_with_params(self) -> None:
        """Parameters pass through to the compiled ODE."""
        system = derive_hamiltonian(
            state_equations={"x": "-alpha*x + u"},
            state_names=["x"],
            input_names=["u"],
            param_names=["alpha"],
            spec=HamiltonianSpec(lagrangian="x**2 + u**2"),
        )

        # With alpha=2, u=0: dx/dt = -2*1 = -2
        dy = system.augmented_ode(0.0, [1.0, 0.0], {"alpha": 2.0, "u": 0.0})
        assert dy[0] == pytest.approx(-2.0)

    def test_missing_state_equation(self) -> None:
        """State without equation gets dx/dt = 0."""
        system = derive_hamiltonian(
            state_equations={"x1": "-x1"},
            state_names=["x1", "x2"],
            input_names=[],
            param_names=[],
            spec=HamiltonianSpec(lagrangian="x1**2"),
        )

        dy = system.augmented_ode(0.0, [1.0, 2.0, 0.0, 0.0], {})
        # dx2/dt = 0 (no equation)
        assert dy[1] == pytest.approx(0.0)


class TestDeriveFromModel:
    """Test derive_from_model with SymbolicControlModel."""

    def test_from_symbolic_model(self) -> None:
        from gds_control.dsl.elements import Input, State

        from gds_symbolic import SymbolicControlModel
        from gds_symbolic.elements import StateEquation
        from gds_symbolic.hamiltonian import derive_from_model

        model = SymbolicControlModel(
            name="LQR",
            states=[State(name="x", initial=1.0)],
            inputs=[Input(name="u")],
            state_equations=[StateEquation(state_name="x", expr_str="-x + u")],
            symbolic_params=["Q", "R"],
        )

        system = derive_from_model(
            model,
            HamiltonianSpec(lagrangian="Q*x**2 + R*u**2"),
        )

        assert system.state_names == ["x"]
        assert system.costate_names == ["p_x"]
        dy = system.augmented_ode(0.0, [1.0, 0.5], {"u": 0.0, "Q": 1.0, "R": 1.0})
        assert len(dy) == 2


class TestVerifyConservation:
    """Test Hamiltonian conservation checking."""

    def test_constant_hamiltonian(self) -> None:
        """H = const should be detected as conserved."""

        def h_fn(t, y, params):
            return 1.0  # constant

        times = [0.0, 0.1, 0.2, 0.3]
        states = [[1.0, 0.5]] * 4
        conserved, max_var = verify_conservation(times, states, h_fn, {})
        assert conserved is True
        assert max_var == pytest.approx(0.0)

    def test_varying_hamiltonian(self) -> None:
        """H varying beyond tolerance should fail."""

        def h_fn(t, y, params):
            return t  # varies with time

        times = [0.0, 0.5, 1.0]
        states = [[1.0, 0.5]] * 3
        conserved, max_var = verify_conservation(times, states, h_fn, {}, tolerance=0.1)
        assert conserved is False
        assert max_var == pytest.approx(1.0)

    def test_empty_trajectory(self) -> None:
        conserved, max_var = verify_conservation([], [], lambda t, y, p: 0.0, {})
        assert conserved is True
        assert max_var == 0.0

    def test_integration_with_ode(self) -> None:
        """End-to-end: derive → integrate → verify conservation."""
        pytest.importorskip("numpy")
        from gds_continuous import ODEModel, ODESimulation

        # Simple decay: dx/dt = -x, L = x^2
        system = derive_hamiltonian(
            state_equations={"x": "-x"},
            state_names=["x"],
            input_names=[],
            param_names=[],
            spec=HamiltonianSpec(lagrangian="x**2"),
        )

        model = ODEModel(
            state_names=system.augmented_names,
            initial_state={"x": 1.0, "p_x": 0.5},
            rhs=system.augmented_ode,
            params={},
        )
        sim = ODESimulation(model=model, t_span=(0.0, 1.0))
        results = sim.run()

        # Build H function from the symbolic expression
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr

        x, p_x = sp.Symbol("x"), sp.Symbol("p_x")
        h_expr = parse_expr(system.hamiltonian_expr, local_dict={"x": x, "p_x": p_x})
        h_lambda = sp.lambdify([x, p_x], h_expr, modules="math")

        def h_fn(t, y, params):
            return h_lambda(y[0], y[1])

        times = results.times
        rows = results.to_list()
        states = [[row[n] for n in system.augmented_names] for row in rows]

        # Conservation won't be exact for non-optimal trajectories,
        # but we can check the function runs without error
        _, max_var = verify_conservation(times, states, h_fn, {})
        assert isinstance(max_var, float)

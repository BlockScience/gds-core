"""Tests for parameter space constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gds_psuu import (
    KPI,
    Continuous,
    Discrete,
    FunctionalConstraint,
    GridSearchOptimizer,
    Integer,
    LinearConstraint,
    ParameterSpace,
    PsuuSearchError,
    PsuuValidationError,
    RandomSearchOptimizer,
    Sweep,
    final_state_mean,
)

if TYPE_CHECKING:
    from gds_sim import Model


class TestLinearConstraint:
    def test_feasible(self) -> None:
        c = LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=10.0)
        assert c.is_feasible({"a": 3.0, "b": 5.0}) is True

    def test_infeasible(self) -> None:
        c = LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=10.0)
        assert c.is_feasible({"a": 6.0, "b": 5.0}) is False

    def test_boundary(self) -> None:
        c = LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=10.0)
        assert c.is_feasible({"a": 5.0, "b": 5.0}) is True  # exactly equal

    def test_empty_coefficients_rejected(self) -> None:
        with pytest.raises(
            (PsuuValidationError, ValueError),
            match="at least 1 coefficient",
        ):
            LinearConstraint(coefficients={}, bound=10.0)

    def test_negative_coefficients(self) -> None:
        c = LinearConstraint(coefficients={"a": 1.0, "b": -1.0}, bound=0.0)
        # a - b <= 0 means a <= b
        assert c.is_feasible({"a": 3.0, "b": 5.0}) is True
        assert c.is_feasible({"a": 5.0, "b": 3.0}) is False


class TestFunctionalConstraint:
    def test_feasible(self) -> None:
        c = FunctionalConstraint(fn=lambda p: p["x"] > 0)
        assert c.is_feasible({"x": 1.0}) is True

    def test_infeasible(self) -> None:
        c = FunctionalConstraint(fn=lambda p: p["x"] > 0)
        assert c.is_feasible({"x": -1.0}) is False

    def test_multi_param(self) -> None:
        c = FunctionalConstraint(fn=lambda p: p["a"] * p["b"] < 100)
        assert c.is_feasible({"a": 5, "b": 10}) is True
        assert c.is_feasible({"a": 20, "b": 10}) is False


class TestParameterSpaceConstraints:
    def test_no_constraints_default(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=10)})
        assert space.constraints == ()

    def test_is_feasible_no_constraints(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=10)})
        assert space.is_feasible({"x": 5.0}) is True

    def test_is_feasible_with_linear(self) -> None:
        space = ParameterSpace(
            params={
                "a": Continuous(min_val=0, max_val=100),
                "b": Continuous(min_val=0, max_val=100),
            },
            constraints=(
                LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=100.0),
            ),
        )
        assert space.is_feasible({"a": 40.0, "b": 50.0}) is True
        assert space.is_feasible({"a": 60.0, "b": 50.0}) is False

    def test_is_feasible_with_functional(self) -> None:
        space = ParameterSpace(
            params={
                "x": Continuous(min_val=0, max_val=10),
                "y": Continuous(min_val=0, max_val=10),
            },
            constraints=(FunctionalConstraint(fn=lambda p: p["x"] < p["y"]),),
        )
        assert space.is_feasible({"x": 3, "y": 5}) is True
        assert space.is_feasible({"x": 5, "y": 3}) is False

    def test_multiple_constraints(self) -> None:
        space = ParameterSpace(
            params={
                "a": Continuous(min_val=0, max_val=100),
                "b": Continuous(min_val=0, max_val=100),
            },
            constraints=(
                LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=100.0),
                FunctionalConstraint(fn=lambda p: p["a"] >= 10),
            ),
        )
        # Satisfies both
        assert space.is_feasible({"a": 40.0, "b": 50.0}) is True
        # Fails first constraint
        assert space.is_feasible({"a": 60.0, "b": 50.0}) is False
        # Fails second constraint
        assert space.is_feasible({"a": 5.0, "b": 10.0}) is False

    def test_linear_constraint_unknown_param_rejected(self) -> None:
        with pytest.raises((PsuuValidationError, ValueError), match="unknown params"):
            ParameterSpace(
                params={"a": Continuous(min_val=0, max_val=10)},
                constraints=(
                    LinearConstraint(coefficients={"a": 1.0, "z": 1.0}, bound=10.0),
                ),
            )

    def test_grid_points_filtered(self) -> None:
        space = ParameterSpace(
            params={
                "a": Continuous(min_val=0, max_val=10),
                "b": Continuous(min_val=0, max_val=10),
            },
            constraints=(
                LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=10.0),
            ),
        )
        points = space.grid_points(n_steps=3)  # 0, 5, 10 for each
        # Valid: (0,0), (0,5), (0,10), (5,0), (5,5), (10,0) = 6 of 9
        assert len(points) == 6
        for p in points:
            assert p["a"] + p["b"] <= 10.0

    def test_grid_points_no_constraints_unchanged(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=10)})
        points = space.grid_points(n_steps=3)
        assert len(points) == 3

    def test_grid_points_all_infeasible(self) -> None:
        space = ParameterSpace(
            params={"x": Continuous(min_val=0, max_val=10)},
            constraints=(FunctionalConstraint(fn=lambda p: False),),
        )
        points = space.grid_points(n_steps=3)
        assert points == []


class TestGridOptimizerWithConstraints:
    def test_grid_respects_constraints(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={
                "growth_rate": Continuous(min_val=0.01, max_val=0.1),
            },
            constraints=(FunctionalConstraint(fn=lambda p: p["growth_rate"] <= 0.06),),
        )
        sweep = Sweep(
            model=simple_model,
            space=space,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=3),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        # 3 grid points: 0.01, 0.055, 0.1 — only first two are <= 0.06
        assert len(results.evaluations) == 2


class TestRandomOptimizerWithConstraints:
    def test_random_respects_constraints(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={
                "growth_rate": Continuous(min_val=0.01, max_val=0.1),
            },
            constraints=(FunctionalConstraint(fn=lambda p: p["growth_rate"] <= 0.05),),
        )
        sweep = Sweep(
            model=simple_model,
            space=space,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=RandomSearchOptimizer(n_samples=10, seed=42),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 10
        for ev in results.evaluations:
            assert ev.params["growth_rate"] <= 0.05

    def test_random_infeasible_raises(self) -> None:
        space = ParameterSpace(
            params={"x": Continuous(min_val=0, max_val=10)},
            constraints=(FunctionalConstraint(fn=lambda p: False),),
        )
        opt = RandomSearchOptimizer(n_samples=1, seed=0)
        opt.setup(space, ["kpi"])
        with pytest.raises(PsuuSearchError, match="feasible point"):
            opt.suggest()

    def test_random_no_constraints_unchanged(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=10)})
        opt = RandomSearchOptimizer(n_samples=5, seed=42)
        opt.setup(space, ["kpi"])
        points = [opt.suggest() for _ in range(5)]
        assert len(points) == 5
        assert opt.is_exhausted()


class TestConstraintWithIntegerAndDiscrete:
    def test_integer_with_linear_constraint(self) -> None:
        space = ParameterSpace(
            params={
                "a": Integer(min_val=1, max_val=5),
                "b": Integer(min_val=1, max_val=5),
            },
            constraints=(
                LinearConstraint(coefficients={"a": 1.0, "b": 1.0}, bound=5.0),
            ),
        )
        points = space.grid_points(n_steps=0)  # n_steps ignored for Integer
        for p in points:
            assert p["a"] + p["b"] <= 5

    def test_discrete_with_functional_constraint(self) -> None:
        space = ParameterSpace(
            params={
                "strategy": Discrete(values=("A", "B", "C")),
                "x": Continuous(min_val=0, max_val=10),
            },
            constraints=(FunctionalConstraint(fn=lambda p: p["strategy"] != "C"),),
        )
        points = space.grid_points(n_steps=3)
        # 3 discrete * 3 continuous = 9, minus 3 where strategy="C" = 6
        assert len(points) == 6
        for p in points:
            assert p["strategy"] != "C"

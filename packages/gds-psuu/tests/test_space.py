"""Tests for parameter space definitions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gds_psuu import Continuous, Discrete, Integer, ParameterSpace
from gds_psuu.errors import PsuuValidationError


class TestContinuous:
    def test_valid(self) -> None:
        c = Continuous(min_val=0.0, max_val=1.0)
        assert c.min_val == 0.0
        assert c.max_val == 1.0

    def test_invalid_bounds(self) -> None:
        with pytest.raises(ValidationError, match="must be less than"):
            Continuous(min_val=1.0, max_val=0.0)

    def test_equal_bounds(self) -> None:
        with pytest.raises(ValidationError, match="must be less than"):
            Continuous(min_val=1.0, max_val=1.0)

    def test_infinite_bounds(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            Continuous(min_val=0.0, max_val=float("inf"))

    def test_frozen(self) -> None:
        c = Continuous(min_val=0.0, max_val=1.0)
        with pytest.raises(ValidationError):
            c.min_val = 0.5  # type: ignore[misc]


class TestInteger:
    def test_valid(self) -> None:
        i = Integer(min_val=1, max_val=10)
        assert i.min_val == 1
        assert i.max_val == 10

    def test_invalid_bounds(self) -> None:
        with pytest.raises(ValidationError):
            Integer(min_val=10, max_val=1)


class TestDiscrete:
    def test_valid(self) -> None:
        d = Discrete(values=("a", "b", "c"))
        assert d.values == ("a", "b", "c")

    def test_single_value(self) -> None:
        d = Discrete(values=("only",))
        assert len(d.values) == 1

    def test_empty_values(self) -> None:
        with pytest.raises(ValidationError, match="at least 1"):
            Discrete(values=())


class TestParameterSpace:
    def test_empty_space(self) -> None:
        with pytest.raises(ValidationError, match="at least 1"):
            ParameterSpace(params={})

    def test_dimension_names(self, simple_space: ParameterSpace) -> None:
        assert simple_space.dimension_names == ["growth_rate", "strategy"]

    def test_grid_points_continuous(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0.0, max_val=1.0)})
        points = space.grid_points(n_steps=3)
        assert len(points) == 3
        assert points[0] == {"x": 0.0}
        assert points[1] == {"x": 0.5}
        assert points[2] == {"x": 1.0}

    def test_grid_points_integer(self) -> None:
        space = ParameterSpace(params={"n": Integer(min_val=1, max_val=3)})
        points = space.grid_points(n_steps=2)
        assert points == [{"n": 1}, {"n": 2}, {"n": 3}]

    def test_grid_points_discrete(self) -> None:
        space = ParameterSpace(params={"mode": Discrete(values=("fast", "slow"))})
        points = space.grid_points(n_steps=2)
        assert points == [{"mode": "fast"}, {"mode": "slow"}]

    def test_grid_cartesian_product(self) -> None:
        space = ParameterSpace(
            params={
                "x": Continuous(min_val=0.0, max_val=1.0),
                "mode": Discrete(values=("a", "b")),
            }
        )
        points = space.grid_points(n_steps=2)
        assert len(points) == 4  # 2 x 2
        assert points[0] == {"x": 0.0, "mode": "a"}
        assert points[3] == {"x": 1.0, "mode": "b"}

    def test_grid_n_steps_too_small(self) -> None:
        space = ParameterSpace(params={"x": Continuous(min_val=0.0, max_val=1.0)})
        with pytest.raises(PsuuValidationError, match="n_steps must be >= 2"):
            space.grid_points(n_steps=1)

"""Tests for optimizer implementations."""

from __future__ import annotations

import pytest

from gds_analysis.psuu import (
    Continuous,
    Discrete,
    GridSearchOptimizer,
    Integer,
    ParameterSpace,
    RandomSearchOptimizer,
)


@pytest.fixture
def continuous_space() -> ParameterSpace:
    return ParameterSpace(params={"x": Continuous(min_val=0.0, max_val=1.0)})


@pytest.fixture
def mixed_space() -> ParameterSpace:
    return ParameterSpace(
        params={
            "x": Continuous(min_val=0.0, max_val=1.0),
            "n": Integer(min_val=1, max_val=3),
            "mode": Discrete(values=("a", "b")),
        }
    )


class TestGridSearchOptimizer:
    def test_exhaustive(self, continuous_space: ParameterSpace) -> None:
        opt = GridSearchOptimizer(n_steps=3)
        opt.setup(continuous_space, ["kpi"])
        points = []
        while not opt.is_exhausted():
            points.append(opt.suggest())
        assert len(points) == 3
        assert points[0] == {"x": 0.0}
        assert points[1] == {"x": 0.5}
        assert points[2] == {"x": 1.0}

    def test_mixed_space(self, mixed_space: ParameterSpace) -> None:
        opt = GridSearchOptimizer(n_steps=2)
        opt.setup(mixed_space, ["kpi"])
        points = []
        while not opt.is_exhausted():
            p = opt.suggest()
            opt.observe(p, {"kpi": 0.0})
            points.append(p)
        # 2 continuous * 3 integer * 2 discrete = 12
        assert len(points) == 12

    def test_observe_is_noop(self, continuous_space: ParameterSpace) -> None:
        opt = GridSearchOptimizer(n_steps=2)
        opt.setup(continuous_space, ["kpi"])
        p = opt.suggest()
        opt.observe(p, {"kpi": 42.0})  # Should not raise


class TestRandomSearchOptimizer:
    def test_correct_count(self, continuous_space: ParameterSpace) -> None:
        opt = RandomSearchOptimizer(n_samples=5, seed=42)
        opt.setup(continuous_space, ["kpi"])
        points = []
        while not opt.is_exhausted():
            points.append(opt.suggest())
        assert len(points) == 5

    def test_deterministic_with_seed(self, continuous_space: ParameterSpace) -> None:
        opt1 = RandomSearchOptimizer(n_samples=3, seed=42)
        opt1.setup(continuous_space, ["kpi"])
        points1 = [opt1.suggest() for _ in range(3)]

        opt2 = RandomSearchOptimizer(n_samples=3, seed=42)
        opt2.setup(continuous_space, ["kpi"])
        points2 = [opt2.suggest() for _ in range(3)]

        assert points1 == points2

    def test_values_in_bounds(self, continuous_space: ParameterSpace) -> None:
        opt = RandomSearchOptimizer(n_samples=50, seed=0)
        opt.setup(continuous_space, ["kpi"])
        for _ in range(50):
            p = opt.suggest()
            assert 0.0 <= p["x"] <= 1.0

    def test_integer_bounds(self) -> None:
        space = ParameterSpace(params={"n": Integer(min_val=1, max_val=5)})
        opt = RandomSearchOptimizer(n_samples=50, seed=0)
        opt.setup(space, ["kpi"])
        for _ in range(50):
            p = opt.suggest()
            assert 1 <= p["n"] <= 5
            assert isinstance(p["n"], int)

    def test_discrete_values(self) -> None:
        space = ParameterSpace(params={"mode": Discrete(values=("a", "b", "c"))})
        opt = RandomSearchOptimizer(n_samples=50, seed=0)
        opt.setup(space, ["kpi"])
        seen = set()
        for _ in range(50):
            p = opt.suggest()
            assert p["mode"] in ("a", "b", "c")
            seen.add(p["mode"])
        assert seen == {"a", "b", "c"}  # Very likely with 50 samples

    def test_mixed_space(self, mixed_space: ParameterSpace) -> None:
        opt = RandomSearchOptimizer(n_samples=10, seed=0)
        opt.setup(mixed_space, ["kpi"])
        for _ in range(10):
            p = opt.suggest()
            assert "x" in p
            assert "n" in p
            assert "mode" in p

"""Tests for ODEResults columnar storage."""

from __future__ import annotations

import pytest

from gds_continuous.results import ODEResults


class TestAppend:
    """Row-by-row append."""

    def test_basic_append(self) -> None:
        r = ODEResults(["x", "v"])
        r.append(0.0, [1.0, 0.0])
        r.append(0.1, [0.99, -0.1])
        assert len(r) == 2

    def test_preallocated_append(self) -> None:
        r = ODEResults(["x"], capacity=10)
        for i in range(10):
            r.append(float(i), [float(i * 2)])
        assert len(r) == 10

    def test_overflow_to_dynamic(self) -> None:
        r = ODEResults(["x"], capacity=2)
        r.append(0.0, [1.0])
        r.append(1.0, [2.0])
        r.append(2.0, [3.0])  # exceeds capacity
        assert len(r) == 3

    def test_with_metadata(self) -> None:
        r = ODEResults(["x"])
        r.append(0.0, [1.0], run=2, subset=3)
        rows = r.to_list()
        assert rows[0]["run"] == 2
        assert rows[0]["subset"] == 3

    def test_with_outputs(self) -> None:
        r = ODEResults(["x"], output_names=["y"])
        r.append(0.0, [1.0], outputs=[2.0])
        rows = r.to_list()
        assert rows[0]["y"] == 2.0


class TestAppendSolution:
    """Bulk append from scipy solution arrays."""

    def test_append_solution(self) -> None:
        r = ODEResults(["x", "v"])
        t = [0.0, 0.1, 0.2]
        y = [[1.0, 0.99, 0.98], [0.0, -0.1, -0.2]]  # shape (2, 3)
        r.append_solution(t, y, run=0, subset=0)
        assert len(r) == 3
        assert r.times == [0.0, 0.1, 0.2]
        assert r.state_array("x") == [1.0, 0.99, 0.98]
        assert r.state_array("v") == [0.0, -0.1, -0.2]


class TestConversion:
    """to_list and to_dataframe."""

    def test_to_list(self) -> None:
        r = ODEResults(["x"])
        r.append(0.0, [1.0])
        r.append(1.0, [2.0])
        rows = r.to_list()
        assert len(rows) == 2
        assert rows[0] == {"time": 0.0, "run": 0, "subset": 0, "x": 1.0}
        assert rows[1] == {"time": 1.0, "run": 0, "subset": 0, "x": 2.0}

    def test_to_list_preallocated_trimmed(self) -> None:
        r = ODEResults(["x"], capacity=100)
        r.append(0.0, [1.0])
        r.append(1.0, [2.0])
        rows = r.to_list()
        assert len(rows) == 2

    def test_to_dataframe(self) -> None:
        pytest.importorskip("pandas")
        r = ODEResults(["x", "v"])
        r.append(0.0, [1.0, 0.0])
        r.append(0.1, [0.99, -0.1])
        df = r.to_dataframe()
        assert list(df.columns) == ["time", "run", "subset", "x", "v"]
        assert len(df) == 2


class TestAccessors:
    """Property and method accessors."""

    def test_state_names(self) -> None:
        r = ODEResults(["alpha", "beta"])
        assert r.state_names == ["alpha", "beta"]

    def test_times(self) -> None:
        r = ODEResults(["x"])
        r.append(0.0, [1.0])
        r.append(0.5, [0.5])
        assert r.times == [0.0, 0.5]

    def test_state_array(self) -> None:
        r = ODEResults(["x", "v"])
        r.append(0.0, [1.0, 0.0])
        r.append(0.1, [0.9, -0.1])
        assert r.state_array("x") == [1.0, 0.9]
        assert r.state_array("v") == [0.0, -0.1]


class TestMerge:
    """Merging multiple results."""

    def test_merge_two(self) -> None:
        r1 = ODEResults(["x"])
        r1.append(0.0, [1.0], subset=0)
        r1.append(1.0, [2.0], subset=0)

        r2 = ODEResults(["x"])
        r2.append(0.0, [10.0], subset=1)
        r2.append(1.0, [20.0], subset=1)

        merged = ODEResults.merge([r1, r2])
        assert len(merged) == 4
        rows = merged.to_list()
        assert rows[0]["subset"] == 0
        assert rows[2]["subset"] == 1

    def test_merge_empty(self) -> None:
        merged = ODEResults.merge([])
        assert len(merged) == 0

    def test_merge_single(self) -> None:
        r = ODEResults(["x"])
        r.append(0.0, [1.0])
        merged = ODEResults.merge([r])
        assert merged is r

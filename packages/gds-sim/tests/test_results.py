"""Tests for columnar result storage."""

from __future__ import annotations

import gds_sim


class TestResults:
    def test_append_and_len(self) -> None:
        r = gds_sim.Results(["x", "y"])
        r.append({"x": 1, "y": 2}, timestep=0, substep=0, run=0, subset=0)
        r.append({"x": 3, "y": 4}, timestep=1, substep=1, run=0, subset=0)
        assert len(r) == 2

    def test_to_list(self) -> None:
        r = gds_sim.Results(["x"])
        r.append({"x": 10}, timestep=0, substep=0, run=0, subset=0)
        r.append({"x": 20}, timestep=1, substep=1, run=0, subset=0)
        rows = r.to_list()
        assert len(rows) == 2
        assert rows[0] == {"timestep": 0, "substep": 0, "run": 0, "subset": 0, "x": 10}
        assert rows[1] == {"timestep": 1, "substep": 1, "run": 0, "subset": 0, "x": 20}

    def test_preallocated(self) -> None:
        r = gds_sim.Results(["a", "b"], capacity=5)
        for i in range(3):
            r.append({"a": i, "b": i * 10}, timestep=i, substep=0, run=0, subset=0)
        assert len(r) == 3
        rows = r.to_list()
        assert len(rows) == 3
        assert rows[2]["a"] == 2

    def test_preallocated_overflow_to_append(self) -> None:
        r = gds_sim.Results(["x"], capacity=2)
        for i in range(4):
            r.append({"x": i}, timestep=i, substep=0, run=0, subset=0)
        assert len(r) == 4

    def test_to_dataframe(self) -> None:
        pd = __import__("pytest").importorskip("pandas")

        r = gds_sim.Results(["val"])
        r.append({"val": 100}, timestep=0, substep=0, run=0, subset=0)
        r.append({"val": 200}, timestep=1, substep=1, run=0, subset=0)
        df = r.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["timestep", "substep", "run", "subset", "val"]
        assert df["val"].tolist() == [100, 200]

    def test_merge(self) -> None:
        r1 = gds_sim.Results(["x"])
        r1.append({"x": 1}, timestep=0, substep=0, run=0, subset=0)

        r2 = gds_sim.Results(["x"])
        r2.append({"x": 2}, timestep=0, substep=0, run=1, subset=0)

        merged = gds_sim.Results.merge([r1, r2])
        assert len(merged) == 2
        rows = merged.to_list()
        assert rows[0]["x"] == 1
        assert rows[1]["x"] == 2

    def test_merge_empty(self) -> None:
        merged = gds_sim.Results.merge([])
        assert len(merged) == 0

    def test_merge_single(self) -> None:
        r = gds_sim.Results(["x"])
        r.append({"x": 42}, timestep=0, substep=0, run=0, subset=0)
        merged = gds_sim.Results.merge([r])
        assert merged is r


class TestResultsFromSimulation:
    def test_to_dataframe_from_sim(self, simple_model: gds_sim.Model) -> None:
        pd = __import__("pytest").importorskip("pandas")

        sim = gds_sim.Simulation(model=simple_model, timesteps=5)
        df = sim.run().to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert "population" in df.columns
        assert "food" in df.columns
        assert "timestep" in df.columns

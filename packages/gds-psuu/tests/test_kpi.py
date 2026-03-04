"""Tests for KPI wrapper and helper functions."""

from __future__ import annotations

from gds_sim import Model, Results, Simulation, StateUpdateBlock

from gds_psuu import KPI, final_state_mean, final_state_std, time_average


def _identity_update(state: dict, params: dict, **kw: object) -> tuple[str, float]:
    return ("value", state["value"])


def _growing_update(state: dict, params: dict, **kw: object) -> tuple[str, float]:
    return ("value", state["value"] + 10.0)


def _make_results(
    initial: float, updater: object, timesteps: int = 5, runs: int = 1
) -> Results:
    model = Model(
        initial_state={"value": initial},
        state_update_blocks=[StateUpdateBlock(variables={"value": updater})],
    )
    sim = Simulation(model=model, timesteps=timesteps, runs=runs)
    return sim.run()


class TestKPI:
    def test_kpi_creation(self) -> None:
        kpi = KPI(name="test", fn=lambda r: 42.0)
        assert kpi.name == "test"
        assert kpi.fn(None) == 42.0  # type: ignore[arg-type]


class TestFinalStateMean:
    def test_constant_value(self) -> None:
        results = _make_results(100.0, _identity_update, timesteps=5, runs=1)
        assert final_state_mean(results, "value") == 100.0

    def test_growing_value(self) -> None:
        results = _make_results(0.0, _growing_update, timesteps=3, runs=1)
        # After 3 timesteps: 0 + 3*10 = 30
        assert final_state_mean(results, "value") == 30.0

    def test_multiple_runs(self) -> None:
        results = _make_results(100.0, _identity_update, timesteps=3, runs=3)
        # All runs identical → mean = 100
        assert final_state_mean(results, "value") == 100.0

    def test_empty_results(self) -> None:
        results = Results(state_keys=["value"])
        assert final_state_mean(results, "value") == 0.0


class TestFinalStateStd:
    def test_identical_runs(self) -> None:
        results = _make_results(100.0, _identity_update, timesteps=3, runs=3)
        assert final_state_std(results, "value") == 0.0

    def test_single_run(self) -> None:
        results = _make_results(100.0, _identity_update, timesteps=3, runs=1)
        assert final_state_std(results, "value") == 0.0


class TestTimeAverage:
    def test_constant(self) -> None:
        results = _make_results(100.0, _identity_update, timesteps=3, runs=1)
        assert time_average(results, "value") == 100.0

    def test_growing(self) -> None:
        results = _make_results(0.0, _growing_update, timesteps=2, runs=1)
        # Rows: t=0 s=0 → 0, t=1 s=1 → 10, t=2 s=1 → 20
        avg = time_average(results, "value")
        assert avg == 10.0  # (0 + 10 + 20) / 3

    def test_empty(self) -> None:
        results = Results(state_keys=["value"])
        assert time_average(results, "value") == 0.0

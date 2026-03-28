"""Tests for trajectory distance computation."""

import pytest
from gds import GDSSpec
from gds.constraints import StateMetric

from gds_analysis.metrics import trajectory_distances


class TestTrajectoryDistances:
    def test_euclidean_distance(self, thermostat_spec: GDSSpec) -> None:
        trajectory = [
            {"Room.temperature": 18.0},
            {"Room.temperature": 20.0},
            {"Room.temperature": 21.0},
        ]
        result = trajectory_distances(thermostat_spec, trajectory)
        assert "temp_distance" in result
        assert len(result["temp_distance"]) == 2
        assert result["temp_distance"][0] == pytest.approx(2.0)
        assert result["temp_distance"][1] == pytest.approx(1.0)

    def test_single_metric_by_name(self, thermostat_spec: GDSSpec) -> None:
        trajectory = [
            {"Room.temperature": 0.0},
            {"Room.temperature": 3.0},
        ]
        result = trajectory_distances(
            thermostat_spec, trajectory, metric_name="temp_distance"
        )
        assert list(result.keys()) == ["temp_distance"]
        assert result["temp_distance"] == [pytest.approx(3.0)]

    def test_unknown_metric_raises(self, thermostat_spec: GDSSpec) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            trajectory_distances(thermostat_spec, [{}], metric_name="nonexistent")

    def test_no_distance_callable_raises(self, thermostat_spec: GDSSpec) -> None:
        thermostat_spec.register_state_metric(
            StateMetric(
                name="structural_only",
                variables=[("Room", "temperature")],
                metric_type="euclidean",
                distance=None,
            )
        )
        with pytest.raises(ValueError, match="no distance callable"):
            trajectory_distances(thermostat_spec, [{}], metric_name="structural_only")

    def test_empty_trajectory(self, thermostat_spec: GDSSpec) -> None:
        result = trajectory_distances(thermostat_spec, [{"Room.temperature": 0.0}])
        assert result["temp_distance"] == []

    def test_skips_metrics_without_distance(self, thermostat_spec: GDSSpec) -> None:
        thermostat_spec.register_state_metric(
            StateMetric(
                name="no_fn",
                variables=[("Room", "temperature")],
                distance=None,
            )
        )
        trajectory = [
            {"Room.temperature": 0.0},
            {"Room.temperature": 1.0},
        ]
        result = trajectory_distances(thermostat_spec, trajectory)
        assert "temp_distance" in result
        assert "no_fn" not in result

    def test_integration_with_simulation(self, thermostat_spec: GDSSpec) -> None:
        """End-to-end: spec -> model -> simulate -> measure distances."""
        from gds_sim import Simulation

        from gds_analysis.adapter import spec_to_model

        def sensor_policy(state, params, **kw):
            return {"temperature": state.get("Room.temperature", 20.0)}

        def controller_policy(state, params, **kw):
            temp = state.get("Room.temperature", 20.0)
            return {"command": (22.0 - temp) * 0.5}

        def heater_suf(state, params, *, signal=None, **kw):
            signal = signal or {}
            temp = state.get("Room.temperature", 20.0)
            return "Room.temperature", temp + signal.get("command", 0) * 0.1

        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": sensor_policy,
                "Controller": controller_policy,
            },
            sufs={"Heater": heater_suf},
            initial_state={"Room.temperature": 18.0},
            params={"setpoint": [22.0]},
        )
        sim = Simulation(model=model, timesteps=20, runs=1)
        results = sim.run()
        trajectory = results.to_list()

        distances = trajectory_distances(thermostat_spec, trajectory)
        assert "temp_distance" in distances
        assert len(distances["temp_distance"]) == len(trajectory) - 1
        assert all(d >= 0 for d in distances["temp_distance"])

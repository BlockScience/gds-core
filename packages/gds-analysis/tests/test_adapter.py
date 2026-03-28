"""Tests for the GDSSpec -> gds_sim.Model adapter."""

import pytest
from gds import GDSSpec
from gds_sim import Model

from gds_analysis.adapter import spec_to_model


def _sensor_policy(state, params, **kw):
    return {"temperature": state.get("Room.temperature", 20.0)}


def _controller_policy(state, params, **kw):
    temp = state.get("Room.temperature", 20.0)
    setpoint = params.get("setpoint", 22.0)
    return {"command": (setpoint - temp) * params.get("gain", 0.5)}


def _heater_suf(state, params, *, signal=None, **kw):
    signal = signal or {}
    command = signal.get("command", 0.0)
    temp = state.get("Room.temperature", 20.0)
    return "Room.temperature", temp + command * 0.1


class TestSpecToModel:
    def test_returns_model(self, thermostat_spec: GDSSpec) -> None:
        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 18.0},
        )
        assert isinstance(model, Model)

    def test_missing_policy_raises(self, thermostat_spec: GDSSpec) -> None:
        with pytest.raises(ValueError, match=r"Missing policy.*Sensor"):
            spec_to_model(
                thermostat_spec,
                policies={"Controller": _controller_policy},
                sufs={"Heater": _heater_suf},
            )

    def test_missing_suf_raises(self, thermostat_spec: GDSSpec) -> None:
        with pytest.raises(ValueError, match=r"Missing state update.*Heater"):
            spec_to_model(
                thermostat_spec,
                policies={
                    "Sensor": _sensor_policy,
                    "Controller": _controller_policy,
                },
                sufs={},
            )

    def test_default_initial_state(self, thermostat_spec: GDSSpec) -> None:
        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
        )
        assert "Room.temperature" in model.initial_state
        assert model.initial_state["Room.temperature"] == 0.0

    def test_runs_simulation(self, thermostat_spec: GDSSpec) -> None:
        from gds_sim import Simulation

        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 18.0},
            params={"setpoint": [22.0], "gain": [0.5]},
        )
        sim = Simulation(model=model, timesteps=10, runs=1)
        results = sim.run()
        rows = results.to_list()
        assert len(rows) > 0
        last = rows[-1]
        assert last["Room.temperature"] > 18.0

    def test_constraint_enforcement(self, thermostat_spec: GDSSpec) -> None:
        """Constraint guard allows valid signals through."""
        from gds_sim import Simulation

        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 20.0},
            params={"setpoint": [22.0], "gain": [0.5]},
            enforce_constraints=True,
        )
        sim = Simulation(model=model, timesteps=5, runs=1)
        results = sim.run()
        assert len(results) > 0

    def test_no_constraints(self, thermostat_spec: GDSSpec) -> None:
        """Works with enforce_constraints=False."""
        model = spec_to_model(
            thermostat_spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 20.0},
            enforce_constraints=False,
        )
        assert isinstance(model, Model)

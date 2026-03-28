"""Tests for reachable set and configuration space computation."""

from gds import GDSSpec

from gds_analysis.adapter import spec_to_model
from gds_analysis.reachability import (
    configuration_space,
    reachable_graph,
    reachable_set,
)


def _sensor_policy(state, params, **kw):
    return {"temperature": state.get("Room.temperature", 20.0)}


def _controller_policy(state, params, **kw):
    temp = state.get("Room.temperature", 20.0)
    return {"command": (22.0 - temp) * 0.5}


def _heater_suf(state, params, *, signal=None, **kw):
    signal = signal or {}
    temp = state.get("Room.temperature", 20.0)
    command = signal.get("command", 0.0)
    return "Room.temperature", temp + command * 0.1


class TestReachableSet:
    def _make_model(self, spec: GDSSpec):
        return spec_to_model(
            spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 20.0},
            enforce_constraints=False,
        )

    def test_single_input(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        state = {"Room.temperature": 20.0}
        samples = [{"command": 1.0}]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
        ).states
        assert len(reached) == 1
        assert reached[0]["Room.temperature"] != 20.0

    def test_multiple_inputs_distinct(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        state = {"Room.temperature": 20.0}
        samples = [
            {"command": 0.0},
            {"command": 1.0},
            {"command": 2.0},
        ]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
        ).states
        assert len(reached) == 3

    def test_duplicate_inputs_deduplicated(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        state = {"Room.temperature": 20.0}
        samples = [
            {"command": 1.0},
            {"command": 1.0},
        ]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
        ).states
        assert len(reached) == 1

    def test_empty_inputs(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        reached = reachable_set(
            model,
            {"Room.temperature": 20.0},
            input_samples=[],
        ).states
        assert reached == []

    def test_result_metadata(self, thermostat_spec: GDSSpec) -> None:
        """ReachabilityResult carries coverage metadata."""
        model = self._make_model(thermostat_spec)
        state = {"Room.temperature": 20.0}
        samples = [{"command": 0.0}, {"command": 1.0}, {"command": 1.0}]
        result = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
        )
        assert result.n_samples == 3
        assert result.n_distinct == 2  # duplicate deduped
        assert len(result.states) == 2
        assert result.is_exhaustive is False

    def test_exhaustive_flag(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        result = reachable_set(
            model,
            {"Room.temperature": 20.0},
            input_samples=[{"command": 1.0}],
            exhaustive=True,
        )
        assert result.is_exhaustive is True

    def test_float_tolerance(self, thermostat_spec: GDSSpec) -> None:
        """Float tolerance collapses near-identical states."""
        model = self._make_model(thermostat_spec)
        state = {"Room.temperature": 20.0}
        # These produce slightly different floats
        samples = [
            {"command": 1.0000001},
            {"command": 1.0000002},
        ]
        # Without tolerance: may produce 2 distinct states
        r1 = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
        )
        # With tolerance=4: rounds to 4 decimal places, should collapse
        r2 = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Room.temperature",
            float_tolerance=4,
        )
        assert r2.n_distinct <= r1.n_distinct


class TestReachableGraph:
    def _make_model(self, spec: GDSSpec):
        return spec_to_model(
            spec,
            policies={
                "Sensor": _sensor_policy,
                "Controller": _controller_policy,
            },
            sufs={"Heater": _heater_suf},
            initial_state={"Room.temperature": 20.0},
            enforce_constraints=False,
        )

    def test_depth_1(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        graph = reachable_graph(
            model,
            [{"Room.temperature": 20.0}],
            input_samples=[{"command": 1.0}, {"command": -1.0}],
            max_depth=1,
            state_key="Room.temperature",
        )
        assert len(graph) >= 1

    def test_depth_2_expands(self, thermostat_spec: GDSSpec) -> None:
        model = self._make_model(thermostat_spec)
        graph_1 = reachable_graph(
            model,
            [{"Room.temperature": 20.0}],
            input_samples=[{"command": 1.0}],
            max_depth=1,
            state_key="Room.temperature",
        )
        graph_2 = reachable_graph(
            model,
            [{"Room.temperature": 20.0}],
            input_samples=[{"command": 1.0}],
            max_depth=2,
            state_key="Room.temperature",
        )
        assert len(graph_2) >= len(graph_1)


class TestConfigurationSpace:
    def test_single_node_scc(self) -> None:
        graph = {("a",): [("a",)]}
        sccs = configuration_space(graph)
        assert len(sccs) == 1
        assert ("a",) in sccs[0]

    def test_two_node_cycle(self) -> None:
        graph = {
            ("a",): [("b",)],
            ("b",): [("a",)],
        }
        sccs = configuration_space(graph)
        assert len(sccs) == 1
        assert sccs[0] == {("a",), ("b",)}

    def test_disconnected_components(self) -> None:
        graph = {
            ("a",): [("b",)],
            ("b",): [("a",)],
            ("c",): [("d",)],
            ("d",): [],
        }
        sccs = configuration_space(graph)
        # Largest SCC first
        assert sccs[0] == {("a",), ("b",)}
        assert len(sccs) >= 2

    def test_dag_no_cycles(self) -> None:
        graph = {
            ("a",): [("b",)],
            ("b",): [("c",)],
            ("c",): [],
        }
        sccs = configuration_space(graph)
        # Each node is its own SCC (no cycles)
        assert all(len(scc) == 1 for scc in sccs)

    def test_integration(self, thermostat_spec: GDSSpec) -> None:
        """End-to-end: spec -> model -> reachability graph -> SCCs."""
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
        graph = reachable_graph(
            model,
            [{"Room.temperature": 20.0}],
            input_samples=[
                {"command": 0.5},
                {"command": -0.5},
            ],
            max_depth=3,
            state_key="Room.temperature",
        )
        sccs = configuration_space(graph)
        assert len(sccs) >= 1

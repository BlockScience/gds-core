"""ODEModel, ODESimulation, and ODEExperiment configuration objects."""

from __future__ import annotations

import itertools
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_continuous.types import (  # noqa: TC001
    EventFunction,
    ODEFunction,
    OutputFunction,
    Params,
    Solver,
)


class ODEModel(BaseModel):
    """A continuous-time ODE model: state names, initial conditions, RHS function.

    The ``rhs`` callable has signature ``(t, y, params) -> dy/dt`` where
    ``y`` is a list of floats ordered by ``state_names``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state_names: list[str]
    initial_state: dict[str, float]
    rhs: ODEFunction
    output_fn: OutputFunction | None = None
    output_names: list[str] = []
    params: dict[str, list[Any]] = {}
    events: list[EventFunction] = []

    # Computed at validation time
    _param_subsets: list[Params]
    _state_order: list[str]

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        # 1. Cache state ordering
        self._state_order = list(self.state_names)

        # 2. Verify initial_state keys match state_names
        state_set = set(self.state_names)
        initial_set = set(self.initial_state.keys())
        missing = state_set - initial_set
        if missing:
            msg = (
                f"initial_state is missing keys: {sorted(missing)}. "
                f"Expected keys matching state_names: {self.state_names}"
            )
            raise ValueError(msg)
        extra = initial_set - state_set
        if extra:
            msg = f"initial_state has extra keys not in state_names: {sorted(extra)}"
            raise ValueError(msg)

        # 3. Verify output_names if output_fn provided
        if self.output_fn is not None and not self.output_names:
            msg = "output_names must be provided when output_fn is set"
            raise ValueError(msg)

        # 4. Expand parameter sweep (cartesian product)
        if self.params:
            keys = list(self.params.keys())
            values = [self.params[k] for k in keys]
            self._param_subsets = [
                dict(zip(keys, combo, strict=True))
                for combo in itertools.product(*values)
            ]
        else:
            self._param_subsets = [{}]

        return self

    def y0(self) -> list[float]:
        """Initial state as an ordered list of floats."""
        return [self.initial_state[k] for k in self._state_order]


class ODESimulation(BaseModel):
    """A runnable ODE simulation: model + time span + solver config."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: ODEModel
    t_span: tuple[float, float]
    t_eval: list[float] | None = None
    solver: Solver = "RK45"
    rtol: float = 1e-6
    atol: float = 1e-9
    max_step: float = float("inf")
    runs: int = 1

    def run(self) -> Any:
        """Integrate and return ODEResults."""
        from gds_continuous.engine import integrate_simulation

        return integrate_simulation(self)


class ODEExperiment(BaseModel):
    """A collection of ODE simulations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    simulations: list[ODESimulation]

    def run(self) -> Any:
        """Execute all simulations and return merged ODEResults."""
        from gds_continuous.engine import integrate_experiment

        return integrate_experiment(self)

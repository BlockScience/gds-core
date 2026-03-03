"""Model, Simulation, and Experiment configuration objects."""

from __future__ import annotations

import itertools
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_sim.compat import adapt_policy, adapt_suf
from gds_sim.types import (
    Hooks,
    Params,
    StateUpdateBlock,
)


class Model(BaseModel):
    """A simulation model: initial state, update blocks, and parameter space."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    initial_state: dict[str, Any]
    state_update_blocks: list[StateUpdateBlock]
    params: dict[str, list[Any]] = {}

    # Computed at validation time — not part of the public schema
    _param_subsets: list[Params]
    _state_keys: list[str]

    @model_validator(mode="before")
    @classmethod
    def _coerce_blocks(cls, data: Any) -> Any:
        """Allow passing plain dicts instead of StateUpdateBlock instances."""
        if isinstance(data, dict) and "state_update_blocks" in data:
            blocks = data["state_update_blocks"]
            data["state_update_blocks"] = [
                StateUpdateBlock(**b) if isinstance(b, dict) else b for b in blocks
            ]
        return data

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        # 1. Cache state keys
        self._state_keys = list(self.initial_state.keys())
        state_key_set = set(self._state_keys)

        # 2. Verify all SUF keys exist in initial_state
        for i, block in enumerate(self.state_update_blocks):
            for var_key in block.variables:
                if var_key not in state_key_set:
                    msg = (
                        f"State update block {i} references variable "
                        f"'{var_key}' not found in initial_state. "
                        f"Available keys: {self._state_keys}"
                    )
                    raise ValueError(msg)

        # 3. Adapt cadCAD-style function signatures
        adapted_blocks: list[StateUpdateBlock] = []
        for block in self.state_update_blocks:
            new_policies = {k: adapt_policy(fn) for k, fn in block.policies.items()}
            new_variables = {k: adapt_suf(fn) for k, fn in block.variables.items()}
            adapted_blocks.append(
                StateUpdateBlock(policies=new_policies, variables=new_variables)
            )
        self.state_update_blocks = adapted_blocks

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


class Simulation(BaseModel):
    """A runnable simulation: model + execution parameters."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Model
    timesteps: int = 100
    runs: int = 1
    history: int | Literal["full"] | None = None
    hooks: Hooks = Hooks()

    def run(self) -> Any:
        """Execute this simulation and return Results."""
        from gds_sim.engine import execute_simulation

        return execute_simulation(self)


class Experiment(BaseModel):
    """A collection of simulations, optionally run in parallel."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    simulations: list[Simulation]
    processes: int | None = None

    def run(self) -> Any:
        """Execute all simulations and return merged Results."""
        from gds_sim.parallel import execute_experiment

        return execute_experiment(self)

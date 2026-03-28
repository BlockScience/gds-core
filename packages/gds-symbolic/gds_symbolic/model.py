"""SymbolicControlModel — extends ControlModel with symbolic ODEs."""

from __future__ import annotations

from typing import Any, Self

from gds_control.dsl.model import ControlModel
from pydantic import model_validator

from gds_symbolic.elements import OutputEquation, StateEquation  # noqa: TC001
from gds_symbolic.errors import SymbolicError


class SymbolicControlModel(ControlModel):
    """ControlModel extended with symbolic differential equations.

    Preserves all structural GDS semantics from ControlModel.
    Adds symbolic ODEs as an annotation layer — they do not affect
    ``compile()`` or ``compile_system()`` (those remain structural).

    The ODEs are behavioral (R3) and compile to plain Python callables
    via ``to_ode_function()``.
    """

    state_equations: list[StateEquation] = []  # noqa: RUF012
    output_equations: list[OutputEquation] = []  # noqa: RUF012
    symbolic_params: list[str] = []  # noqa: RUF012

    @model_validator(mode="after")
    def _validate_symbolic_structure(self) -> Self:
        state_names = {s.name for s in self.states}
        sensor_names = {s.name for s in self.sensors}
        input_names = {i.name for i in self.inputs}

        errors: list[str] = []

        # Every state_equation must reference a declared state
        for eq in self.state_equations:
            if eq.state_name not in state_names:
                errors.append(
                    f"StateEquation references undeclared state '{eq.state_name}'"
                )

        # No duplicate state equations
        eq_states = [eq.state_name for eq in self.state_equations]
        dupes = {s for s in eq_states if eq_states.count(s) > 1}
        if dupes:
            errors.append(f"Duplicate state equations for: {sorted(dupes)}")

        # Every output_equation must reference a declared sensor
        for eq in self.output_equations:
            if eq.sensor_name not in sensor_names:
                errors.append(
                    f"OutputEquation references undeclared sensor '{eq.sensor_name}'"
                )

        # Symbolic params should not collide with state/input names
        reserved = state_names | input_names
        for p in self.symbolic_params:
            if p in reserved:
                errors.append(
                    f"Symbolic param '{p}' conflicts with a state or input name"
                )

        if errors:
            raise SymbolicError(
                "Symbolic model validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return self

    def to_ode_function(
        self,
    ) -> tuple[Any, list[str]]:
        """Compile symbolic ODEs to a plain Python callable.

        Returns
        -------
        ode_fn : ODEFunction
            Signature: ``(t, y, params) -> dy/dt``
        state_order : list[str]
            State variable names in vector order.
        """
        from gds_symbolic.compile import compile_to_ode

        return compile_to_ode(self)

    def linearize(
        self,
        x0: list[float],
        u0: list[float],
        param_values: dict[str, float] | None = None,
    ) -> Any:
        """Linearize around an operating point.

        Returns a ``LinearizedSystem`` with A, B, C, D matrices.
        """
        from gds_symbolic.linearize import linearize

        return linearize(self, x0, u0, param_values)

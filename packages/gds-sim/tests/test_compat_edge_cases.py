"""Tests for _positional_count edge cases and compat adaptation edge cases."""

from __future__ import annotations

import functools
from typing import Any

from gds_sim.compat import _positional_count, adapt_policy, adapt_suf

# -- _positional_count edge cases ------------------------------------------


class TestPositionalCountEdgeCases:
    def test_lambda_no_args(self) -> None:
        assert _positional_count(lambda: None) == 0

    def test_lambda_one_arg(self) -> None:
        assert _positional_count(lambda x: x) == 1

    def test_lambda_two_args(self) -> None:
        assert _positional_count(lambda x, y: x + y) == 2

    def test_lambda_with_kwargs_not_counted(self) -> None:
        """**kw should not count as positional."""
        assert _positional_count(lambda x, y, **kw: x) == 2

    def test_lambda_with_default_still_counted(self) -> None:
        """Args with defaults are still POSITIONAL_OR_KEYWORD."""
        assert _positional_count(lambda x, y=1: x) == 2

    def test_builtin_returns_zero(self) -> None:
        """Built-in functions cannot be inspected -- should return 0, not crash."""
        assert _positional_count(len) >= 0  # builtins may or may not be inspectable

    def test_partial_reduces_count(self) -> None:
        """functools.partial with one positional arg bound."""

        def f(a: int, b: int, c: int) -> int:
            return a + b + c

        p = functools.partial(f, 1)
        assert _positional_count(p) == 2  # b, c remain

    def test_partial_all_bound(self) -> None:
        def f(a: int, b: int) -> int:
            return a + b

        p = functools.partial(f, 1, 2)
        assert _positional_count(p) == 0

    def test_class_callable(self) -> None:
        """A class with __call__ -- inspect.signature strips self for instances."""

        class Adder:
            def __call__(self, x: int, y: int) -> int:
                return x + y

        assert _positional_count(Adder()) == 2

    def test_keyword_only_not_counted(self) -> None:
        """Keyword-only params (after *) should not be counted."""

        def f(a: int, *, b: int, c: int) -> int:
            return a + b + c

        assert _positional_count(f) == 1

    def test_none_returns_zero(self) -> None:
        """Non-callable should return 0, not crash."""
        assert _positional_count(None) == 0  # type: ignore[arg-type]

    def test_string_returns_zero(self) -> None:
        """Non-callable should return 0, not crash."""
        assert _positional_count("not a function") == 0  # type: ignore[arg-type]

    def test_var_positional_not_counted(self) -> None:
        """*args should not add to the positional count."""

        def f(a: int, *args: int) -> int:
            return a + sum(args)

        assert _positional_count(f) == 1


# -- adapt_policy edge cases -----------------------------------------------


class TestAdaptPolicyEdgeCases:
    def test_three_arg_passes_through(self) -> None:
        """Non-4-arg functions should pass through unchanged."""

        def three_arg(a: Any, b: Any, c: Any) -> dict[str, Any]:
            return {"x": 1}

        adapted = adapt_policy(three_arg)
        assert adapted is three_arg

    def test_one_arg_passes_through(self) -> None:
        def one_arg(state: Any) -> dict[str, Any]:
            return {}

        adapted = adapt_policy(one_arg)
        assert adapted is one_arg

    def test_zero_arg_passes_through(self) -> None:
        def zero_arg() -> dict[str, Any]:
            return {}

        adapted = adapt_policy(zero_arg)
        assert adapted is zero_arg

    def test_cadcad_policy_forwards_substep_kwarg(self) -> None:
        """Wrapped cadCAD policy should forward substep from **kw."""
        received: dict[str, Any] = {}

        def cadcad_policy(
            params: Any, substep: int, history: list[Any], state: Any
        ) -> dict[str, Any]:
            received["substep"] = substep
            received["state"] = state
            received["params"] = params
            return {}

        adapted = adapt_policy(cadcad_policy)
        adapted({"x": 1}, {"rate": 2}, substep=7, timestep=3)
        assert received["substep"] == 7
        assert received["state"] == {"x": 1}
        assert received["params"] == {"rate": 2}

    def test_cadcad_policy_default_substep_zero(self) -> None:
        """If substep not in kw, defaults to 0."""
        received: dict[str, Any] = {}

        def cadcad_policy(
            params: Any, substep: int, history: list[Any], state: Any
        ) -> dict[str, Any]:
            received["substep"] = substep
            return {}

        adapted = adapt_policy(cadcad_policy)
        adapted({"x": 1}, {}, timestep=1)
        assert received["substep"] == 0

    def test_cadcad_policy_receives_empty_history(self) -> None:
        """Wrapped cadCAD policy always gets [] for state_history."""
        received_history: list[Any] = [None]  # sentinel

        def cadcad_policy(
            params: Any, substep: int, history: list[Any], state: Any
        ) -> dict[str, Any]:
            received_history[0] = history
            return {}

        adapted = adapt_policy(cadcad_policy)
        adapted({}, {})
        assert received_history[0] == []


# -- adapt_suf edge cases --------------------------------------------------


class TestAdaptSufEdgeCases:
    def test_three_arg_passes_through(self) -> None:
        def three_arg(a: Any, b: Any, c: Any) -> tuple[str, Any]:
            return "x", 1

        adapted = adapt_suf(three_arg)
        assert adapted is three_arg

    def test_cadcad_suf_forwards_substep_kwarg(self) -> None:
        received: dict[str, Any] = {}

        def cadcad_suf(
            params: Any,
            substep: int,
            history: list[Any],
            state: Any,
            policy_input: Any,
        ) -> tuple[str, Any]:
            received["substep"] = substep
            received["policy_input"] = policy_input
            return "x", 1

        adapted = adapt_suf(cadcad_suf)
        adapted({"x": 0}, {}, signal={"delta": 5}, substep=3)
        assert received["substep"] == 3
        assert received["policy_input"] == {"delta": 5}

    def test_cadcad_suf_none_signal_becomes_empty_dict(self) -> None:
        """When signal is None, cadCAD wrapper should pass {} as policy_input."""
        received: dict[str, Any] = {}

        def cadcad_suf(
            params: Any,
            substep: int,
            history: list[Any],
            state: Any,
            policy_input: Any,
        ) -> tuple[str, Any]:
            received["policy_input"] = policy_input
            return "x", 1

        adapted = adapt_suf(cadcad_suf)
        adapted({"x": 0}, {}, signal=None)
        assert received["policy_input"] == {}

    def test_cadcad_suf_default_substep_zero(self) -> None:
        received: dict[str, Any] = {}

        def cadcad_suf(
            params: Any,
            substep: int,
            history: list[Any],
            state: Any,
            policy_input: Any,
        ) -> tuple[str, Any]:
            received["substep"] = substep
            return "x", 1

        adapted = adapt_suf(cadcad_suf)
        adapted({"x": 0}, {})
        assert received["substep"] == 0

    def test_cadcad_suf_receives_empty_history(self) -> None:
        received_history: list[Any] = [None]

        def cadcad_suf(
            params: Any,
            substep: int,
            history: list[Any],
            state: Any,
            policy_input: Any,
        ) -> tuple[str, Any]:
            received_history[0] = history
            return "x", 1

        adapted = adapt_suf(cadcad_suf)
        adapted({"x": 0}, {})
        assert received_history[0] == []

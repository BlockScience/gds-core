"""Columnar result storage for continuous-time ODE trajectories."""

from __future__ import annotations

from typing import Any

# Metadata column names
_META_COLS = ("time", "run", "subset")


class ODEResults:
    """Columnar dict-of-lists result storage for ODE trajectories.

    Mirrors ``gds_sim.Results`` in interface but uses continuous
    ``time`` (float) instead of discrete ``timestep``/``substep``.
    """

    __slots__ = ("_capacity", "_columns", "_output_names", "_size", "_state_names")

    def __init__(
        self,
        state_names: list[str],
        output_names: list[str] | None = None,
        capacity: int = 0,
    ) -> None:
        self._state_names = state_names
        self._output_names = output_names or []
        self._size = 0
        self._capacity = capacity

        all_keys = list(_META_COLS) + state_names + self._output_names
        if capacity > 0:
            self._columns: dict[str, list[Any]] = {
                k: [None] * capacity for k in all_keys
            }
        else:
            self._columns = {k: [] for k in all_keys}

    # ------------------------------------------------------------------
    # Append
    # ------------------------------------------------------------------

    def append(
        self,
        time: float,
        state: list[float],
        *,
        run: int = 0,
        subset: int = 0,
        outputs: list[float] | None = None,
    ) -> None:
        """Append a single time point."""
        cols = self._columns
        idx = self._size

        if self._capacity > 0 and idx < self._capacity:
            cols["time"][idx] = time
            cols["run"][idx] = run
            cols["subset"][idx] = subset
            for i, name in enumerate(self._state_names):
                cols[name][idx] = state[i]
            if outputs:
                for i, name in enumerate(self._output_names):
                    cols[name][idx] = outputs[i]
        else:
            cols["time"].append(time)
            cols["run"].append(run)
            cols["subset"].append(subset)
            for i, name in enumerate(self._state_names):
                cols[name].append(state[i])
            if outputs:
                for i, name in enumerate(self._output_names):
                    cols[name].append(outputs[i])

        self._size += 1

    def append_solution(
        self,
        t_array: Any,
        y_array: Any,
        *,
        run: int = 0,
        subset: int = 0,
    ) -> None:
        """Append an entire scipy solve_ivp solution.

        Parameters
        ----------
        t_array : array-like of shape (n_points,)
        y_array : array-like of shape (n_states, n_points)
        """
        n_points = len(t_array)
        for j in range(n_points):
            state = [float(y_array[i][j]) for i in range(len(self._state_names))]
            self.append(float(t_array[j]), state, run=run, subset=subset)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_dataframe(self) -> Any:
        """Convert to pandas DataFrame. Requires ``pandas`` installed."""
        try:
            import pandas as pd  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: uv add gds-continuous[pandas]"
            ) from exc

        data = self._trimmed_columns()
        return pd.DataFrame(data)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of row-dicts."""
        data = self._trimmed_columns()
        keys = list(data.keys())
        n = self._size
        return [{k: data[k][i] for k in keys} for i in range(n)]

    def _trimmed_columns(self) -> dict[str, list[Any]]:
        """Return columns trimmed to actual size."""
        if self._capacity > 0 and self._size < self._capacity:
            return {k: v[: self._size] for k, v in self._columns.items()}
        return self._columns

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def state_names(self) -> list[str]:
        """Ordered state variable names."""
        return list(self._state_names)

    @property
    def times(self) -> list[float]:
        """Time values (trimmed to actual size)."""
        return self._trimmed_columns()["time"]

    def state_array(self, name: str) -> list[float]:
        """Get all values for a single state variable."""
        return self._trimmed_columns()[name]

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    @classmethod
    def merge(cls, results_list: list[ODEResults]) -> ODEResults:
        """Merge multiple ODEResults into one."""
        if not results_list:
            return cls([])
        if len(results_list) == 1:
            return results_list[0]

        state_names = results_list[0]._state_names
        output_names = results_list[0]._output_names
        total = sum(r._size for r in results_list)
        merged = cls(state_names, output_names, capacity=total)

        all_keys = list(_META_COLS) + state_names + output_names
        offset = 0
        for r in results_list:
            trimmed = r._trimmed_columns()
            n = r._size
            for k in all_keys:
                merged._columns[k][offset : offset + n] = trimmed[k]
            offset += n

        merged._size = total
        return merged

    def __len__(self) -> int:
        return self._size

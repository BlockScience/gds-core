"""Columnar result storage with optional DataFrame conversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds_sim.model import Simulation

# Metadata column names
_META_COLS = ("timestep", "substep", "run", "subset")


class Results:
    """Columnar dict-of-lists result storage.

    Pre-allocates capacity when the total row count is known,
    then fills via ``append()``. Converts to pandas DataFrame
    or list-of-dicts on demand.
    """

    __slots__ = ("_capacity", "_columns", "_size", "_state_keys")

    def __init__(self, state_keys: list[str], capacity: int = 0) -> None:
        self._state_keys = state_keys
        self._size = 0
        self._capacity = capacity

        # Build column storage: metadata + state variables
        self._columns: dict[str, list[Any]] = {}
        all_keys = list(_META_COLS) + state_keys
        if capacity > 0:
            for k in all_keys:
                self._columns[k] = [None] * capacity
        else:
            for k in all_keys:
                self._columns[k] = []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def preallocate(cls, sim: Simulation) -> Results:
        """Create a Results instance pre-allocated for the given simulation."""
        n_subsets = len(sim.model._param_subsets)
        n_blocks = len(sim.model.state_update_blocks)
        # Row 0 (initial state) + timesteps * substeps, per run per subset
        rows_per_run = 1 + sim.timesteps * max(n_blocks, 1)
        capacity = rows_per_run * sim.runs * n_subsets
        return cls(list(sim.model._state_keys), capacity)

    # ------------------------------------------------------------------
    # Append
    # ------------------------------------------------------------------

    def append(
        self,
        state: dict[str, Any],
        *,
        timestep: int,
        substep: int,
        run: int,
        subset: int,
    ) -> None:
        """Append a single row (state snapshot + metadata)."""
        cols = self._columns
        idx = self._size

        if self._capacity > 0 and idx < self._capacity:
            # Fast path: fill pre-allocated slots
            cols["timestep"][idx] = timestep
            cols["substep"][idx] = substep
            cols["run"][idx] = run
            cols["subset"][idx] = subset
            for k in self._state_keys:
                cols[k][idx] = state[k]
        else:
            # Fallback: dynamic append
            cols["timestep"].append(timestep)
            cols["substep"].append(substep)
            cols["run"].append(run)
            cols["subset"].append(subset)
            for k in self._state_keys:
                cols[k].append(state[k])

        self._size += 1

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
                "Install with: pip install gds-sim[pandas]"
            ) from exc

        data = self._trimmed_columns()
        return pd.DataFrame(data)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of row-dicts (cadCAD-compatible format)."""
        data = self._trimmed_columns()
        keys = list(data.keys())
        n = self._size
        return [{k: data[k][i] for k in keys} for i in range(n)]

    def _trimmed_columns(self) -> dict[str, list[Any]]:
        """Return columns trimmed to actual size (handles pre-allocation)."""
        if self._capacity > 0 and self._size < self._capacity:
            return {k: v[: self._size] for k, v in self._columns.items()}
        return self._columns

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    @classmethod
    def merge(cls, results_list: list[Results]) -> Results:
        """Merge multiple Results into one."""
        if not results_list:
            return cls([])
        if len(results_list) == 1:
            return results_list[0]

        state_keys = results_list[0]._state_keys
        total = sum(r._size for r in results_list)
        merged = cls(state_keys, capacity=total)

        all_keys = list(_META_COLS) + state_keys
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

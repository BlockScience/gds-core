"""Dependency analysis and query engine for GDSSpec.

SpecQuery replaces MSML's parameter crawling, exploded parameter links,
and ad-hoc traversal methods with a clean query API.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from gds.blocks.roles import HasParams, Mechanism

if TYPE_CHECKING:
    from gds.spec import GDSSpec


class SpecQuery:
    """Query engine for exploring GDSSpec structure."""

    def __init__(self, spec: GDSSpec) -> None:
        self.spec = spec

    def param_to_blocks(self) -> dict[str, list[str]]:
        """Map each parameter to the blocks that use it."""
        mapping: dict[str, list[str]] = {p: [] for p in self.spec.parameters}
        for bname, block in self.spec.blocks.items():
            if isinstance(block, HasParams):
                for param in block.params_used:
                    if param in mapping:
                        mapping[param].append(bname)
        return mapping

    def block_to_params(self) -> dict[str, list[str]]:
        """Map each block to the parameters it uses."""
        result: dict[str, list[str]] = {}
        for bname, block in self.spec.blocks.items():
            if isinstance(block, HasParams):
                result[bname] = list(block.params_used)
            else:
                result[bname] = []
        return result

    def entity_update_map(self) -> dict[str, dict[str, list[str]]]:
        """Map entity -> variable -> list of mechanisms that update it."""
        result: dict[str, dict[str, list[str]]] = {}
        for ename, entity in self.spec.entities.items():
            result[ename] = {vname: [] for vname in entity.variables}

        for bname, block in self.spec.blocks.items():
            if isinstance(block, Mechanism):
                for ename, vname in block.updates:
                    if ename in result and vname in result[ename]:
                        result[ename][vname].append(bname)
        return result

    def dependency_graph(self) -> dict[str, set[str]]:
        """Full block dependency DAG (who feeds whom) from all wirings."""
        adj: dict[str, set[str]] = defaultdict(set)
        for wiring in self.spec.wirings.values():
            for wire in wiring.wires:
                adj[wire.source].add(wire.target)
        return dict(adj)

    def blocks_by_kind(self) -> dict[str, list[str]]:
        """Group blocks by their GDS role (kind)."""
        result: dict[str, list[str]] = {
            "boundary": [],
            "control": [],
            "policy": [],
            "mechanism": [],
            "generic": [],
        }
        for bname, block in self.spec.blocks.items():
            kind = getattr(block, "kind", "generic")
            if kind in result:
                result[kind].append(bname)
            else:
                result[kind] = [bname]
        return result

    def blocks_affecting(self, entity: str, variable: str) -> list[str]:
        """Which blocks can transitively affect this variable?

        Finds all mechanisms that directly update the variable, then
        all blocks that can transitively reach those mechanisms.
        """
        direct: list[str] = []
        for bname, block in self.spec.blocks.items():
            if isinstance(block, Mechanism) and (entity, variable) in block.updates:
                direct.append(bname)

        adj: dict[str, set[str]] = defaultdict(set)
        for wiring in self.spec.wirings.values():
            for wire in wiring.wires:
                adj[wire.source].add(wire.target)

        all_affecting: set[str] = set(direct)
        for mech_name in direct:
            for bname in self.spec.blocks:
                if self._can_reach(adj, bname, mech_name):
                    all_affecting.add(bname)

        return sorted(all_affecting)

    @staticmethod
    def _can_reach(adj: dict[str, set[str]], source: str, target: str) -> bool:
        """BFS reachability check."""
        if source == target:
            return False
        visited: set[str] = set()
        queue = [source]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(adj.get(current, set()))
        return False

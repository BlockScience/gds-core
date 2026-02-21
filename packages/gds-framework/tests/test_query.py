"""Tests for SpecQuery dependency analysis."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.query import SpecQuery
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef


@pytest.fixture
def query_spec():
    """A spec with enough structure to test all query methods."""
    pop_type = TypeDef(name="Population", python_type=int, constraint=lambda x: x >= 0)
    rate_type = TypeDef(name="Rate", python_type=float, constraint=lambda x: x > 0)

    prey = Entity(
        name="Prey",
        variables={
            "population": StateVariable(
                name="population", typedef=pop_type, symbol="N"
            ),
        },
    )
    predator = Entity(
        name="Predator",
        variables={
            "population": StateVariable(
                name="population", typedef=pop_type, symbol="P"
            ),
        },
    )

    observe = BoundaryAction(
        name="Observe",
        interface=Interface(forward_out=(port("Signal"),)),
        params_used=["birth_rate"],
    )
    hunt = Policy(
        name="Hunt",
        interface=Interface(
            forward_in=(port("Signal"),),
            forward_out=(port("Result"),),
        ),
        params_used=["hunt_efficiency"],
    )
    update_prey = Mechanism(
        name="Update Prey",
        interface=Interface(forward_in=(port("Result"),)),
        updates=[("Prey", "population")],
        params_used=["birth_rate"],
    )
    update_predator = Mechanism(
        name="Update Predator",
        interface=Interface(forward_in=(port("Result"),)),
        updates=[("Predator", "population")],
        params_used=["death_rate"],
    )

    spec = GDSSpec(name="Predator-Prey")
    spec.register_type(pop_type)
    spec.register_type(rate_type)
    spec.register_entity(prey)
    spec.register_entity(predator)
    spec.register_block(observe)
    spec.register_block(hunt)
    spec.register_block(update_prey)
    spec.register_block(update_predator)
    spec.register_parameter("birth_rate", rate_type)
    spec.register_parameter("death_rate", rate_type)
    spec.register_parameter("hunt_efficiency", rate_type)
    spec.register_wiring(
        SpecWiring(
            name="Hunt Cycle",
            block_names=["Observe", "Hunt", "Update Prey", "Update Predator"],
            wires=[
                Wire(source="Observe", target="Hunt"),
                Wire(source="Hunt", target="Update Prey"),
                Wire(source="Hunt", target="Update Predator"),
            ],
        )
    )
    return spec


# ── param_to_blocks ──────────────────────────────────────────


class TestParamMapping:
    def test_param_to_blocks(self, query_spec):
        q = SpecQuery(query_spec)
        mapping = q.param_to_blocks()
        assert "Observe" in mapping["birth_rate"]
        assert "Update Prey" in mapping["birth_rate"]
        assert "Hunt" in mapping["hunt_efficiency"]
        assert "Update Predator" in mapping["death_rate"]

    def test_block_to_params(self, query_spec):
        q = SpecQuery(query_spec)
        mapping = q.block_to_params()
        assert "birth_rate" in mapping["Observe"]
        assert "hunt_efficiency" in mapping["Hunt"]
        assert "birth_rate" in mapping["Update Prey"]

    def test_unused_param(self, query_spec):
        new_rate = TypeDef(name="NewRate", python_type=float)
        query_spec.register_parameter("unused_param", new_rate)
        q = SpecQuery(query_spec)
        mapping = q.param_to_blocks()
        assert mapping["unused_param"] == []


# ── entity_update_map ────────────────────────────────────────


class TestEntityUpdateMap:
    def test_correct_mapping(self, query_spec):
        q = SpecQuery(query_spec)
        update_map = q.entity_update_map()
        assert "Update Prey" in update_map["Prey"]["population"]
        assert "Update Predator" in update_map["Predator"]["population"]

    def test_no_cross_contamination(self, query_spec):
        q = SpecQuery(query_spec)
        update_map = q.entity_update_map()
        assert "Update Predator" not in update_map["Prey"]["population"]
        assert "Update Prey" not in update_map["Predator"]["population"]


# ── dependency_graph ─────────────────────────────────────────


class TestDependencyGraph:
    def test_correct_adjacency(self, query_spec):
        q = SpecQuery(query_spec)
        graph = q.dependency_graph()
        assert "Hunt" in graph["Observe"]
        assert "Update Prey" in graph["Hunt"]
        assert "Update Predator" in graph["Hunt"]

    def test_no_reverse_edges(self, query_spec):
        q = SpecQuery(query_spec)
        graph = q.dependency_graph()
        assert "Observe" not in graph.get("Hunt", set())


# ── blocks_by_kind ───────────────────────────────────────────


class TestBlocksByKind:
    def test_groups_correctly(self, query_spec):
        q = SpecQuery(query_spec)
        by_kind = q.blocks_by_kind()
        assert "Observe" in by_kind["boundary"]
        assert "Hunt" in by_kind["policy"]
        assert "Update Prey" in by_kind["mechanism"]
        assert "Update Predator" in by_kind["mechanism"]

    def test_generic_empty(self, query_spec):
        q = SpecQuery(query_spec)
        by_kind = q.blocks_by_kind()
        assert by_kind["generic"] == []


# ── blocks_affecting ─────────────────────────────────────────


class TestBlocksAffecting:
    def test_direct_mechanism(self, query_spec):
        q = SpecQuery(query_spec)
        affecting = q.blocks_affecting("Prey", "population")
        assert "Update Prey" in affecting

    def test_transitive_blocks(self, query_spec):
        q = SpecQuery(query_spec)
        affecting = q.blocks_affecting("Prey", "population")
        # Observe -> Hunt -> Update Prey, so Observe and Hunt should be included
        assert "Hunt" in affecting
        assert "Observe" in affecting

    def test_unrelated_block_excluded(self, query_spec):
        q = SpecQuery(query_spec)
        affecting = q.blocks_affecting("Prey", "population")
        # Update Predator doesn't affect Prey.population
        assert "Update Predator" not in affecting

    def test_nonexistent_returns_empty(self, query_spec):
        q = SpecQuery(query_spec)
        affecting = q.blocks_affecting("NonExistent", "var")
        assert affecting == []

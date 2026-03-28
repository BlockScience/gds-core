"""Property-based round-trip tests: random GDSSpec -> Turtle -> GDSSpec.

Extends the fixture-based tests in test_roundtrip.py with Hypothesis-generated
random specifications to verify structural fidelity across the full
rho -> RDF -> rho^{-1} transformation.

See: docs/research/verification-plan.md (Phase 3)
     docs/research/formal-representability.md (Remark 2.1)
"""

from hypothesis import given, settings
from rdflib import Graph

from gds import GDSSpec
from gds_owl.export import spec_to_graph
from gds_owl.import_ import graph_to_spec
from gds_owl.serialize import to_turtle
from tests.strategies import gds_specs


def _round_trip(spec: GDSSpec) -> GDSSpec:
    """Export spec to Turtle RDF, parse back, reimport."""
    g = spec_to_graph(spec)
    ttl = to_turtle(g)
    g2 = Graph()
    g2.parse(data=ttl, format="turtle")
    return graph_to_spec(g2)


class TestSpecRoundTripPBT:
    """Property-based round-trip tests for GDSSpec."""

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_name_survives(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert spec2.name == spec.name

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert set(spec2.types.keys()) == set(spec.types.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_python_types_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        for name in spec.types:
            assert spec2.types[name].python_type == spec.types[name].python_type

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_units_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        for name in spec.types:
            assert spec2.types[name].units == spec.types[name].units

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_constraints_are_lossy(self, spec: GDSSpec) -> None:
        """R3 fields: TypeDef.constraint is always None after round-trip."""
        spec2 = _round_trip(spec)
        for td in spec2.types.values():
            assert td.constraint is None

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_space_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert set(spec2.spaces.keys()) == set(spec.spaces.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_space_fields_survive(self, spec: GDSSpec) -> None:
        """Space field names survive (set-based, order independent)."""
        spec2 = _round_trip(spec)
        for name in spec.spaces:
            assert set(spec2.spaces[name].fields.keys()) == set(
                spec.spaces[name].fields.keys()
            )

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_entity_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert set(spec2.entities.keys()) == set(spec.entities.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_entity_variables_survive(self, spec: GDSSpec) -> None:
        """Entity variable names survive (set-based, order independent)."""
        spec2 = _round_trip(spec)
        for name in spec.entities:
            assert set(spec2.entities[name].variables.keys()) == set(
                spec.entities[name].variables.keys()
            )

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_block_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert set(spec2.blocks.keys()) == set(spec.blocks.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_block_roles_survive(self, spec: GDSSpec) -> None:
        """Each block retains its role (kind) after round-trip."""
        spec2 = _round_trip(spec)
        for name in spec.blocks:
            orig_kind = getattr(spec.blocks[name], "kind", "generic")
            new_kind = getattr(spec2.blocks[name], "kind", "generic")
            assert new_kind == orig_kind, f"Block {name}: {orig_kind} -> {new_kind}"

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_mechanism_updates_survive(self, spec: GDSSpec) -> None:
        """Mechanism.updates survive as sets (order independent)."""
        from gds.blocks.roles import Mechanism

        spec2 = _round_trip(spec)
        for name, block in spec.blocks.items():
            if isinstance(block, Mechanism):
                new_block = spec2.blocks[name]
                assert isinstance(new_block, Mechanism)
                assert set(new_block.updates) == set(block.updates)

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_wiring_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        assert set(spec2.wirings.keys()) == set(spec.wirings.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_wiring_wire_count_survives(self, spec: GDSSpec) -> None:
        spec2 = _round_trip(spec)
        for name in spec.wirings:
            assert len(spec2.wirings[name].wires) == len(spec.wirings[name].wires)

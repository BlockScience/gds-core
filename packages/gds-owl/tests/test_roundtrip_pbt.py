"""Property-based round-trip and derived-property tests.

- TestSpecRoundTripPBT: random GDSSpec -> Turtle -> GDSSpec structural fidelity
- TestSHACLConformance: exported RDF passes SHACL validation (separate for perf)
- TestSPARQLConformance: SPARQL queries return expected results (no pyshacl needed)
- TestDerivedPropertyPreservation: SystemIR/Canonical/Report round-trips
- TestStrategyInvariants: structural invariants of generated specs

See: docs/research/verification-plan.md (Phase 3)
     docs/research/formal-representability.md (Remark 2.1)
"""

import importlib.util
import os
from collections import Counter

import pytest
from hypothesis import given, settings
from rdflib import Graph

from gds import CanonicalGDS, GDSSpec, SystemIR, VerificationReport
from gds.blocks.roles import BoundaryAction, Mechanism
from gds_owl.export import (
    canonical_to_graph,
    report_to_graph,
    spec_to_graph,
    system_ir_to_graph,
)
from gds_owl.import_ import (
    graph_to_canonical,
    graph_to_report,
    graph_to_spec,
    graph_to_system_ir,
)
from gds_owl.serialize import to_turtle
from tests.strategies import (
    gds_specs,
    specs_with_canonical,
    specs_with_report,
    system_irs,
)

HAS_PYSHACL = importlib.util.find_spec("pyshacl") is not None

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
settings.register_profile("ci", database=None, derandomize=True, max_examples=100)
settings.register_profile("dev", max_examples=100)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec_round_trip(spec: GDSSpec) -> GDSSpec:
    """Export spec to Turtle RDF, parse back, reimport."""
    g = spec_to_graph(spec)
    ttl = to_turtle(g)
    g2 = Graph()
    g2.parse(data=ttl, format="turtle")
    return graph_to_spec(g2)


def _ir_round_trip(ir: SystemIR) -> SystemIR:
    g = system_ir_to_graph(ir)
    ttl = to_turtle(g)
    g2 = Graph()
    g2.parse(data=ttl, format="turtle")
    return graph_to_system_ir(g2)


def _canonical_round_trip(can: CanonicalGDS) -> CanonicalGDS:
    g = canonical_to_graph(can)
    ttl = to_turtle(g)
    g2 = Graph()
    g2.parse(data=ttl, format="turtle")
    return graph_to_canonical(g2)


def _report_round_trip(report: VerificationReport) -> VerificationReport:
    g = report_to_graph(report)
    ttl = to_turtle(g)
    g2 = Graph()
    g2.parse(data=ttl, format="turtle")
    return graph_to_report(g2)


# ---------------------------------------------------------------------------
# GDSSpec Round-Trip (Phase 3a-b)
# ---------------------------------------------------------------------------


class TestSpecRoundTripPBT:
    """Property-based round-trip tests for GDSSpec."""

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_name_survives(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert spec2.name == spec.name

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert set(spec2.types.keys()) == set(spec.types.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_python_types_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        for name in spec.types:
            assert spec2.types[name].python_type == spec.types[name].python_type

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_type_units_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        for name in spec.types:
            assert spec2.types[name].units == spec.types[name].units

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_space_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert set(spec2.spaces.keys()) == set(spec.spaces.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_space_fields_survive(self, spec: GDSSpec) -> None:
        """Space field names survive (set-based, order independent)."""
        spec2 = _spec_round_trip(spec)
        for name in spec.spaces:
            assert set(spec2.spaces[name].fields.keys()) == set(
                spec.spaces[name].fields.keys()
            )

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_entity_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert set(spec2.entities.keys()) == set(spec.entities.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_entity_variables_survive(self, spec: GDSSpec) -> None:
        """Entity variable names survive (set-based)."""
        spec2 = _spec_round_trip(spec)
        for name in spec.entities:
            assert set(spec2.entities[name].variables.keys()) == set(
                spec.entities[name].variables.keys()
            )

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_block_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert set(spec2.blocks.keys()) == set(spec.blocks.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_block_roles_survive(self, spec: GDSSpec) -> None:
        """Each block retains its role (kind) after round-trip."""
        spec2 = _spec_round_trip(spec)
        for name in spec.blocks:
            orig = getattr(spec.blocks[name], "kind", "generic")
            new = getattr(spec2.blocks[name], "kind", "generic")
            assert new == orig, f"Block {name}: {orig} -> {new}"

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_mechanism_updates_survive(self, spec: GDSSpec) -> None:
        """Mechanism.updates survive as sets (order independent)."""
        spec2 = _spec_round_trip(spec)
        for name, block in spec.blocks.items():
            if isinstance(block, Mechanism):
                new_block = spec2.blocks[name]
                assert isinstance(new_block, Mechanism)
                assert set(new_block.updates) == set(block.updates)

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_wiring_names_survive(self, spec: GDSSpec) -> None:
        spec2 = _spec_round_trip(spec)
        assert set(spec2.wirings.keys()) == set(spec.wirings.keys())

    @given(spec=gds_specs())
    @settings(max_examples=100)
    def test_wire_content_survives(self, spec: GDSSpec) -> None:
        """Wire source, target, and space all survive round-trip."""
        spec2 = _spec_round_trip(spec)
        for name in spec.wirings:
            orig = {(w.source, w.target, w.space) for w in spec.wirings[name].wires}
            new = {(w.source, w.target, w.space) for w in spec2.wirings[name].wires}
            assert orig == new


# ---------------------------------------------------------------------------
# SHACL Conformance Gate (Phase 3c)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_PYSHACL, reason="pyshacl not installed")
class TestSHACLConformance:
    """Exported RDF from random specs conforms to SHACL shapes.

    Separate from TestSpecRoundTripPBT to avoid pyshacl overhead on
    every round-trip test. Lower example count since validation is
    expensive.
    """

    @given(spec=gds_specs())
    @settings(max_examples=30)
    def test_spec_graph_conforms(self, spec: GDSSpec) -> None:
        """Exported GDSSpec RDF passes SHACL structural validation."""
        from gds_owl.shacl import validate_graph

        g = spec_to_graph(spec)
        conforms, _, text = validate_graph(g)
        assert conforms, f"SHACL validation failed:\n{text}"

    @given(ir=system_irs())
    @settings(max_examples=30)
    def test_system_ir_graph_conforms(self, ir: SystemIR) -> None:
        """Exported SystemIR RDF passes SHACL structural validation."""
        from gds_owl.shacl import validate_graph

        g = system_ir_to_graph(ir)
        conforms, _, text = validate_graph(g)
        assert conforms, f"SHACL validation failed:\n{text}"


# ---------------------------------------------------------------------------
# SPARQL Conformance (Phase 3c — no pyshacl dependency)
# ---------------------------------------------------------------------------


class TestSPARQLConformance:
    """SPARQL queries over exported RDF return expected results."""

    @given(spec=gds_specs())
    @settings(max_examples=30)
    def test_blocks_by_role_matches(self, spec: GDSSpec) -> None:
        """SPARQL blocks_by_role returns same blocks as the spec."""
        from gds_owl.sparql import run_query

        g = spec_to_graph(spec)
        results = run_query(g, "blocks_by_role")
        queried_names = {str(r["block_name"]) for r in results}
        assert queried_names == set(spec.blocks.keys())


# ---------------------------------------------------------------------------
# Derived Property Preservation (Phase 3d)
# ---------------------------------------------------------------------------


class TestDerivedPropertyPreservation:
    """Verify that OWL round-trip of SystemIR, CanonicalGDS, and
    VerificationReport preserves structural content.
    """

    # --- SystemIR preservation ---

    @given(ir=system_irs())
    @settings(max_examples=50)
    def test_system_ir_name_survives(self, ir: SystemIR) -> None:
        ir2 = _ir_round_trip(ir)
        assert ir2.name == ir.name

    @given(ir=system_irs())
    @settings(max_examples=50)
    def test_system_ir_block_names_survive(self, ir: SystemIR) -> None:
        ir2 = _ir_round_trip(ir)
        orig = {b.name for b in ir.blocks}
        new = {b.name for b in ir2.blocks}
        assert new == orig

    @given(ir=system_irs())
    @settings(max_examples=50)
    def test_system_ir_wiring_content_survives(self, ir: SystemIR) -> None:
        """Wiring source/target pairs survive round-trip."""
        ir2 = _ir_round_trip(ir)
        orig = {(w.source, w.target) for w in ir.wirings}
        new = {(w.source, w.target) for w in ir2.wirings}
        assert new == orig

    @given(ir=system_irs())
    @settings(max_examples=50)
    def test_system_ir_composition_type_survives(self, ir: SystemIR) -> None:
        ir2 = _ir_round_trip(ir)
        assert ir2.composition_type == ir.composition_type

    # --- CanonicalGDS preservation ---

    @given(pair=specs_with_canonical())
    @settings(max_examples=50)
    def test_canonical_block_roles_survive(
        self, pair: tuple[GDSSpec, CanonicalGDS]
    ) -> None:
        """Boundary, policy, and mechanism block sets survive."""
        _, can = pair
        can2 = _canonical_round_trip(can)
        assert set(can2.boundary_blocks) == set(can.boundary_blocks)
        assert set(can2.policy_blocks) == set(can.policy_blocks)
        assert set(can2.mechanism_blocks) == set(can.mechanism_blocks)

    @given(pair=specs_with_canonical())
    @settings(max_examples=50)
    def test_canonical_state_variables_survive(
        self, pair: tuple[GDSSpec, CanonicalGDS]
    ) -> None:
        _, can = pair
        can2 = _canonical_round_trip(can)
        assert set(can2.state_variables) == set(can.state_variables)

    # --- VerificationReport preservation ---

    @given(triple=specs_with_report())
    @settings(max_examples=50)
    def test_report_system_name_survives(
        self, triple: tuple[GDSSpec, SystemIR, VerificationReport]
    ) -> None:
        _, _, report = triple
        report2 = _report_round_trip(report)
        assert report2.system_name == report.system_name

    @given(triple=specs_with_report())
    @settings(max_examples=50)
    def test_report_findings_survive(
        self, triple: tuple[GDSSpec, SystemIR, VerificationReport]
    ) -> None:
        """Finding count and check_id distribution both survive."""
        _, _, report = triple
        report2 = _report_round_trip(report)
        assert len(report2.findings) == len(report.findings)
        orig_counts = Counter(f.check_id for f in report.findings)
        new_counts = Counter(f.check_id for f in report2.findings)
        assert new_counts == orig_counts


# ---------------------------------------------------------------------------
# Strategy Invariants
# ---------------------------------------------------------------------------


class TestStrategyInvariants:
    """Structural invariants of generated specs — not round-trip tests."""

    @given(triple=specs_with_report())
    @settings(max_examples=50)
    def test_g002_failures_on_expected_blocks_only(
        self, triple: tuple[GDSSpec, SystemIR, VerificationReport]
    ) -> None:
        """G-002 (signature completeness) failures are expected on
        BoundaryAction (no forward_in) and Mechanism (no forward_out).
        No other block types should fail G-002.
        """
        spec, _, report = triple
        g002_failed = [
            f for f in report.findings if f.check_id == "G-002" and not f.passed
        ]
        expected_incomplete = {
            name
            for name, block in spec.blocks.items()
            if isinstance(block, (BoundaryAction, Mechanism))
        }
        for finding in g002_failed:
            flagged = set(finding.source_elements)
            assert flagged <= expected_incomplete, (
                f"G-002 failed on unexpected blocks: {flagged - expected_incomplete}"
            )

    @given(triple=specs_with_report())
    @settings(max_examples=50)
    def test_g002_invariant_survives_round_trip(
        self, triple: tuple[GDSSpec, SystemIR, VerificationReport]
    ) -> None:
        """The G-002 invariant still holds after report round-trip."""
        spec, _, report = triple
        report2 = _report_round_trip(report)
        g002_failed = [
            f for f in report2.findings if f.check_id == "G-002" and not f.passed
        ]
        expected_incomplete = {
            name
            for name, block in spec.blocks.items()
            if isinstance(block, (BoundaryAction, Mechanism))
        }
        for finding in g002_failed:
            flagged = set(finding.source_elements)
            assert flagged <= expected_incomplete

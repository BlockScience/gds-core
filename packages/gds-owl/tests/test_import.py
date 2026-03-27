"""Tests for RDF -> Pydantic import functions."""

import pytest
from rdflib import Graph

from gds import CanonicalGDS, GDSSpec, SystemIR
from gds.verification.findings import VerificationReport
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


class TestGraphToSpec:
    def test_reconstructs_spec_name(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert spec2.name == "thermostat"

    def test_reconstructs_description(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert spec2.description == "Simple thermostat system"

    def test_reconstructs_types(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert set(spec2.types.keys()) == set(thermostat_spec.types.keys())

    def test_type_python_type_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        for name, td in spec2.types.items():
            assert td.python_type == thermostat_spec.types[name].python_type

    def test_type_units_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert spec2.types["Temperature"].units == "celsius"

    def test_reconstructs_spaces(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert set(spec2.spaces.keys()) == set(thermostat_spec.spaces.keys())

    def test_space_fields_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        for name, space in spec2.spaces.items():
            orig = thermostat_spec.spaces[name]
            assert set(space.fields.keys()) == set(orig.fields.keys())

    def test_reconstructs_entities(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert set(spec2.entities.keys()) == set(thermostat_spec.entities.keys())

    def test_entity_variables_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        for name, entity in spec2.entities.items():
            orig = thermostat_spec.entities[name]
            assert set(entity.variables.keys()) == set(orig.variables.keys())

    def test_reconstructs_blocks(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert set(spec2.blocks.keys()) == set(thermostat_spec.blocks.keys())

    def test_block_kinds_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        for name, block in spec2.blocks.items():
            orig = thermostat_spec.blocks[name]
            assert getattr(block, "kind", "generic") == getattr(orig, "kind", "generic")

    def test_block_params_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        from gds.blocks.roles import HasParams

        for name, block in spec2.blocks.items():
            orig = thermostat_spec.blocks[name]
            if isinstance(orig, HasParams):
                assert isinstance(block, HasParams)
                assert set(block.params_used) == set(orig.params_used)

    def test_mechanism_updates_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        from gds.blocks.roles import Mechanism

        for name, block in spec2.blocks.items():
            orig = thermostat_spec.blocks[name]
            if isinstance(orig, Mechanism):
                assert isinstance(block, Mechanism)
                assert set(block.updates) == set(orig.updates)

    def test_reconstructs_parameters(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert (
            spec2.parameter_schema.names() == thermostat_spec.parameter_schema.names()
        )

    def test_reconstructs_wirings(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        assert set(spec2.wirings.keys()) == set(thermostat_spec.wirings.keys())

    def test_wiring_wires_preserved(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spec2 = graph_to_spec(g)
        for name, wiring in spec2.wirings.items():
            orig = thermostat_spec.wirings[name]
            assert len(wiring.wires) == len(orig.wires)

    def test_raises_on_empty_graph(self) -> None:
        g = Graph()
        with pytest.raises(ValueError, match="No GDSSpec found"):
            graph_to_spec(g)


class TestGraphToSystemIR:
    def test_reconstructs_name(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        ir2 = graph_to_system_ir(g)
        assert ir2.name == "thermostat"

    def test_reconstructs_blocks(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        ir2 = graph_to_system_ir(g)
        assert len(ir2.blocks) == len(thermostat_ir.blocks)

    def test_block_names_match(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        ir2 = graph_to_system_ir(g)
        orig_names = {b.name for b in thermostat_ir.blocks}
        new_names = {b.name for b in ir2.blocks}
        assert new_names == orig_names

    def test_reconstructs_wirings(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        ir2 = graph_to_system_ir(g)
        assert len(ir2.wirings) == len(thermostat_ir.wirings)

    def test_composition_type_preserved(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        ir2 = graph_to_system_ir(g)
        assert ir2.composition_type == thermostat_ir.composition_type

    def test_raises_on_empty_graph(self) -> None:
        g = Graph()
        with pytest.raises(ValueError, match="No SystemIR found"):
            graph_to_system_ir(g)


class TestGraphToCanonical:
    def test_reconstructs_blocks(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        can2 = graph_to_canonical(g)
        assert set(can2.boundary_blocks) == set(thermostat_canonical.boundary_blocks)
        assert set(can2.policy_blocks) == set(thermostat_canonical.policy_blocks)
        assert set(can2.mechanism_blocks) == set(thermostat_canonical.mechanism_blocks)

    def test_reconstructs_state_variables(
        self, thermostat_canonical: CanonicalGDS
    ) -> None:
        g = canonical_to_graph(thermostat_canonical)
        can2 = graph_to_canonical(g)
        assert set(can2.state_variables) == set(thermostat_canonical.state_variables)

    def test_reconstructs_update_map(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        can2 = graph_to_canonical(g)
        # Compare as sets of (mech_name, set_of_updates)
        orig = {(m, frozenset(u)) for m, u in thermostat_canonical.update_map}
        new = {(m, frozenset(u)) for m, u in can2.update_map}
        assert new == orig

    def test_raises_on_empty_graph(self) -> None:
        g = Graph()
        with pytest.raises(ValueError, match="No CanonicalGDS found"):
            graph_to_canonical(g)


class TestGraphToReport:
    def test_reconstructs_system_name(
        self, thermostat_report: VerificationReport
    ) -> None:
        g = report_to_graph(thermostat_report)
        r2 = graph_to_report(g)
        assert r2.system_name == thermostat_report.system_name

    def test_reconstructs_findings_count(
        self, thermostat_report: VerificationReport
    ) -> None:
        g = report_to_graph(thermostat_report)
        r2 = graph_to_report(g)
        assert len(r2.findings) == len(thermostat_report.findings)

    def test_finding_check_ids_preserved(
        self, thermostat_report: VerificationReport
    ) -> None:
        g = report_to_graph(thermostat_report)
        r2 = graph_to_report(g)
        orig_ids = {f.check_id for f in thermostat_report.findings}
        new_ids = {f.check_id for f in r2.findings}
        assert new_ids == orig_ids

    def test_raises_on_empty_graph(self) -> None:
        g = Graph()
        with pytest.raises(ValueError, match="No VerificationReport found"):
            graph_to_report(g)

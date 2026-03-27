"""Round-trip tests: Pydantic -> Turtle -> Pydantic.

These prove the RDF representation is structurally lossless
(except for known lossy fields like TypeDef.constraint).
"""

from rdflib import Graph

from gds import CanonicalGDS, GDSSpec, SystemIR
from gds.blocks.roles import HasParams, Mechanism
from gds.verification.findings import VerificationReport
from gds_owl.import_ import (
    graph_to_canonical,
    graph_to_report,
    graph_to_spec,
    graph_to_system_ir,
)
from gds_owl.serialize import to_turtle


class TestSpecRoundTrip:
    def _round_trip(self, spec: GDSSpec) -> GDSSpec:
        from gds_owl.export import spec_to_graph

        g = spec_to_graph(spec)
        ttl = to_turtle(g)
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        return graph_to_spec(g2)

    def test_name_survives(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert spec2.name == thermostat_spec.name

    def test_types_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert set(spec2.types.keys()) == set(thermostat_spec.types.keys())
        for name in thermostat_spec.types:
            orig_type = thermostat_spec.types[name].python_type
            assert spec2.types[name].python_type == orig_type
            assert spec2.types[name].units == thermostat_spec.types[name].units

    def test_spaces_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert set(spec2.spaces.keys()) == set(thermostat_spec.spaces.keys())
        for name in thermostat_spec.spaces:
            assert set(spec2.spaces[name].fields.keys()) == set(
                thermostat_spec.spaces[name].fields.keys()
            )

    def test_entities_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert set(spec2.entities.keys()) == set(thermostat_spec.entities.keys())
        for name in thermostat_spec.entities:
            assert set(spec2.entities[name].variables.keys()) == set(
                thermostat_spec.entities[name].variables.keys()
            )

    def test_blocks_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert set(spec2.blocks.keys()) == set(thermostat_spec.blocks.keys())
        for name in thermostat_spec.blocks:
            orig = thermostat_spec.blocks[name]
            new = spec2.blocks[name]
            assert getattr(new, "kind", "generic") == getattr(orig, "kind", "generic")
            if isinstance(orig, HasParams):
                assert isinstance(new, HasParams)
                assert set(new.params_used) == set(orig.params_used)
            if isinstance(orig, Mechanism):
                assert isinstance(new, Mechanism)
                assert set(new.updates) == set(orig.updates)

    def test_parameters_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert (
            spec2.parameter_schema.names() == thermostat_spec.parameter_schema.names()
        )

    def test_wirings_survive(self, thermostat_spec: GDSSpec) -> None:
        spec2 = self._round_trip(thermostat_spec)
        assert set(spec2.wirings.keys()) == set(thermostat_spec.wirings.keys())
        for name in thermostat_spec.wirings:
            assert len(spec2.wirings[name].wires) == len(
                thermostat_spec.wirings[name].wires
            )

    def test_constraint_is_lossy(self, thermostat_spec: GDSSpec) -> None:
        """TypeDef.constraint is not serializable; imported as None."""
        spec2 = self._round_trip(thermostat_spec)
        for td in spec2.types.values():
            assert td.constraint is None

    def test_admissibility_constraints_survive(
        self, thermostat_spec: GDSSpec
    ) -> None:
        from gds.constraints import AdmissibleInputConstraint

        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="sensor_dep",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
                constraint=lambda s, u: True,
                description="Sensor reads room temp",
            )
        )
        spec2 = self._round_trip(thermostat_spec)
        assert "sensor_dep" in spec2.admissibility_constraints
        ac = spec2.admissibility_constraints["sensor_dep"]
        assert ac.boundary_block == "Sensor"
        assert set(ac.depends_on) == {("Room", "temperature")}
        assert ac.description == "Sensor reads room temp"
        assert ac.constraint is None  # lossy

    def test_transition_signatures_survive(
        self, thermostat_spec: GDSSpec
    ) -> None:
        from gds.constraints import TransitionSignature

        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
                depends_on_blocks=["Controller"],
                preserves_invariant="temp >= 0",
            )
        )
        spec2 = self._round_trip(thermostat_spec)
        assert "Heater" in spec2.transition_signatures
        ts = spec2.transition_signatures["Heater"]
        assert set(ts.reads) == {("Room", "temperature")}
        assert set(ts.depends_on_blocks) == {"Controller"}
        assert ts.preserves_invariant == "temp >= 0"


class TestSystemIRRoundTrip:
    def _round_trip(self, ir: SystemIR) -> SystemIR:
        from gds_owl.export import system_ir_to_graph

        g = system_ir_to_graph(ir)
        ttl = to_turtle(g)
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        return graph_to_system_ir(g2)

    def test_name_survives(self, thermostat_ir: SystemIR) -> None:
        ir2 = self._round_trip(thermostat_ir)
        assert ir2.name == thermostat_ir.name

    def test_blocks_survive(self, thermostat_ir: SystemIR) -> None:
        ir2 = self._round_trip(thermostat_ir)
        orig_names = {b.name for b in thermostat_ir.blocks}
        new_names = {b.name for b in ir2.blocks}
        assert new_names == orig_names

    def test_wirings_survive(self, thermostat_ir: SystemIR) -> None:
        ir2 = self._round_trip(thermostat_ir)
        assert len(ir2.wirings) == len(thermostat_ir.wirings)

    def test_composition_type_survives(self, thermostat_ir: SystemIR) -> None:
        ir2 = self._round_trip(thermostat_ir)
        assert ir2.composition_type == thermostat_ir.composition_type


class TestCanonicalRoundTrip:
    def _round_trip(self, can: CanonicalGDS) -> CanonicalGDS:
        from gds_owl.export import canonical_to_graph

        g = canonical_to_graph(can)
        ttl = to_turtle(g)
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        return graph_to_canonical(g2)

    def test_blocks_survive(self, thermostat_canonical: CanonicalGDS) -> None:
        can2 = self._round_trip(thermostat_canonical)
        assert set(can2.boundary_blocks) == set(thermostat_canonical.boundary_blocks)
        assert set(can2.policy_blocks) == set(thermostat_canonical.policy_blocks)
        assert set(can2.mechanism_blocks) == set(thermostat_canonical.mechanism_blocks)

    def test_state_variables_survive(self, thermostat_canonical: CanonicalGDS) -> None:
        can2 = self._round_trip(thermostat_canonical)
        assert set(can2.state_variables) == set(thermostat_canonical.state_variables)


class TestReportRoundTrip:
    def _round_trip(self, report: VerificationReport) -> VerificationReport:
        from gds_owl.export import report_to_graph

        g = report_to_graph(report)
        ttl = to_turtle(g)
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        return graph_to_report(g2)

    def test_system_name_survives(self, thermostat_report: VerificationReport) -> None:
        r2 = self._round_trip(thermostat_report)
        assert r2.system_name == thermostat_report.system_name

    def test_findings_survive(self, thermostat_report: VerificationReport) -> None:
        r2 = self._round_trip(thermostat_report)
        assert len(r2.findings) == len(thermostat_report.findings)
        orig_ids = {f.check_id for f in thermostat_report.findings}
        new_ids = {f.check_id for f in r2.findings}
        assert new_ids == orig_ids

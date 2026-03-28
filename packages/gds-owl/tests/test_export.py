"""Tests for GDS -> RDF export functions."""

from rdflib import RDF, Graph, Literal

from gds import CanonicalGDS, GDSSpec, SystemIR
from gds.verification.findings import VerificationReport
from gds_owl._namespace import GDS_CORE, GDS_IR, GDS_VERIF
from gds_owl.export import (
    canonical_to_graph,
    report_to_graph,
    spec_to_graph,
    system_ir_to_graph,
)
from gds_owl.serialize import (
    spec_to_turtle,
    system_ir_to_turtle,
    to_jsonld,
    to_ntriples,
    to_turtle,
)


class TestSpecToGraph:
    def test_returns_graph(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        assert isinstance(g, Graph)
        assert len(g) > 0

    def test_spec_individual_exists(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        specs = list(g.subjects(RDF.type, GDS_CORE["GDSSpec"]))
        assert len(specs) == 1

    def test_spec_name(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        specs = list(g.subjects(RDF.type, GDS_CORE["GDSSpec"]))
        names = list(g.objects(specs[0], GDS_CORE["name"]))
        assert Literal("thermostat") in names

    def test_types_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        typedefs = list(g.subjects(RDF.type, GDS_CORE["TypeDef"]))
        assert len(typedefs) >= 2  # Temperature, HeaterCommand (+ GainType)

    def test_typedef_has_python_type(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        typedefs = list(g.subjects(RDF.type, GDS_CORE["TypeDef"]))
        for td in typedefs:
            py_types = list(g.objects(td, GDS_CORE["pythonType"]))
            assert len(py_types) == 1

    def test_typedef_has_units(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        # Temperature has units="celsius"
        found_units = False
        for td in g.subjects(RDF.type, GDS_CORE["TypeDef"]):
            units = list(g.objects(td, GDS_CORE["units"]))
            if units and str(units[0]) == "celsius":
                found_units = True
        assert found_units

    def test_spaces_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        spaces = list(g.subjects(RDF.type, GDS_CORE["Space"]))
        assert len(spaces) == 2  # TemperatureSpace, CommandSpace

    def test_space_has_fields(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        fields = list(g.subjects(RDF.type, GDS_CORE["SpaceField"]))
        assert len(fields) >= 2

    def test_entities_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        entities = list(g.subjects(RDF.type, GDS_CORE["Entity"]))
        assert len(entities) == 1  # Room

    def test_entity_has_variables(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        state_vars = list(g.subjects(RDF.type, GDS_CORE["StateVariable"]))
        assert len(state_vars) == 1  # temperature

    def test_state_variable_has_symbol(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        svs = list(g.subjects(RDF.type, GDS_CORE["StateVariable"]))
        for sv in svs:
            symbols = list(g.objects(sv, GDS_CORE["symbol"]))
            assert len(symbols) == 1

    def test_blocks_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        # Check role classes
        boundaries = list(g.subjects(RDF.type, GDS_CORE["BoundaryAction"]))
        policies = list(g.subjects(RDF.type, GDS_CORE["Policy"]))
        mechanisms = list(g.subjects(RDF.type, GDS_CORE["Mechanism"]))
        assert len(boundaries) == 1  # Sensor
        assert len(policies) == 1  # Controller
        assert len(mechanisms) == 1  # Heater

    def test_block_has_interface(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        interfaces = list(g.subjects(RDF.type, GDS_CORE["Interface"]))
        assert len(interfaces) == 3

    def test_block_has_ports(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        ports = list(g.subjects(RDF.type, GDS_CORE["Port"]))
        # Sensor fwd_out, Controller fwd_in+fwd_out, Heater fwd_in
        assert len(ports) >= 3

    def test_mechanism_has_updates(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        entries = list(g.subjects(RDF.type, GDS_CORE["UpdateMapEntry"]))
        assert len(entries) == 1

    def test_policy_uses_parameter(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        policies = list(g.subjects(RDF.type, GDS_CORE["Policy"]))
        for p in policies:
            params = list(g.objects(p, GDS_CORE["usesParameter"]))
            assert len(params) == 1  # gain

    def test_parameters_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        params = list(g.subjects(RDF.type, GDS_CORE["ParameterDef"]))
        assert len(params) == 1  # gain

    def test_wirings_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        wirings = list(g.subjects(RDF.type, GDS_CORE["SpecWiring"]))
        assert len(wirings) == 1  # main

    def test_wires_exported(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        wires = list(g.subjects(RDF.type, GDS_CORE["Wire"]))
        assert len(wires) == 2  # Sensor->Controller, Controller->Heater

    def test_custom_base_uri(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec, base_uri="https://example.com/")
        ttl = g.serialize(format="turtle")
        assert "https://example.com/" in ttl


class TestSystemIRToGraph:
    def test_returns_graph(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        assert isinstance(g, Graph)

    def test_system_ir_exists(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        systems = list(g.subjects(RDF.type, GDS_IR["SystemIR"]))
        assert len(systems) == 1

    def test_block_irs_exported(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        blocks = list(g.subjects(RDF.type, GDS_IR["BlockIR"]))
        assert len(blocks) == 3

    def test_wiring_irs_exported(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        wirings = list(g.subjects(RDF.type, GDS_IR["WiringIR"]))
        assert len(wirings) >= 2

    def test_hierarchy_exported(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        nodes = list(g.subjects(RDF.type, GDS_IR["HierarchyNodeIR"]))
        assert len(nodes) >= 1

    def test_block_ir_has_signature(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        blocks = list(g.subjects(RDF.type, GDS_IR["BlockIR"]))
        for b in blocks:
            fwd_in = list(g.objects(b, GDS_IR["signatureForwardIn"]))
            assert len(fwd_in) == 1


class TestCanonicalToGraph:
    def test_returns_graph(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        assert isinstance(g, Graph)

    def test_canonical_exists(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        canons = list(g.subjects(RDF.type, GDS_CORE["CanonicalGDS"]))
        assert len(canons) == 1

    def test_formula_exported(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        canons = list(g.subjects(RDF.type, GDS_CORE["CanonicalGDS"]))
        formulas = list(g.objects(canons[0], GDS_CORE["formula"]))
        assert len(formulas) == 1
        assert "h" in str(formulas[0])

    def test_role_blocks_exported(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        canons = list(g.subjects(RDF.type, GDS_CORE["CanonicalGDS"]))
        can = canons[0]
        boundaries = list(g.objects(can, GDS_CORE["boundaryBlock"]))
        policies = list(g.objects(can, GDS_CORE["policyBlock"]))
        mechanisms = list(g.objects(can, GDS_CORE["mechanismBlock"]))
        assert len(boundaries) == 1
        assert len(policies) == 1
        assert len(mechanisms) == 1

    def test_update_map_exported(self, thermostat_canonical: CanonicalGDS) -> None:
        g = canonical_to_graph(thermostat_canonical)
        entries = list(g.subjects(RDF.type, GDS_CORE["UpdateMapEntry"]))
        assert len(entries) == 1


class TestReportToGraph:
    def test_returns_graph(self, thermostat_report: VerificationReport) -> None:
        g = report_to_graph(thermostat_report)
        assert isinstance(g, Graph)

    def test_report_exists(self, thermostat_report: VerificationReport) -> None:
        g = report_to_graph(thermostat_report)
        reports = list(g.subjects(RDF.type, GDS_VERIF["VerificationReport"]))
        assert len(reports) == 1

    def test_findings_exported(self, thermostat_report: VerificationReport) -> None:
        g = report_to_graph(thermostat_report)
        findings = list(g.subjects(RDF.type, GDS_VERIF["Finding"]))
        assert len(findings) == len(thermostat_report.findings)

    def test_finding_has_check_id(self, thermostat_report: VerificationReport) -> None:
        g = report_to_graph(thermostat_report)
        findings = list(g.subjects(RDF.type, GDS_VERIF["Finding"]))
        for f in findings:
            check_ids = list(g.objects(f, GDS_VERIF["checkId"]))
            assert len(check_ids) == 1


class TestSerializationFormats:
    def test_to_turtle(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        ttl = to_turtle(g)
        assert isinstance(ttl, str)
        assert "gds-core:GDSSpec" in ttl

    def test_to_jsonld(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        jld = to_jsonld(g)
        assert isinstance(jld, str)
        assert "thermostat" in jld

    def test_to_ntriples(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        nt = to_ntriples(g)
        assert isinstance(nt, str)
        assert "gds.block.science" in nt

    def test_spec_to_turtle_convenience(self, thermostat_spec: GDSSpec) -> None:
        ttl = spec_to_turtle(thermostat_spec)
        assert "thermostat" in ttl
        assert "gds-core:BoundaryAction" in ttl

    def test_system_ir_to_turtle_convenience(self, thermostat_ir: SystemIR) -> None:
        ttl = system_ir_to_turtle(thermostat_ir)
        assert "thermostat" in ttl
        assert "gds-ir:BlockIR" in ttl

    def test_turtle_parses_back(self, thermostat_spec: GDSSpec) -> None:
        g1 = spec_to_graph(thermostat_spec)
        ttl = to_turtle(g1)
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        assert len(g1) == len(g2)

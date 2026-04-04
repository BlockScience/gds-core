"""Tests for SysML model → RDF conversion."""

from gds_sysml.model import SysMLModel
from gds_sysml.rdf import sysml_to_rdf
from rdflib import RDF

from gds_owl._namespace import GDS_CORE


class TestRDFConversion:
    """Tests for sysml_to_rdf() on the satellite fixture."""

    def test_graph_not_empty(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        assert len(g) > 0

    def test_spec_individual_exists(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        specs = list(g.subjects(RDF.type, GDS_CORE["GDSSpec"]))
        assert len(specs) == 1

    def test_spec_name(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        spec = next(g.subjects(RDF.type, GDS_CORE["GDSSpec"]))
        name = str(next(g.objects(spec, GDS_CORE["name"])))
        assert name == "SimpleSatellite"

    def test_typedefs_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        typedefs = list(g.subjects(RDF.type, GDS_CORE["TypeDef"]))
        assert len(typedefs) >= 3  # At least Real + port types

    def test_entity_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        entities = list(g.subjects(RDF.type, GDS_CORE["Entity"]))
        assert len(entities) == 1
        name = str(next(g.objects(entities[0], GDS_CORE["name"])))
        assert name == "ThermalState"

    def test_state_variables_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        state_vars = list(g.subjects(RDF.type, GDS_CORE["StateVariable"]))
        assert len(state_vars) == 3  # temperature, heaterPower, radiatorAngle

    def test_parameters_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        params = list(g.subjects(RDF.type, GDS_CORE["ParameterDef"]))
        assert len(params) == 2  # solarConstant, thermalMass

    def test_blocks_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        # Count blocks by role
        boundaries = list(g.subjects(RDF.type, GDS_CORE["BoundaryAction"]))
        policies = list(g.subjects(RDF.type, GDS_CORE["Policy"]))
        mechanisms = list(g.subjects(RDF.type, GDS_CORE["Mechanism"]))
        assert len(boundaries) == 2  # SolarFluxSensor, TemperatureSensor
        assert len(policies) == 1  # ThermalController
        assert len(mechanisms) == 2  # HeaterActuator, RadiatorActuator

    def test_block_interfaces(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        interfaces = list(g.subjects(RDF.type, GDS_CORE["Interface"]))
        assert len(interfaces) == 5  # One per action

    def test_wiring_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        wirings = list(g.subjects(RDF.type, GDS_CORE["SpecWiring"]))
        assert len(wirings) == 1

    def test_wires_emitted(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        wires = list(g.subjects(RDF.type, GDS_CORE["Wire"]))
        assert len(wires) == 4

    def test_transition_signatures(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        sigs = list(g.subjects(RDF.type, GDS_CORE["TransitionSignature"]))
        assert len(sigs) == 2  # HeaterActuator, RadiatorActuator

    def test_update_entries(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        entries = list(g.subjects(RDF.type, GDS_CORE["UpdateMapEntry"]))
        assert len(entries) == 2  # temperature, radiatorAngle

    def test_total_triple_count(self, satellite_model: SysMLModel) -> None:
        g = sysml_to_rdf(satellite_model)
        # Sanity check: should have a reasonable number of triples
        assert len(g) > 50


class TestRDFMinimal:
    """Tests for RDF conversion of minimal models."""

    def test_empty_model(self) -> None:
        model = SysMLModel(name="Empty")
        g = sysml_to_rdf(model)
        specs = list(g.subjects(RDF.type, GDS_CORE["GDSSpec"]))
        assert len(specs) == 1

    def test_action_only_model(self) -> None:
        from gds_sysml.parser.regex import parse_sysml

        sysml = """
        package ActionOnly {
            @GDSPolicy
            action def MyPolicy {
                in port inputPort : Signal;
                out port outputPort : Command;
            }
        }
        """
        model = parse_sysml(sysml)
        g = sysml_to_rdf(model)
        policies = list(g.subjects(RDF.type, GDS_CORE["Policy"]))
        assert len(policies) == 1

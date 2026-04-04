"""Tests for the regex-based SysML v2 parser."""

from pathlib import Path

from gds_sysml.model import SysMLModel
from gds_sysml.parser.regex import (
    _extract_annotations,
    _parse_annotation_body,
    _strip_comments,
    parse_sysml,
)


class TestAnnotationParsing:
    """Tests for @GDS* annotation extraction."""

    def test_simple_annotation(self) -> None:
        anns = _extract_annotations("@GDSMechanism")
        assert len(anns) == 1
        assert anns[0].kind == "Mechanism"
        assert anns[0].properties == {}

    def test_annotation_with_body(self) -> None:
        anns = _extract_annotations("@GDSDynamics { reads = [x, y]; writes = [z]; }")
        assert len(anns) == 1
        assert anns[0].kind == "Dynamics"
        assert anns[0].properties["reads"] == ["x", "y"]
        assert anns[0].properties["writes"] == ["z"]

    def test_annotation_with_string_property(self) -> None:
        anns = _extract_annotations('@GDSStateVariable { symbol = "T"; }')
        assert len(anns) == 1
        assert anns[0].properties["symbol"] == "T"

    def test_annotation_with_bare_value(self) -> None:
        anns = _extract_annotations("@GDSParameter { units = kelvin; }")
        assert len(anns) == 1
        assert anns[0].properties["units"] == "kelvin"

    def test_multiple_annotations_on_line(self) -> None:
        anns = _extract_annotations(
            "@GDSMechanism @GDSDynamics { reads = [x]; writes = [y]; }"
        )
        assert len(anns) == 2
        assert anns[0].kind == "Mechanism"
        assert anns[1].kind == "Dynamics"

    def test_boundary_action_annotation(self) -> None:
        anns = _extract_annotations("@GDSBoundaryAction")
        assert len(anns) == 1
        assert anns[0].kind == "BoundaryAction"

    def test_no_annotations(self) -> None:
        anns = _extract_annotations("part def Foo {")
        assert len(anns) == 0


class TestAnnotationBody:
    """Tests for annotation body property parsing."""

    def test_empty_body(self) -> None:
        assert _parse_annotation_body("") == {}

    def test_list_value(self) -> None:
        props = _parse_annotation_body("reads = [a, b, c];")
        assert props["reads"] == ["a", "b", "c"]

    def test_quoted_string(self) -> None:
        props = _parse_annotation_body('symbol = "alpha";')
        assert props["symbol"] == "alpha"

    def test_bare_value(self) -> None:
        props = _parse_annotation_body("units = watts;")
        assert props["units"] == "watts"

    def test_multiple_properties(self) -> None:
        props = _parse_annotation_body('reads = [x, y]; writes = [z]; symbol = "f";')
        assert props["reads"] == ["x", "y"]
        assert props["writes"] == ["z"]
        assert props["symbol"] == "f"


class TestCommentStripping:
    """Tests for comment removal."""

    def test_line_comment(self) -> None:
        lines = _strip_comments("part def Foo { // this is a comment")
        assert lines[0] == "part def Foo { "

    def test_block_comment(self) -> None:
        lines = _strip_comments("/* block comment */\npart def Foo {")
        assert "block comment" not in lines[0]
        assert "part def Foo" in lines[1]

    def test_multiline_block_comment(self) -> None:
        text = "before\n/* start\nmiddle\nend */\nafter"
        lines = _strip_comments(text)
        joined = " ".join(lines)
        assert "middle" not in joined
        assert "before" in joined
        assert "after" in joined


class TestParserSatellite:
    """Tests for parsing the simple satellite fixture."""

    def test_model_name(self, satellite_model: SysMLModel) -> None:
        assert satellite_model.name == "SimpleSatellite"

    def test_metadata_defs(self, satellite_model: SysMLModel) -> None:
        assert "GDSBoundaryAction" in satellite_model.metadata_defs
        assert "GDSPolicy" in satellite_model.metadata_defs
        assert "GDSMechanism" in satellite_model.metadata_defs
        assert "GDSStateVariable" in satellite_model.metadata_defs
        assert "GDSParameter" in satellite_model.metadata_defs
        assert "GDSDynamics" in satellite_model.metadata_defs

    def test_parts_found(self, satellite_model: SysMLModel) -> None:
        assert "ThermalState" in satellite_model.parts

    def test_thermal_state_attributes(self, satellite_model: SysMLModel) -> None:
        thermal = satellite_model.parts["ThermalState"]
        attr_names = [a.name for a in thermal.attributes]
        assert "temperature" in attr_names
        assert "heaterPower" in attr_names
        assert "radiatorAngle" in attr_names
        assert "solarConstant" in attr_names
        assert "thermalMass" in attr_names

    def test_state_variable_annotations(self, satellite_model: SysMLModel) -> None:
        thermal = satellite_model.parts["ThermalState"]
        temp_attr = next(a for a in thermal.attributes if a.name == "temperature")
        assert any(ann.kind == "StateVariable" for ann in temp_attr.annotations)
        sv_ann = next(
            ann for ann in temp_attr.annotations if ann.kind == "StateVariable"
        )
        assert sv_ann.properties.get("symbol") == "T"

    def test_parameter_annotations(self, satellite_model: SysMLModel) -> None:
        thermal = satellite_model.parts["ThermalState"]
        solar = next(a for a in thermal.attributes if a.name == "solarConstant")
        assert any(ann.kind == "Parameter" for ann in solar.annotations)

    def test_actions_found(self, satellite_model: SysMLModel) -> None:
        expected_actions = {
            "SolarFluxSensor",
            "TemperatureSensor",
            "ThermalController",
            "HeaterActuator",
            "RadiatorActuator",
        }
        assert expected_actions == set(satellite_model.actions.keys())

    def test_boundary_action_role(self, satellite_model: SysMLModel) -> None:
        sensor = satellite_model.actions["SolarFluxSensor"]
        assert any(ann.kind == "BoundaryAction" for ann in sensor.annotations)

    def test_mechanism_role(self, satellite_model: SysMLModel) -> None:
        heater = satellite_model.actions["HeaterActuator"]
        assert any(ann.kind == "Mechanism" for ann in heater.annotations)

    def test_dynamics_annotation(self, satellite_model: SysMLModel) -> None:
        heater = satellite_model.actions["HeaterActuator"]
        dynamics = next(
            (ann for ann in heater.annotations if ann.kind == "Dynamics"), None
        )
        assert dynamics is not None
        assert dynamics.properties["reads"] == ["temperature", "heaterPower"]
        assert dynamics.properties["writes"] == ["temperature"]

    def test_action_ports(self, satellite_model: SysMLModel) -> None:
        controller = satellite_model.actions["ThermalController"]
        port_names = [p.name for p in controller.ports]
        assert "temperatureIn" in port_names
        assert "solarFluxIn" in port_names
        assert "heaterCommandOut" in port_names
        assert "radiatorCommandOut" in port_names

    def test_port_directions(self, satellite_model: SysMLModel) -> None:
        controller = satellite_model.actions["ThermalController"]
        temp_port = next(p for p in controller.ports if p.name == "temperatureIn")
        assert temp_port.direction == "in"
        heater_port = next(p for p in controller.ports if p.name == "heaterCommandOut")
        assert heater_port.direction == "out"

    def test_connections_found(self, satellite_model: SysMLModel) -> None:
        assert len(satellite_model.connections) == 4

    def test_connection_endpoints(self, satellite_model: SysMLModel) -> None:
        sources = {c.source for c in satellite_model.connections}
        targets = {c.target for c in satellite_model.connections}
        assert "SolarFluxSensor.solarFluxOut" in sources
        assert "ThermalController.solarFluxIn" in targets

    def test_parse_from_path(self, satellite_sysml_path: Path) -> None:
        model = parse_sysml(satellite_sysml_path)
        assert model.name == "SimpleSatellite"
        assert len(model.actions) == 5

    def test_parse_from_text(self, satellite_sysml_text: str) -> None:
        model = parse_sysml(satellite_sysml_text)
        assert model.name == "SimpleSatellite"
        assert len(model.actions) == 5


class TestParserMinimal:
    """Tests for parsing minimal SysML fragments."""

    def test_empty_package(self) -> None:
        model = parse_sysml("package Empty { }")
        assert model.name == "Empty"
        assert len(model.parts) == 0
        assert len(model.actions) == 0

    def test_single_action(self) -> None:
        sysml = """
        package Test {
            @GDSPolicy
            action def MyPolicy {
                in port inputPort : Signal;
                out port outputPort : Command;
            }
        }
        """
        model = parse_sysml(sysml)
        assert "MyPolicy" in model.actions
        policy = model.actions["MyPolicy"]
        assert any(ann.kind == "Policy" for ann in policy.annotations)
        assert len(policy.ports) == 2

    def test_single_part_with_state_var(self) -> None:
        sysml = """
        package Test {
            part def MyEntity {
                @GDSStateVariable { symbol = "x"; }
                attribute position : Real;
            }
        }
        """
        model = parse_sysml(sysml)
        assert "MyEntity" in model.parts
        entity = model.parts["MyEntity"]
        assert len(entity.attributes) == 1
        assert entity.attributes[0].name == "position"
        assert entity.attributes[0].type_name == "Real"

    def test_connection_parsing(self) -> None:
        sysml = """
        package Test {
            connect A.out to B.in;
            connect B.out to C.in;
        }
        """
        model = parse_sysml(sysml)
        assert len(model.connections) == 2
        assert model.connections[0].source == "A.out"
        assert model.connections[0].target == "B.in"

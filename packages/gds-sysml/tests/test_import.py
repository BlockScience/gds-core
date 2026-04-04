"""Tests for the end-to-end SysML → GDSSpec import pipeline."""

from pathlib import Path

from gds_sysml.import_ import sysml_to_spec
from gds_sysml.model import SysMLModel


class TestSysMLToSpec:
    """End-to-end tests for sysml_to_spec()."""

    def test_spec_name(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        assert spec.name == "SimpleSatellite"

    def test_spec_from_path(self, satellite_sysml_path: Path) -> None:
        spec = sysml_to_spec(satellite_sysml_path)
        assert spec.name == "SimpleSatellite"

    def test_spec_from_text(self, satellite_sysml_text: str) -> None:
        spec = sysml_to_spec(satellite_sysml_text)
        assert spec.name == "SimpleSatellite"

    def test_blocks_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        block_names = set(spec.blocks.keys())
        expected = {
            "SolarFluxSensor",
            "TemperatureSensor",
            "ThermalController",
            "HeaterActuator",
            "RadiatorActuator",
        }
        assert expected == block_names

    def test_block_roles(self, satellite_model: SysMLModel) -> None:
        from gds.blocks.roles import BoundaryAction, Mechanism, Policy

        spec = sysml_to_spec(satellite_model)
        assert isinstance(spec.blocks["SolarFluxSensor"], BoundaryAction)
        assert isinstance(spec.blocks["TemperatureSensor"], BoundaryAction)
        assert isinstance(spec.blocks["ThermalController"], Policy)
        assert isinstance(spec.blocks["HeaterActuator"], Mechanism)
        assert isinstance(spec.blocks["RadiatorActuator"], Mechanism)

    def test_entities_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        assert "ThermalState" in spec.entities
        entity = spec.entities["ThermalState"]
        var_names = set(entity.variables.keys())
        assert "temperature" in var_names
        assert "heaterPower" in var_names
        assert "radiatorAngle" in var_names

    def test_state_variable_symbols(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        entity = spec.entities["ThermalState"]
        assert entity.variables["temperature"].symbol == "T"
        assert entity.variables["heaterPower"].symbol == "P_h"
        assert entity.variables["radiatorAngle"].symbol == "alpha"

    def test_types_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        assert len(spec.types) > 0
        # Real should map to a float TypeDef
        type_names = set(spec.types.keys())
        assert "Real" in type_names

    def test_parameters_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        param_names = set(spec.parameter_schema.parameters.keys())
        assert "solarConstant" in param_names
        assert "thermalMass" in param_names

    def test_wirings_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        assert len(spec.wirings) > 0
        wiring = next(iter(spec.wirings.values()))
        assert len(wiring.wires) == 4

    def test_transition_signatures_imported(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        assert len(spec.transition_signatures) == 2
        ts_names = {ts.mechanism for ts in spec.transition_signatures.values()}
        assert "HeaterActuator" in ts_names
        assert "RadiatorActuator" in ts_names

    def test_mechanism_updates(self, satellite_model: SysMLModel) -> None:
        spec = sysml_to_spec(satellite_model)
        heater = spec.blocks["HeaterActuator"]
        assert hasattr(heater, "updates")
        # Should have update entries for temperature
        assert len(heater.updates) > 0


class TestMinimalImport:
    """Tests for importing minimal SysML models."""

    def test_empty_model(self) -> None:
        model = SysMLModel(name="Empty")
        spec = sysml_to_spec(model)
        assert spec.name == "Empty"
        assert len(spec.blocks) == 0

    def test_single_boundary_action(self) -> None:
        sysml = """
        package Test {
            @GDSBoundaryAction
            action def Sensor {
                out port dataOut : Signal;
            }
        }
        """
        spec = sysml_to_spec(sysml)
        assert "Sensor" in spec.blocks
        from gds.blocks.roles import BoundaryAction

        assert isinstance(spec.blocks["Sensor"], BoundaryAction)

    def test_policy_with_ports(self) -> None:
        sysml = """
        package Test {
            @GDSPolicy
            action def Controller {
                in port sensorIn : Data;
                out port commandOut : Command;
            }
        }
        """
        spec = sysml_to_spec(sysml)
        controller = spec.blocks["Controller"]
        assert len(controller.interface.forward_in) > 0
        assert len(controller.interface.forward_out) > 0

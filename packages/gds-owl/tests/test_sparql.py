"""Tests for SPARQL query templates."""

import pytest

from gds import GDSSpec, SystemIR
from gds.verification.findings import VerificationReport
from gds_owl.export import report_to_graph, spec_to_graph, system_ir_to_graph
from gds_owl.sparql import TEMPLATES, run_query


class TestTemplateRegistry:
    def test_templates_registered(self) -> None:
        assert len(TEMPLATES) >= 7

    def test_required_templates_exist(self) -> None:
        expected = [
            "blocks_by_role",
            "dependency_path",
            "entity_update_map",
            "param_impact",
            "ir_block_list",
            "ir_wiring_list",
            "verification_summary",
        ]
        for name in expected:
            assert name in TEMPLATES, f"Missing template: {name}"

    def test_templates_have_descriptions(self) -> None:
        for name, t in TEMPLATES.items():
            assert t.description, f"Template {name} has no description"

    def test_templates_have_queries(self) -> None:
        for name, t in TEMPLATES.items():
            assert "SELECT" in t.query or "CONSTRUCT" in t.query, (
                f"Template {name} has no SELECT/CONSTRUCT"
            )


class TestBlocksByRole:
    def test_returns_results(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "blocks_by_role")
        assert len(results) == 3  # Sensor, Controller, Heater

    def test_results_have_kind(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "blocks_by_role")
        kinds = {str(r["kind"]) for r in results}
        assert "boundary" in kinds
        assert "policy" in kinds
        assert "mechanism" in kinds

    def test_results_have_block_name(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "blocks_by_role")
        names = {str(r["block_name"]) for r in results}
        assert "Sensor" in names
        assert "Controller" in names
        assert "Heater" in names


class TestDependencyPath:
    def test_returns_wire_connections(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "dependency_path")
        assert len(results) == 2  # Sensor->Controller, Controller->Heater

    def test_wire_source_target(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "dependency_path")
        pairs = {(str(r["source"]), str(r["target"])) for r in results}
        assert ("Sensor", "Controller") in pairs
        assert ("Controller", "Heater") in pairs


class TestEntityUpdateMap:
    def test_returns_mechanism_updates(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "entity_update_map")
        assert len(results) == 1

    def test_heater_updates_room_temperature(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "entity_update_map")
        r = results[0]
        assert str(r["block_name"]) == "Heater"
        assert str(r["entity"]) == "Room"
        assert str(r["variable"]) == "temperature"


class TestParamImpact:
    def test_returns_param_usage(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "param_impact")
        assert len(results) == 1

    def test_gain_used_by_controller(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        results = run_query(g, "param_impact")
        r = results[0]
        assert str(r["param_name"]) == "gain"
        assert str(r["block_name"]) == "Controller"


class TestIRBlockList:
    def test_returns_blocks(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        results = run_query(g, "ir_block_list")
        assert len(results) == 3

    def test_block_names(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        results = run_query(g, "ir_block_list")
        names = {str(r["block_name"]) for r in results}
        assert "Sensor" in names
        assert "Controller" in names
        assert "Heater" in names


class TestIRWiringList:
    def test_returns_wirings(self, thermostat_ir: SystemIR) -> None:
        g = system_ir_to_graph(thermostat_ir)
        results = run_query(g, "ir_wiring_list")
        assert len(results) >= 2


class TestVerificationSummary:
    def test_returns_findings(self, thermostat_report: VerificationReport) -> None:
        g = report_to_graph(thermostat_report)
        results = run_query(g, "verification_summary")
        assert len(results) == len(thermostat_report.findings)

    def test_findings_have_check_ids(
        self, thermostat_report: VerificationReport
    ) -> None:
        g = report_to_graph(thermostat_report)
        results = run_query(g, "verification_summary")
        check_ids = {str(r["check_id"]) for r in results}
        assert len(check_ids) > 0


class TestRunQueryErrors:
    def test_unknown_template_raises(self, thermostat_spec: GDSSpec) -> None:
        g = spec_to_graph(thermostat_spec)
        with pytest.raises(KeyError, match="Unknown template"):
            run_query(g, "nonexistent_template")

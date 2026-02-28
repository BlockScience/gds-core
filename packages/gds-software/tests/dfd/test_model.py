"""Tests for DFDModel validation."""

import pytest

from gds_software.common.errors import SWValidationError
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process
from gds_software.dfd.model import DFDModel


class TestModelConstruction:
    def test_minimal(self):
        m = DFDModel(
            name="Test",
            processes=[Process(name="P")],
        )
        assert m.name == "Test"
        assert len(m.processes) == 1

    def test_full_model(self):
        m = DFDModel(
            name="Auth System",
            external_entities=[ExternalEntity(name="User")],
            processes=[
                Process(name="Authenticate"),
                Process(name="Authorize"),
            ],
            data_stores=[DataStore(name="User DB")],
            data_flows=[
                DataFlow(name="Login", source="User", target="Authenticate"),
                DataFlow(name="Check", source="Authenticate", target="User DB"),
                DataFlow(name="Result", source="Authenticate", target="Authorize"),
            ],
        )
        assert len(m.element_names) == 4


class TestValidation:
    def test_no_processes_raises(self):
        with pytest.raises(SWValidationError, match="at least one process"):
            DFDModel(name="Bad", processes=[])

    def test_duplicate_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate element name"):
            DFDModel(
                name="Bad",
                processes=[Process(name="X")],
                external_entities=[ExternalEntity(name="X")],
            )

    def test_flow_bad_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared element"):
            DFDModel(
                name="Bad",
                processes=[Process(name="P")],
                data_flows=[DataFlow(name="F", source="Ghost", target="P")],
            )

    def test_flow_bad_target_raises(self):
        with pytest.raises(SWValidationError, match="not a declared element"):
            DFDModel(
                name="Bad",
                processes=[Process(name="P")],
                data_flows=[DataFlow(name="F", source="P", target="Ghost")],
            )

    def test_ext_to_ext_raises(self):
        with pytest.raises(SWValidationError, match="two external entities"):
            DFDModel(
                name="Bad",
                external_entities=[
                    ExternalEntity(name="A"),
                    ExternalEntity(name="B"),
                ],
                processes=[Process(name="P")],
                data_flows=[DataFlow(name="F", source="A", target="B")],
            )


class TestProperties:
    def test_element_names(self):
        m = DFDModel(
            name="Test",
            external_entities=[ExternalEntity(name="E")],
            processes=[Process(name="P")],
            data_stores=[DataStore(name="D")],
        )
        assert m.element_names == {"E", "P", "D"}

    def test_external_names(self):
        m = DFDModel(
            name="Test",
            external_entities=[ExternalEntity(name="A"), ExternalEntity(name="B")],
            processes=[Process(name="P")],
        )
        assert m.external_names == {"A", "B"}

    def test_process_names(self):
        m = DFDModel(
            name="Test",
            processes=[Process(name="P1"), Process(name="P2")],
        )
        assert m.process_names == {"P1", "P2"}

    def test_store_names(self):
        m = DFDModel(
            name="Test",
            processes=[Process(name="P")],
            data_stores=[DataStore(name="D1"), DataStore(name="D2")],
        )
        assert m.store_names == {"D1", "D2"}

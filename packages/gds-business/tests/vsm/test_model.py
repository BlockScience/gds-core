"""Tests for ValueStreamModel."""

import pytest

from gds_business.common.errors import BizValidationError
from gds_business.vsm.elements import (
    Customer,
    InformationFlow,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)
from gds_business.vsm.model import ValueStreamModel


class TestValueStreamModelConstruction:
    def test_minimal(self):
        m = ValueStreamModel(
            name="test",
            steps=[ProcessStep(name="S1", cycle_time=10.0)],
        )
        assert m.name == "test"
        assert len(m.steps) == 1

    def test_full_model(self):
        m = ValueStreamModel(
            name="test",
            steps=[
                ProcessStep(name="S1", cycle_time=10.0),
                ProcessStep(name="S2", cycle_time=20.0),
            ],
            buffers=[InventoryBuffer(name="WIP", between=("S1", "S2"))],
            suppliers=[Supplier(name="Sup")],
            customers=[Customer(name="Cust", takt_time=30.0)],
            material_flows=[
                MaterialFlow(source="Sup", target="S1"),
                MaterialFlow(source="S1", target="WIP"),
                MaterialFlow(source="WIP", target="S2"),
                MaterialFlow(source="S2", target="Cust"),
            ],
        )
        assert len(m.material_flows) == 4

    def test_no_steps_fails(self):
        with pytest.raises(BizValidationError, match="at least one process step"):
            ValueStreamModel(name="test", steps=[])

    def test_duplicate_names_fails(self):
        with pytest.raises(BizValidationError, match="Duplicate element name"):
            ValueStreamModel(
                name="test",
                steps=[
                    ProcessStep(name="S1", cycle_time=10.0),
                    ProcessStep(name="S1", cycle_time=20.0),
                ],
            )

    def test_material_flow_source_invalid_fails(self):
        with pytest.raises(BizValidationError, match="source.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                material_flows=[MaterialFlow(source="Z", target="S1")],
            )

    def test_material_flow_target_invalid_fails(self):
        with pytest.raises(BizValidationError, match="target.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                material_flows=[MaterialFlow(source="S1", target="Z")],
            )

    def test_info_flow_source_invalid_fails(self):
        with pytest.raises(BizValidationError, match="source.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                information_flows=[InformationFlow(source="Z", target="S1")],
            )

    def test_info_flow_target_invalid_fails(self):
        with pytest.raises(BizValidationError, match="target.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                information_flows=[InformationFlow(source="S1", target="Z")],
            )

    def test_buffer_upstream_invalid_fails(self):
        with pytest.raises(BizValidationError, match="upstream step.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                buffers=[InventoryBuffer(name="WIP", between=("Z", "S1"))],
            )

    def test_buffer_downstream_invalid_fails(self):
        with pytest.raises(BizValidationError, match="downstream step.*not a declared"):
            ValueStreamModel(
                name="test",
                steps=[ProcessStep(name="S1", cycle_time=10.0)],
                buffers=[InventoryBuffer(name="WIP", between=("S1", "Z"))],
            )


class TestValueStreamModelProperties:
    def test_element_names(self):
        m = ValueStreamModel(
            name="test",
            steps=[ProcessStep(name="S1", cycle_time=10.0)],
            suppliers=[Supplier(name="Sup")],
            customers=[Customer(name="Cust", takt_time=30.0)],
        )
        assert m.element_names == {"S1", "Sup", "Cust"}

    def test_step_names(self):
        m = ValueStreamModel(
            name="test",
            steps=[
                ProcessStep(name="S1", cycle_time=10.0),
                ProcessStep(name="S2", cycle_time=20.0),
            ],
        )
        assert m.step_names == {"S1", "S2"}

    def test_buffer_names(self):
        m = ValueStreamModel(
            name="test",
            steps=[
                ProcessStep(name="S1", cycle_time=10.0),
                ProcessStep(name="S2", cycle_time=20.0),
            ],
            buffers=[InventoryBuffer(name="WIP", between=("S1", "S2"))],
        )
        assert m.buffer_names == {"WIP"}

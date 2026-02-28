"""Tests for VSM element declarations."""

import pytest
from pydantic import ValidationError

from gds_business.vsm.elements import (
    Customer,
    InformationFlow,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)


class TestProcessStep:
    def test_create(self):
        s = ProcessStep(name="Assembly", cycle_time=30.0)
        assert s.name == "Assembly"
        assert s.cycle_time == 30.0
        assert s.changeover_time == 0.0
        assert s.uptime == 1.0
        assert s.batch_size == 1
        assert s.operators == 1

    def test_with_params(self):
        s = ProcessStep(
            name="Welding",
            cycle_time=60.0,
            changeover_time=15.0,
            uptime=0.85,
            batch_size=10,
            operators=2,
        )
        assert s.uptime == 0.85
        assert s.batch_size == 10

    def test_frozen(self):
        s = ProcessStep(name="X", cycle_time=1.0)
        with pytest.raises(ValidationError):
            s.name = "Y"

    def test_uptime_bounds(self):
        with pytest.raises(ValidationError):
            ProcessStep(name="X", cycle_time=1.0, uptime=1.5)
        with pytest.raises(ValidationError):
            ProcessStep(name="X", cycle_time=1.0, uptime=-0.1)


class TestInventoryBuffer:
    def test_create(self):
        b = InventoryBuffer(name="WIP1", between=("Step1", "Step2"))
        assert b.name == "WIP1"
        assert b.quantity == 0.0
        assert b.between == ("Step1", "Step2")

    def test_with_quantity(self):
        b = InventoryBuffer(name="WIP1", quantity=50.0, between=("A", "B"))
        assert b.quantity == 50.0

    def test_frozen(self):
        b = InventoryBuffer(name="WIP1", between=("A", "B"))
        with pytest.raises(ValidationError):
            b.name = "WIP2"


class TestSupplier:
    def test_create(self):
        s = Supplier(name="Steel Co")
        assert s.name == "Steel Co"

    def test_frozen(self):
        s = Supplier(name="X")
        with pytest.raises(ValidationError):
            s.name = "Y"


class TestCustomer:
    def test_create(self):
        c = Customer(name="End User", takt_time=60.0)
        assert c.takt_time == 60.0

    def test_frozen(self):
        c = Customer(name="X", takt_time=1.0)
        with pytest.raises(ValidationError):
            c.name = "Y"


class TestMaterialFlow:
    def test_create_push(self):
        f = MaterialFlow(source="A", target="B")
        assert f.flow_type == "push"

    def test_create_pull(self):
        f = MaterialFlow(source="A", target="B", flow_type="pull")
        assert f.flow_type == "pull"

    def test_invalid_flow_type(self):
        with pytest.raises(ValidationError):
            MaterialFlow(source="A", target="B", flow_type="invalid")

    def test_frozen(self):
        f = MaterialFlow(source="A", target="B")
        with pytest.raises(ValidationError):
            f.source = "C"


class TestInformationFlow:
    def test_create(self):
        f = InformationFlow(source="A", target="B")
        assert f.source == "A"
        assert f.target == "B"

    def test_frozen(self):
        f = InformationFlow(source="A", target="B")
        with pytest.raises(ValidationError):
            f.source = "C"

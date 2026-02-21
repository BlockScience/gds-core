"""Tests for Entity and StateVariable."""

import pytest
from pydantic import ValidationError

from gds.state import Entity, StateVariable
from gds.types.typedef import TypeDef


class TestStateVariable:
    def test_creation(self):
        t = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        sv = StateVariable(name="population", typedef=t)
        assert sv.name == "population"
        assert sv.typedef == t

    def test_validate_passes(self):
        t = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        sv = StateVariable(name="population", typedef=t)
        assert sv.check_value(100) is True

    def test_validate_fails_type(self):
        t = TypeDef(name="Pop", python_type=int)
        sv = StateVariable(name="population", typedef=t)
        assert sv.check_value("not an int") is False

    def test_validate_fails_constraint(self):
        t = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        sv = StateVariable(name="population", typedef=t)
        assert sv.check_value(-1) is False

    def test_symbol(self):
        t = TypeDef(name="Pop", python_type=int)
        sv = StateVariable(name="population", typedef=t, symbol="N")
        assert sv.symbol == "N"

    def test_symbol_default(self):
        t = TypeDef(name="Pop", python_type=int)
        sv = StateVariable(name="population", typedef=t)
        assert sv.symbol == ""

    def test_description(self):
        t = TypeDef(name="Pop", python_type=int)
        sv = StateVariable(name="population", typedef=t, description="Current pop")
        assert sv.description == "Current pop"

    def test_frozen(self):
        t = TypeDef(name="Pop", python_type=int)
        sv = StateVariable(name="population", typedef=t)
        with pytest.raises(ValidationError):
            sv.name = "other"  # type: ignore[misc]


class TestEntity:
    def test_creation(self):
        t = TypeDef(name="Pop", python_type=int)
        e = Entity(
            name="Prey",
            variables={"population": StateVariable(name="population", typedef=t)},
        )
        assert e.name == "Prey"
        assert "population" in e.variables

    def test_validate_state_valid(self):
        t = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        e = Entity(
            name="Prey",
            variables={"population": StateVariable(name="population", typedef=t)},
        )
        assert e.validate_state({"population": 100}) == []

    def test_validate_state_missing(self):
        t = TypeDef(name="Pop", python_type=int)
        e = Entity(
            name="Prey",
            variables={"population": StateVariable(name="population", typedef=t)},
        )
        errors = e.validate_state({})
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_validate_state_invalid_value(self):
        t = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        e = Entity(
            name="Prey",
            variables={"population": StateVariable(name="population", typedef=t)},
        )
        errors = e.validate_state({"population": -1})
        assert len(errors) == 1
        assert "violation" in errors[0]

    def test_multiple_variables(self):
        t_pop = TypeDef(name="Pop", python_type=int, constraint=lambda x: x >= 0)
        t_rate = TypeDef(name="Rate", python_type=float, constraint=lambda x: x > 0)
        e = Entity(
            name="Species",
            variables={
                "population": StateVariable(name="population", typedef=t_pop),
                "growth_rate": StateVariable(name="growth_rate", typedef=t_rate),
            },
        )
        assert e.validate_state({"population": 50, "growth_rate": 0.1}) == []
        errors = e.validate_state({"population": 50, "growth_rate": -0.1})
        assert len(errors) == 1

    def test_frozen(self):
        e = Entity(name="Prey")
        with pytest.raises(ValidationError):
            e.name = "Other"  # type: ignore[misc]

"""Tests for stock-flow element declarations."""

import pytest

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock


class TestStock:
    def test_basic(self):
        s = Stock(name="Population")
        assert s.name == "Population"
        assert s.initial is None
        assert s.non_negative is True

    def test_with_initial(self):
        s = Stock(name="Water", initial=100.0, units="liters")
        assert s.initial == 100.0
        assert s.units == "liters"

    def test_frozen(self):
        s = Stock(name="Population")
        with pytest.raises(Exception):
            s.name = "Other"  # type: ignore[misc]


class TestFlow:
    def test_basic(self):
        f = Flow(name="Births", target="Population")
        assert f.name == "Births"
        assert f.source == ""
        assert f.target == "Population"

    def test_cloud_source(self):
        f = Flow(name="Immigration", target="Population")
        assert f.source == ""

    def test_both_stocks(self):
        f = Flow(name="Transfer", source="A", target="B")
        assert f.source == "A"
        assert f.target == "B"


class TestAuxiliary:
    def test_basic(self):
        a = Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"])
        assert a.name == "Birth Rate"
        assert a.inputs == ["Population", "Fertility"]

    def test_no_inputs(self):
        a = Auxiliary(name="Constant")
        assert a.inputs == []


class TestConverter:
    def test_basic(self):
        c = Converter(name="Fertility", units="births/person/year")
        assert c.name == "Fertility"
        assert c.units == "births/person/year"

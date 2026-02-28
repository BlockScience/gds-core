"""Tests for CLD element declarations."""

import pytest
from pydantic import ValidationError

from gds_business.cld.elements import CausalLink, Variable


class TestVariable:
    def test_create_minimal(self):
        v = Variable(name="Population")
        assert v.name == "Population"
        assert v.description == ""

    def test_create_with_description(self):
        v = Variable(name="GDP", description="Gross Domestic Product")
        assert v.description == "Gross Domestic Product"

    def test_frozen(self):
        v = Variable(name="X")
        with pytest.raises(ValidationError):
            v.name = "Y"

    def test_equality(self):
        v1 = Variable(name="X")
        v2 = Variable(name="X")
        assert v1 == v2

    def test_inequality(self):
        v1 = Variable(name="X")
        v2 = Variable(name="Y")
        assert v1 != v2


class TestCausalLink:
    def test_create_positive(self):
        link = CausalLink(source="A", target="B", polarity="+")
        assert link.source == "A"
        assert link.target == "B"
        assert link.polarity == "+"
        assert link.delay is False

    def test_create_negative_with_delay(self):
        link = CausalLink(source="A", target="B", polarity="-", delay=True)
        assert link.polarity == "-"
        assert link.delay is True

    def test_frozen(self):
        link = CausalLink(source="A", target="B", polarity="+")
        with pytest.raises(ValidationError):
            link.source = "C"

    def test_invalid_polarity(self):
        with pytest.raises(ValidationError):
            CausalLink(source="A", target="B", polarity="x")

    def test_equality(self):
        l1 = CausalLink(source="A", target="B", polarity="+")
        l2 = CausalLink(source="A", target="B", polarity="+")
        assert l1 == l2

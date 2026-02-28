"""Tests for CausalLoopModel."""

import pytest

from gds_business.cld.elements import CausalLink, Variable
from gds_business.cld.model import CausalLoopModel
from gds_business.common.errors import BizValidationError


class TestCausalLoopModelConstruction:
    def test_minimal(self):
        m = CausalLoopModel(name="test", variables=[Variable(name="X")])
        assert m.name == "test"
        assert len(m.variables) == 1

    def test_with_links(self):
        m = CausalLoopModel(
            name="test",
            variables=[Variable(name="A"), Variable(name="B")],
            links=[CausalLink(source="A", target="B", polarity="+")],
        )
        assert len(m.links) == 1

    def test_no_variables_fails(self):
        with pytest.raises(BizValidationError, match="at least one variable"):
            CausalLoopModel(name="test", variables=[])

    def test_duplicate_variable_names_fails(self):
        with pytest.raises(BizValidationError, match="Duplicate variable name"):
            CausalLoopModel(
                name="test",
                variables=[Variable(name="X"), Variable(name="X")],
            )

    def test_link_source_not_declared_fails(self):
        with pytest.raises(BizValidationError, match="not a declared variable"):
            CausalLoopModel(
                name="test",
                variables=[Variable(name="A")],
                links=[CausalLink(source="Z", target="A", polarity="+")],
            )

    def test_link_target_not_declared_fails(self):
        with pytest.raises(BizValidationError, match="not a declared variable"):
            CausalLoopModel(
                name="test",
                variables=[Variable(name="A")],
                links=[CausalLink(source="A", target="Z", polarity="+")],
            )

    def test_self_loop_fails(self):
        with pytest.raises(BizValidationError, match="Self-loop"):
            CausalLoopModel(
                name="test",
                variables=[Variable(name="A")],
                links=[CausalLink(source="A", target="A", polarity="+")],
            )


class TestCausalLoopModelProperties:
    def test_variable_names(self):
        m = CausalLoopModel(
            name="test",
            variables=[Variable(name="A"), Variable(name="B")],
        )
        assert m.variable_names == {"A", "B"}


class TestCausalLoopModelDescriptions:
    def test_description(self):
        m = CausalLoopModel(
            name="test",
            variables=[Variable(name="X")],
            description="A test CLD",
        )
        assert m.description == "A test CLD"


class TestCausalLoopModelMultipleErrors:
    def test_multiple_errors_reported(self):
        with pytest.raises(BizValidationError) as exc_info:
            CausalLoopModel(
                name="test",
                variables=[Variable(name="A"), Variable(name="A")],
                links=[CausalLink(source="Z", target="W", polarity="+")],
            )
        msg = str(exc_info.value)
        assert "Duplicate" in msg
        assert "not a declared" in msg

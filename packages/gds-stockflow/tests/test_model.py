"""Tests for StockFlowModel validation."""

import pytest

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.errors import SFValidationError
from stockflow.dsl.model import StockFlowModel


class TestModelConstruction:
    def test_minimal(self):
        m = StockFlowModel(name="Test", stocks=[Stock(name="S")])
        assert m.name == "Test"
        assert len(m.stocks) == 1

    def test_full_model(self):
        m = StockFlowModel(
            name="Population",
            stocks=[Stock(name="Population", initial=1000.0)],
            flows=[
                Flow(name="Births", target="Population"),
                Flow(name="Deaths", source="Population"),
            ],
            auxiliaries=[
                Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
            ],
            converters=[Converter(name="Fertility")],
        )
        assert len(m.element_names) == 5


class TestValidation:
    def test_no_stocks_raises(self):
        with pytest.raises(SFValidationError, match="at least one stock"):
            StockFlowModel(name="Bad", stocks=[])

    def test_duplicate_names_raises(self):
        with pytest.raises(SFValidationError, match="Duplicate element name"):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="X")],
                flows=[Flow(name="X", target="X")],
            )

    def test_flow_bad_source_raises(self):
        with pytest.raises(SFValidationError, match="not a declared stock"):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="A")],
                flows=[Flow(name="F", source="Nonexistent", target="A")],
            )

    def test_flow_bad_target_raises(self):
        with pytest.raises(SFValidationError, match="not a declared stock"):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="A")],
                flows=[Flow(name="F", source="A", target="Nonexistent")],
            )

    def test_flow_no_source_or_target_raises(self):
        with pytest.raises(SFValidationError, match="at least one of source or target"):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="A")],
                flows=[Flow(name="F")],
            )

    def test_auxiliary_bad_input_raises(self):
        with pytest.raises(SFValidationError, match="not a declared element"):
            StockFlowModel(
                name="Bad",
                stocks=[Stock(name="A")],
                auxiliaries=[Auxiliary(name="Aux", inputs=["Nonexistent"])],
            )

    def test_auxiliary_references_valid_elements(self):
        m = StockFlowModel(
            name="OK",
            stocks=[Stock(name="S")],
            converters=[Converter(name="C")],
            auxiliaries=[Auxiliary(name="A", inputs=["S", "C"])],
        )
        assert len(m.auxiliaries) == 1


class TestProperties:
    def test_element_names(self):
        m = StockFlowModel(
            name="Test",
            stocks=[Stock(name="S")],
            flows=[Flow(name="F", target="S")],
            converters=[Converter(name="C")],
        )
        assert m.element_names == {"S", "F", "C"}

    def test_stock_names(self):
        m = StockFlowModel(
            name="Test",
            stocks=[Stock(name="A"), Stock(name="B")],
        )
        assert m.stock_names == {"A", "B"}

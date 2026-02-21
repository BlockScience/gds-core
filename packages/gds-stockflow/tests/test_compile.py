"""Tests for compilation: StockFlowModel → GDSSpec → SystemIR."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec
from gds.state import Entity

from stockflow.dsl.compile import (
    LevelType,
    compile_model,
    compile_to_system,
)
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel


@pytest.fixture
def population_model():
    return StockFlowModel(
        name="Population",
        stocks=[Stock(name="Population", initial=1000.0)],
        flows=[
            Flow(name="Births", target="Population"),
            Flow(name="Deaths", source="Population"),
        ],
        auxiliaries=[
            Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
            Auxiliary(name="Death Rate", inputs=["Population"]),
        ],
        converters=[Converter(name="Fertility")],
    )


@pytest.fixture
def two_stock_model():
    return StockFlowModel(
        name="Predator Prey",
        stocks=[
            Stock(name="Prey", initial=100.0),
            Stock(name="Predator", initial=20.0),
        ],
        flows=[
            Flow(name="Prey Births", target="Prey"),
            Flow(name="Prey Deaths", source="Prey"),
            Flow(name="Predator Births", target="Predator"),
            Flow(name="Predator Deaths", source="Predator"),
        ],
    )


class TestCompileModel:
    def test_returns_gds_spec(self, population_model):
        spec = compile_model(population_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Population"

    def test_types_registered(self, population_model):
        spec = compile_model(population_model)
        assert "Level" in spec.types
        assert "Rate" in spec.types
        assert "Signal" in spec.types

    def test_spaces_registered(self, population_model):
        spec = compile_model(population_model)
        assert "LevelSpace" in spec.spaces
        assert "RateSpace" in spec.spaces
        assert "SignalSpace" in spec.spaces

    def test_entities_for_stocks(self, population_model):
        spec = compile_model(population_model)
        assert "Population" in spec.entities
        entity = spec.entities["Population"]
        assert isinstance(entity, Entity)
        assert "level" in entity.variables
        assert entity.variables["level"].typedef == LevelType

    def test_converter_becomes_boundary_action(self, population_model):
        spec = compile_model(population_model)
        assert "Fertility" in spec.blocks
        block = spec.blocks["Fertility"]
        assert isinstance(block, BoundaryAction)
        assert block.interface.forward_in == ()
        assert len(block.interface.forward_out) == 1
        assert block.interface.forward_out[0].name == "Fertility Signal"

    def test_auxiliary_becomes_policy(self, population_model):
        spec = compile_model(population_model)
        assert "Birth Rate" in spec.blocks
        block = spec.blocks["Birth Rate"]
        assert isinstance(block, Policy)
        # Receives Population Level + Fertility Signal
        port_names = {p.name for p in block.interface.forward_in}
        assert "Population Level" in port_names
        assert "Fertility Signal" in port_names
        # Emits Birth Rate Signal
        assert block.interface.forward_out[0].name == "Birth Rate Signal"

    def test_flow_becomes_policy(self, population_model):
        spec = compile_model(population_model)
        assert "Deaths" in spec.blocks
        block = spec.blocks["Deaths"]
        assert isinstance(block, Policy)
        # Emits rate
        assert block.interface.forward_out[0].name == "Deaths Rate"

    def test_flow_has_no_forward_in(self, population_model):
        """Flow forward_in is empty — source stock level arrives via temporal loop."""
        spec = compile_model(population_model)
        deaths = spec.blocks["Deaths"]
        assert deaths.interface.forward_in == ()

    def test_stock_becomes_mechanism(self, population_model):
        spec = compile_model(population_model)
        assert "Population Accumulation" in spec.blocks
        block = spec.blocks["Population Accumulation"]
        assert isinstance(block, Mechanism)
        # Receives rates from Births and Deaths
        port_names = {p.name for p in block.interface.forward_in}
        assert "Births Rate" in port_names
        assert "Deaths Rate" in port_names
        # Emits level for temporal loop
        assert block.interface.forward_out[0].name == "Population Level"
        # Updates entity
        assert ("Population", "level") in block.updates

    def test_wirings_registered(self, population_model):
        spec = compile_model(population_model)
        assert len(spec.wirings) == 1
        wiring = list(spec.wirings.values())[0]
        assert len(wiring.wires) > 0

    def test_parameters_registered(self, population_model):
        spec = compile_model(population_model)
        param_names = spec.parameter_schema.names()
        assert "Fertility" in param_names

    def test_two_stocks(self, two_stock_model):
        spec = compile_model(two_stock_model)
        assert "Prey" in spec.entities
        assert "Predator" in spec.entities
        assert "Prey Accumulation" in spec.blocks
        assert "Predator Accumulation" in spec.blocks


class TestCompileToSystem:
    def test_returns_system_ir(self, population_model):
        ir = compile_to_system(population_model)
        assert ir.name == "Population"
        assert len(ir.blocks) > 0
        assert len(ir.wirings) > 0

    def test_block_count(self, population_model):
        ir = compile_to_system(population_model)
        # 1 converter + 2 auxiliaries + 2 flows + 1 mechanism = 6
        assert len(ir.blocks) == 6

    def test_block_names(self, population_model):
        ir = compile_to_system(population_model)
        names = {b.name for b in ir.blocks}
        assert "Fertility" in names
        assert "Birth Rate" in names
        assert "Death Rate" in names
        assert "Births" in names
        assert "Deaths" in names
        assert "Population Accumulation" in names

    def test_auto_wiring_connects_tiers(self, population_model):
        ir = compile_to_system(population_model)
        # Should have auto-wirings between tiers
        assert len(ir.wirings) > 0
        sources = {w.source for w in ir.wirings}
        targets = {w.target for w in ir.wirings}
        # Converter should feed something
        assert "Fertility" in sources
        # Mechanism should receive rates
        assert "Population Accumulation" in targets

    def test_temporal_wirings_exist(self, population_model):
        ir = compile_to_system(population_model)
        temporal = [w for w in ir.wirings if w.is_temporal]
        # Population → Birth Rate, Population → Death Rate (auxiliaries only)
        assert len(temporal) == 2

    def test_stocks_only_model(self):
        model = StockFlowModel(
            name="Simple",
            stocks=[Stock(name="A")],
        )
        ir = compile_to_system(model)
        assert len(ir.blocks) == 1
        assert ir.blocks[0].name == "A Accumulation"

    def test_two_stocks_system(self, two_stock_model):
        ir = compile_to_system(two_stock_model)
        assert len(ir.blocks) == 6  # 4 flows + 2 mechanisms

    def test_hierarchy_exists(self, population_model):
        ir = compile_to_system(population_model)
        assert ir.hierarchy is not None

    def test_method_delegation(self, population_model):
        """model.compile_system() delegates to compile_to_system()."""
        ir = population_model.compile_system()
        assert ir.name == "Population"
        assert len(ir.blocks) == 6

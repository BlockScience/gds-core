"""Tests for CLD compilation."""

from gds.blocks.roles import Policy
from gds.canonical import project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec

from gds_business.cld.compile import compile_cld, compile_cld_to_system
from gds_business.cld.elements import CausalLink, Variable
from gds_business.cld.model import CausalLoopModel


def _simple_model() -> CausalLoopModel:
    return CausalLoopModel(
        name="Simple CLD",
        variables=[
            Variable(name="Population"),
            Variable(name="Births"),
            Variable(name="Deaths"),
        ],
        links=[
            CausalLink(source="Population", target="Births", polarity="+"),
            CausalLink(source="Population", target="Deaths", polarity="+"),
            CausalLink(source="Births", target="Population", polarity="+"),
            CausalLink(source="Deaths", target="Population", polarity="-"),
        ],
    )


def _two_variable_model() -> CausalLoopModel:
    return CausalLoopModel(
        name="Two Var CLD",
        variables=[Variable(name="A"), Variable(name="B")],
        links=[CausalLink(source="A", target="B", polarity="+")],
    )


def _isolated_variable_model() -> CausalLoopModel:
    return CausalLoopModel(
        name="Isolated",
        variables=[Variable(name="X")],
    )


class TestCompileCLD:
    def test_returns_gds_spec(self):
        spec = compile_cld(_simple_model())
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Simple CLD"

    def test_registers_types(self):
        spec = compile_cld(_simple_model())
        assert "CLD Signal" in spec.types

    def test_registers_spaces(self):
        spec = compile_cld(_simple_model())
        assert "CLD SignalSpace" in spec.spaces

    def test_registers_blocks_as_policy(self):
        spec = compile_cld(_simple_model())
        assert len(spec.blocks) == 3
        for block in spec.blocks.values():
            assert isinstance(block, Policy)

    def test_no_entities(self):
        spec = compile_cld(_simple_model())
        assert len(spec.entities) == 0

    def test_registers_wirings(self):
        spec = compile_cld(_simple_model())
        assert len(spec.wirings) == 1

    def test_wire_count(self):
        spec = compile_cld(_simple_model())
        wiring = list(spec.wirings.values())[0]
        assert len(wiring.wires) == 4

    def test_no_wiring_when_no_links(self):
        spec = compile_cld(_isolated_variable_model())
        assert len(spec.wirings) == 0

    def test_two_variable_spec(self):
        spec = compile_cld(_two_variable_model())
        assert len(spec.blocks) == 2


class TestCompileCLDToSystem:
    def test_returns_system_ir(self):
        ir = compile_cld_to_system(_simple_model())
        assert isinstance(ir, SystemIR)
        assert ir.name == "Simple CLD"

    def test_block_count(self):
        ir = compile_cld_to_system(_simple_model())
        assert len(ir.blocks) == 3

    def test_single_variable(self):
        ir = compile_cld_to_system(_isolated_variable_model())
        assert len(ir.blocks) == 1

    def test_two_variable(self):
        ir = compile_cld_to_system(_two_variable_model())
        assert len(ir.blocks) == 2


class TestCLDCanonical:
    """CLD should be stateless: h = g, no mechanisms, no state."""

    def test_canonical_stateless(self):
        spec = compile_cld(_simple_model())
        canon = project_canonical(spec)
        # All blocks are Policy → g (observation/decision)
        # No Mechanism/Entity → f is empty, X is empty
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 3
        assert len(canon.state_variables) == 0

    def test_canonical_no_boundary_or_control(self):
        spec = compile_cld(_simple_model())
        canon = project_canonical(spec)
        assert len(canon.boundary_blocks) == 0
        assert len(canon.control_blocks) == 0


class TestCLDModelCompileMethods:
    def test_model_compile(self):
        m = _simple_model()
        spec = m.compile()
        assert isinstance(spec, GDSSpec)

    def test_model_compile_system(self):
        m = _simple_model()
        ir = m.compile_system()
        assert isinstance(ir, SystemIR)

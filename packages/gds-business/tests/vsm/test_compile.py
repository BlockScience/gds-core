"""Tests for VSM compilation."""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec

from gds_business.vsm.compile import (
    compile_vsm,
    compile_vsm_to_system,
)
from gds_business.vsm.elements import (
    Customer,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)
from gds_business.vsm.model import ValueStreamModel


def _manufacturing_line() -> ValueStreamModel:
    """A manufacturing line with buffers — stateful."""
    return ValueStreamModel(
        name="Manufacturing Line",
        steps=[
            ProcessStep(name="Cutting", cycle_time=30.0),
            ProcessStep(name="Welding", cycle_time=45.0),
            ProcessStep(name="Assembly", cycle_time=25.0),
        ],
        buffers=[
            InventoryBuffer(
                name="Cut WIP", between=("Cutting", "Welding"), quantity=10
            ),
            InventoryBuffer(
                name="Weld WIP", between=("Welding", "Assembly"), quantity=5
            ),
        ],
        suppliers=[Supplier(name="Steel Supplier")],
        customers=[Customer(name="End Customer", takt_time=50.0)],
        material_flows=[
            MaterialFlow(source="Steel Supplier", target="Cutting"),
            MaterialFlow(source="Cutting", target="Cut WIP"),
            MaterialFlow(source="Cut WIP", target="Welding"),
            MaterialFlow(source="Welding", target="Weld WIP"),
            MaterialFlow(source="Weld WIP", target="Assembly"),
            MaterialFlow(source="Assembly", target="End Customer"),
        ],
    )


def _stateless_vsm() -> ValueStreamModel:
    """No buffers — stateless process chain."""
    return ValueStreamModel(
        name="Stateless VSM",
        steps=[
            ProcessStep(name="Step1", cycle_time=10.0),
            ProcessStep(name="Step2", cycle_time=20.0),
        ],
        suppliers=[Supplier(name="Sup")],
        customers=[Customer(name="Cust", takt_time=30.0)],
        material_flows=[
            MaterialFlow(source="Sup", target="Step1"),
            MaterialFlow(source="Step1", target="Step2"),
            MaterialFlow(source="Step2", target="Cust"),
        ],
    )


def _minimal_vsm() -> ValueStreamModel:
    return ValueStreamModel(
        name="Minimal",
        steps=[ProcessStep(name="S1", cycle_time=10.0)],
    )


class TestCompileVSM:
    def test_returns_gds_spec(self):
        spec = compile_vsm(_manufacturing_line())
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Manufacturing Line"

    def test_registers_types(self):
        spec = compile_vsm(_manufacturing_line())
        assert "VSM Material" in spec.types
        assert "VSM ProcessSignal" in spec.types

    def test_registers_spaces(self):
        spec = compile_vsm(_manufacturing_line())
        assert "VSM MaterialSpace" in spec.spaces
        assert "VSM ProcessSignalSpace" in spec.spaces

    def test_registers_entities_for_buffers(self):
        spec = compile_vsm(_manufacturing_line())
        assert len(spec.entities) == 2  # Cut WIP, Weld WIP

    def test_no_entities_when_no_buffers(self):
        spec = compile_vsm(_stateless_vsm())
        assert len(spec.entities) == 0

    def test_block_roles_stateful(self):
        spec = compile_vsm(_manufacturing_line())
        boundary = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundary) == 2  # Supplier + Customer
        assert len(policies) == 3  # 3 steps
        assert len(mechanisms) == 2  # 2 buffers

    def test_block_roles_stateless(self):
        spec = compile_vsm(_stateless_vsm())
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(mechanisms) == 0

    def test_registers_wirings(self):
        spec = compile_vsm(_manufacturing_line())
        assert len(spec.wirings) == 1

    def test_no_wiring_when_no_flows(self):
        spec = compile_vsm(_minimal_vsm())
        assert len(spec.wirings) == 0


class TestCompileVSMToSystem:
    def test_returns_system_ir(self):
        ir = compile_vsm_to_system(_manufacturing_line())
        assert isinstance(ir, SystemIR)
        assert ir.name == "Manufacturing Line"

    def test_block_count_stateful(self):
        ir = compile_vsm_to_system(_manufacturing_line())
        # 2 boundary + 3 steps + 2 buffer mechs = 7
        assert len(ir.blocks) == 7

    def test_block_count_stateless(self):
        ir = compile_vsm_to_system(_stateless_vsm())
        # 2 boundary + 2 steps = 4
        assert len(ir.blocks) == 4

    def test_minimal(self):
        ir = compile_vsm_to_system(_minimal_vsm())
        assert len(ir.blocks) == 1


class TestVSMCanonical:
    """VSM with buffers should be h = f o g, without buffers h = g."""

    def test_canonical_stateful(self):
        spec = compile_vsm(_manufacturing_line())
        canon = project_canonical(spec)
        assert len(canon.mechanism_blocks) == 2
        assert len(canon.policy_blocks) == 3
        assert len(canon.boundary_blocks) == 2
        assert len(canon.state_variables) == 2

    def test_canonical_stateless(self):
        spec = compile_vsm(_stateless_vsm())
        canon = project_canonical(spec)
        assert len(canon.mechanism_blocks) == 0
        assert len(canon.policy_blocks) == 2
        assert len(canon.boundary_blocks) == 2
        assert len(canon.state_variables) == 0


class TestVSMModelCompileMethods:
    def test_model_compile(self):
        m = _manufacturing_line()
        spec = m.compile()
        assert isinstance(spec, GDSSpec)

    def test_model_compile_system(self):
        m = _manufacturing_line()
        ir = m.compile_system()
        assert isinstance(ir, SystemIR)

"""Tests for blocks: AtomicBlock, composition operators, and GDS roles."""

import pytest
from pydantic import ValidationError

from gds.blocks.base import AtomicBlock, Block
from gds.blocks.composition import (
    FeedbackLoop,
    ParallelComposition,
    StackComposition,
    TemporalLoop,
    Wiring,
)
from gds.blocks.errors import GDSCompositionError, GDSTypeError
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.ir.models import FlowDirection
from gds.types.interface import Interface, port

# ── AtomicBlock ──────────────────────────────────────────────


class TestAtomicBlock:
    def test_creation(self):
        b = AtomicBlock(name="A")
        assert b.name == "A"
        assert b.interface == Interface()

    def test_flatten_returns_self(self):
        b = AtomicBlock(name="A")
        assert b.flatten() == [b]

    def test_interface_preserved(self):
        iface = Interface(forward_out=(port("X"),))
        b = AtomicBlock(name="A", interface=iface)
        assert b.interface == iface

    def test_is_block(self):
        b = AtomicBlock(name="A")
        assert isinstance(b, Block)


# ── StackComposition ─────────────────────────────────────────


class TestStackComposition:
    def test_rshift_operator(self, block_a, block_b):
        comp = block_a >> block_b
        assert isinstance(comp, StackComposition)

    def test_type_mismatch_raises(self, block_a, block_unrelated):
        with pytest.raises(GDSTypeError):
            _ = block_a >> block_unrelated

    def test_explicit_wiring_bypasses_check(self, block_a, block_unrelated):
        comp = StackComposition(
            name="explicit",
            first=block_a,
            second=block_unrelated,
            wiring=[
                Wiring(
                    source_block="A",
                    source_port="Temperature",
                    target_block="Unrelated",
                    target_port="Pressure",
                )
            ],
        )
        assert comp is not None

    def test_flatten_order(self, block_a, block_b):
        comp = block_a >> block_b
        flat = comp.flatten()
        assert flat[0].name == "A"
        assert flat[1].name == "B"

    def test_chained_three_blocks(self, block_a, block_b, block_c):
        comp = block_a >> block_b >> block_c
        flat = comp.flatten()
        assert len(flat) == 3
        assert [b.name for b in flat] == ["A", "B", "C"]

    def test_interface_union(self, block_a, block_b):
        comp = block_a >> block_b
        assert len(comp.interface.forward_out) == 2  # Temperature + Command


# ── ParallelComposition ──────────────────────────────────────


class TestParallelComposition:
    def test_or_operator(self, block_a, block_b):
        comp = block_a | block_b
        assert isinstance(comp, ParallelComposition)

    def test_flatten(self, block_a, block_b):
        comp = block_a | block_b
        flat = comp.flatten()
        assert len(flat) == 2

    def test_interface_union(self, block_a, block_b):
        comp = block_a | block_b
        assert len(comp.interface.forward_out) == 2
        assert len(comp.interface.forward_in) == 1


# ── FeedbackLoop ─────────────────────────────────────────────


class TestFeedbackLoop:
    def test_feedback(self, block_controller, block_plant):
        inner = block_controller >> block_plant
        fb = inner.feedback(
            [
                Wiring(
                    source_block="Room",
                    source_port="Energy Cost",
                    target_block="PID Controller",
                    target_port="Energy Cost",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ]
        )
        assert isinstance(fb, FeedbackLoop)

    def test_interface_preserved(self, block_controller, block_plant):
        inner = block_controller >> block_plant
        fb = inner.feedback(
            [
                Wiring(
                    source_block="Room",
                    source_port="Energy Cost",
                    target_block="PID Controller",
                    target_port="Energy Cost",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ]
        )
        assert fb.interface == inner.interface

    def test_flatten(self, block_controller, block_plant):
        inner = block_controller >> block_plant
        fb = inner.feedback([])
        assert len(fb.flatten()) == 2


# ── TemporalLoop ─────────────────────────────────────────────


class TestTemporalLoop:
    def test_loop(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop(
            [
                Wiring(
                    source_block="B",
                    source_port="Command",
                    target_block="A",
                    target_port="Temperature",
                )
            ],
            exit_condition="converged",
        )
        assert isinstance(loop, TemporalLoop)
        assert loop.exit_condition == "converged"

    def test_rejects_contravariant(self, block_a, block_b):
        inner = block_a >> block_b
        with pytest.raises(GDSTypeError):
            inner.loop(
                [
                    Wiring(
                        source_block="B",
                        source_port="Command",
                        target_block="A",
                        target_port="Temperature",
                        direction=FlowDirection.CONTRAVARIANT,
                    )
                ]
            )

    def test_flatten(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop([])
        assert len(loop.flatten()) == 2


# ── Wiring ───────────────────────────────────────────────────


class TestWiring:
    def test_creation(self):
        w = Wiring(
            source_block="A",
            source_port="X",
            target_block="B",
            target_port="Y",
        )
        assert w.source_block == "A"
        assert w.target_port == "Y"

    def test_default_direction(self):
        w = Wiring(source_block="A", source_port="X", target_block="B", target_port="Y")
        assert w.direction == FlowDirection.COVARIANT

    def test_frozen(self):
        w = Wiring(source_block="A", source_port="X", target_block="B", target_port="Y")
        with pytest.raises(ValidationError):
            w.source_block = "C"  # type: ignore[misc]


# ── Block Roles ──────────────────────────────────────────────


class TestBoundaryAction:
    def test_creation(self):
        b = BoundaryAction(
            name="User Input",
            interface=Interface(forward_out=(port("Action"),)),
        )
        assert b.kind == "boundary"
        assert b.name == "User Input"

    def test_enforces_no_forward_in(self):
        with pytest.raises(GDSCompositionError):
            BoundaryAction(
                name="Bad",
                interface=Interface(forward_in=(port("X"),)),
            )

    def test_options(self):
        b = BoundaryAction(
            name="User Input",
            interface=Interface(forward_out=(port("Action"),)),
            options=["option_a", "option_b"],
        )
        assert b.options == ["option_a", "option_b"]

    def test_is_atomic_block(self):
        b = BoundaryAction(
            name="User Input",
            interface=Interface(forward_out=(port("Action"),)),
        )
        assert isinstance(b, AtomicBlock)
        assert b.flatten() == [b]


class TestPolicy:
    def test_creation(self):
        p = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Decision"),),
            ),
        )
        assert p.kind == "policy"

    def test_options(self):
        p = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Decision"),),
            ),
            options=["greedy", "random"],
        )
        assert p.options == ["greedy", "random"]

    def test_params_used(self):
        p = Policy(
            name="Decide",
            params_used=["threshold"],
        )
        assert p.params_used == ["threshold"]


class TestMechanism:
    def test_creation(self):
        m = Mechanism(
            name="Update State",
            interface=Interface(forward_in=(port("Decision"),)),
            updates=[("Entity", "var")],
        )
        assert m.kind == "mechanism"
        assert m.updates == [("Entity", "var")]

    def test_enforces_no_backward(self):
        with pytest.raises(GDSCompositionError):
            Mechanism(
                name="Bad",
                interface=Interface(backward_in=(port("X"),)),
            )

    def test_enforces_no_backward_out(self):
        with pytest.raises(GDSCompositionError):
            Mechanism(
                name="Bad",
                interface=Interface(backward_out=(port("X"),)),
            )

    def test_is_atomic_block(self):
        m = Mechanism(name="Update")
        assert isinstance(m, AtomicBlock)


class TestControlAction:
    def test_creation(self):
        c = ControlAction(
            name="Monitor",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Control Signal"),),
            ),
        )
        assert c.kind == "control"

    def test_options(self):
        c = ControlAction(name="Monitor", options=["pid", "bang_bang"])
        assert c.options == ["pid", "bang_bang"]


class TestRoleComposition:
    def test_boundary_to_policy_to_mechanism(self):
        ba = BoundaryAction(
            name="Input",
            interface=Interface(forward_out=(port("Signal"),)),
        )
        pol = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Action"),),
            ),
        )
        mech = Mechanism(
            name="Update",
            interface=Interface(forward_in=(port("Action"),)),
            updates=[("Entity", "var")],
        )
        comp = ba >> pol >> mech
        flat = comp.flatten()
        assert len(flat) == 3
        assert flat[0].name == "Input"
        assert flat[2].name == "Update"

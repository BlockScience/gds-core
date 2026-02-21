"""Tests for the compiler: compile_system, auto-wiring, hierarchy extraction."""

import dataclasses

from gds.blocks.base import AtomicBlock
from gds.blocks.composition import Wiring
from gds.compiler.compile import (
    StructuralWiring,
    WiringOrigin,
    compile_system,
    extract_hierarchy,
    extract_wirings,
    flatten_blocks,
)
from gds.ir.models import BlockIR, CompositionType, FlowDirection
from gds.types.interface import Interface, port

# ── Basic compilation ────────────────────────────────────────


class TestCompileSystemBasic:
    def test_single_block(self):
        b = AtomicBlock(name="A", interface=Interface(forward_out=(port("X"),)))
        ir = compile_system("Test", b)
        assert ir.name == "Test"
        assert len(ir.blocks) == 1
        assert ir.blocks[0].name == "A"

    def test_two_stacked(self, block_a, block_b):
        comp = block_a >> block_b
        ir = compile_system("Test", comp)
        assert len(ir.blocks) == 2
        assert ir.blocks[0].name == "A"
        assert ir.blocks[1].name == "B"

    def test_names_preserved(self, block_a, block_b, block_c):
        comp = block_a >> block_b >> block_c
        ir = compile_system("Pipeline", comp)
        names = [b.name for b in ir.blocks]
        assert names == ["A", "B", "C"]

    def test_system_name(self, block_a):
        ir = compile_system("MySystem", block_a)
        assert ir.name == "MySystem"

    def test_source_set(self, block_a):
        ir = compile_system("Test", block_a, source="example.py")
        assert ir.source == "example.py"


# ── Auto-wiring ──────────────────────────────────────────────


class TestAutoWiring:
    def test_matching_tokens_wired(self, block_a, block_b):
        comp = block_a >> block_b
        ir = compile_system("Test", comp)
        assert len(ir.wirings) >= 1
        w = ir.wirings[0]
        assert w.source == "A"
        assert w.target == "B"

    def test_direction_is_covariant(self, block_a, block_b):
        comp = block_a >> block_b
        ir = compile_system("Test", comp)
        assert ir.wirings[0].direction == FlowDirection.COVARIANT

    def test_no_auto_wire_with_explicit(self, block_a, block_b):
        from gds.blocks.composition import StackComposition

        comp = StackComposition(
            name="explicit",
            first=block_a,
            second=block_b,
            wiring=[
                Wiring(
                    source_block="A",
                    source_port="Temperature",
                    target_block="B",
                    target_port="Temperature",
                )
            ],
        )
        ir = compile_system("Test", comp)
        # Should have the explicit wiring, not an auto-wire
        assert len(ir.wirings) >= 1

    def test_no_auto_wire_for_parallel(self, block_a, block_b):
        comp = block_a | block_b
        ir = compile_system("Test", comp)
        assert len(ir.wirings) == 0


# ── Explicit wiring ──────────────────────────────────────────


class TestExplicitWiring:
    def test_feedback_is_feedback(self, block_controller, block_plant):
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
        ir = compile_system("Thermostat", fb)
        feedback_wirings = [w for w in ir.wirings if w.is_feedback]
        assert len(feedback_wirings) >= 1

    def test_temporal_is_temporal(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop(
            [
                Wiring(
                    source_block="B",
                    source_port="Command",
                    target_block="A",
                    target_port="Temperature",
                )
            ]
        )
        ir = compile_system("Loop", loop)
        temporal_wirings = [w for w in ir.wirings if w.is_temporal]
        assert len(temporal_wirings) >= 1


# ── Default block compiler ───────────────────────────────────


class TestDefaultBlockCompiler:
    def test_signature_from_interface(self):
        b = AtomicBlock(
            name="A",
            interface=Interface(
                forward_in=(port("X"),),
                forward_out=(port("Y"),),
                backward_in=(port("R"),),
                backward_out=(port("S"),),
            ),
        )
        ir = compile_system("Test", b)
        sig = ir.blocks[0].signature
        assert sig[0] == "X"  # forward_in
        assert sig[1] == "Y"  # forward_out
        assert sig[2] == "R"  # backward_in
        assert sig[3] == "S"  # backward_out

    def test_empty_ports(self):
        b = AtomicBlock(name="A")
        ir = compile_system("Test", b)
        assert ir.blocks[0].signature == ("", "", "", "")

    def test_multi_port_joined(self):
        b = AtomicBlock(
            name="A",
            interface=Interface(
                forward_in=(port("X"), port("Y")),
            ),
        )
        ir = compile_system("Test", b)
        # Multi-port joined with " + "
        assert "+" in ir.blocks[0].signature[0] or "X" in ir.blocks[0].signature[0]


# ── Custom block compiler ────────────────────────────────────


class TestCustomBlockCompiler:
    def test_custom_callback(self, block_a):
        from gds.ir.models import BlockIR

        def custom_compiler(block):
            return BlockIR(
                name=block.name,
                block_type="custom",
                metadata={"custom_key": "custom_value"},
            )

        ir = compile_system("Test", block_a, block_compiler=custom_compiler)
        assert ir.blocks[0].block_type == "custom"
        assert ir.blocks[0].metadata["custom_key"] == "custom_value"


# ── Hierarchy extraction ─────────────────────────────────────


class TestHierarchyExtraction:
    def test_leaf_block(self, block_a):
        ir = compile_system("Test", block_a)
        assert ir.hierarchy is not None
        assert ir.hierarchy.block_name == "A"

    def test_sequential_group(self, block_a, block_b):
        comp = block_a >> block_b
        ir = compile_system("Test", comp)
        assert ir.hierarchy is not None
        assert ir.hierarchy.composition_type == CompositionType.SEQUENTIAL

    def test_parallel_group(self, block_a, block_b):
        comp = block_a | block_b
        ir = compile_system("Test", comp)
        assert ir.hierarchy is not None
        assert ir.hierarchy.composition_type == CompositionType.PARALLEL

    def test_feedback_group(self, block_controller, block_plant):
        inner = block_controller >> block_plant
        fb = inner.feedback([])
        ir = compile_system("Test", fb)
        assert ir.hierarchy is not None
        assert ir.hierarchy.composition_type == CompositionType.FEEDBACK

    def test_temporal_group(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop([])
        ir = compile_system("Test", loop)
        assert ir.hierarchy is not None
        assert ir.hierarchy.composition_type == CompositionType.TEMPORAL

    def test_chain_flattening(self, block_a, block_b, block_c):
        comp = block_a >> block_b >> block_c
        ir = compile_system("Test", comp)
        # After chain flattening, a>>b>>c should be a single sequential
        # node with 3 children, not nested binary tree
        h = ir.hierarchy
        assert h is not None
        assert h.composition_type == CompositionType.SEQUENTIAL
        assert len(h.children) == 3


# ── Pipeline decomposition: flatten_blocks ──────────────────


class TestFlattenBlocks:
    def test_default_compiler(self, block_a, block_b):
        from gds.compiler.compile import _default_block_compiler

        comp = block_a >> block_b
        blocks = flatten_blocks(comp, _default_block_compiler)
        assert len(blocks) == 2
        assert blocks[0].name == "A"
        assert blocks[1].name == "B"

    def test_custom_compiler(self, block_a, block_b):
        comp = block_a >> block_b
        results = flatten_blocks(comp, lambda b: {"custom_name": b.name.upper()})
        assert results == [{"custom_name": "A"}, {"custom_name": "B"}]

    def test_single_block(self, block_a):
        from gds.compiler.compile import _default_block_compiler

        blocks = flatten_blocks(block_a, _default_block_compiler)
        assert len(blocks) == 1
        assert blocks[0].name == "A"


# ── Pipeline decomposition: extract_wirings ─────────────────


class TestExtractWirings:
    def test_default_emitter(self, block_a, block_b):
        comp = block_a >> block_b
        wirings = extract_wirings(comp)
        assert len(wirings) >= 1
        w = wirings[0]
        assert w.source == "A"
        assert w.target == "B"
        assert w.direction == FlowDirection.COVARIANT

    def test_custom_emitter(self, block_a, block_b):
        comp = block_a >> block_b
        wirings = extract_wirings(comp, lambda sw: (sw.source_block, sw.target_block))
        assert len(wirings) >= 1
        assert wirings[0] == ("A", "B")

    def test_origin_auto(self, block_a, block_b):
        comp = block_a >> block_b
        origins: list[WiringOrigin] = []
        extract_wirings(comp, lambda sw: origins.append(sw.origin) or sw)
        assert WiringOrigin.AUTO in origins

    def test_origin_explicit(self, block_a, block_b):
        from gds.blocks.composition import StackComposition

        comp = StackComposition(
            name="explicit",
            first=block_a,
            second=block_b,
            wiring=[
                Wiring(
                    source_block="A",
                    source_port="Temperature",
                    target_block="B",
                    target_port="Temperature",
                )
            ],
        )
        origins: list[WiringOrigin] = []
        extract_wirings(comp, lambda sw: origins.append(sw.origin) or sw)
        assert WiringOrigin.EXPLICIT in origins

    def test_origin_feedback(self, block_controller, block_plant):
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
        origins: list[WiringOrigin] = []
        extract_wirings(fb, lambda sw: origins.append(sw.origin) or sw)
        assert WiringOrigin.FEEDBACK in origins

    def test_origin_temporal(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop(
            [
                Wiring(
                    source_block="B",
                    source_port="Command",
                    target_block="A",
                    target_port="Temperature",
                )
            ]
        )
        origins: list[WiringOrigin] = []
        extract_wirings(loop, lambda sw: origins.append(sw.origin) or sw)
        assert WiringOrigin.TEMPORAL in origins

    def test_no_wirings_for_parallel(self, block_a, block_b):
        comp = block_a | block_b
        wirings = extract_wirings(comp)
        assert len(wirings) == 0


# ── Pipeline decomposition: extract_hierarchy ───────────────


class TestExtractHierarchyPublic:
    def test_leaf_block(self, block_a):
        h = extract_hierarchy(block_a)
        assert h.block_name == "A"
        assert h.composition_type is None

    def test_sequential(self, block_a, block_b):
        comp = block_a >> block_b
        h = extract_hierarchy(comp)
        assert h.composition_type == CompositionType.SEQUENTIAL

    def test_chain_flattening(self, block_a, block_b, block_c):
        comp = block_a >> block_b >> block_c
        h = extract_hierarchy(comp)
        assert h.composition_type == CompositionType.SEQUENTIAL
        assert len(h.children) == 3

    def test_parallel(self, block_a, block_b):
        comp = block_a | block_b
        h = extract_hierarchy(comp)
        assert h.composition_type == CompositionType.PARALLEL

    def test_feedback(self, block_controller, block_plant):
        inner = block_controller >> block_plant
        fb = inner.feedback([])
        h = extract_hierarchy(fb)
        assert h.composition_type == CompositionType.FEEDBACK

    def test_temporal(self, block_a, block_b):
        inner = block_a >> block_b
        loop = inner.loop([])
        h = extract_hierarchy(loop)
        assert h.composition_type == CompositionType.TEMPORAL


# ── StructuralWiring ────────────────────────────────────────


class TestStructuralWiring:
    def test_frozen(self):
        sw = StructuralWiring(
            source_block="A",
            source_port="X",
            target_block="B",
            target_port="Y",
            direction=FlowDirection.COVARIANT,
            origin=WiringOrigin.AUTO,
        )
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            sw.source_block = "C"  # type: ignore[misc]

    def test_fields(self):
        sw = StructuralWiring(
            source_block="A",
            source_port="X",
            target_block="B",
            target_port="Y",
            direction=FlowDirection.CONTRAVARIANT,
            origin=WiringOrigin.FEEDBACK,
        )
        assert sw.source_block == "A"
        assert sw.source_port == "X"
        assert sw.target_block == "B"
        assert sw.target_port == "Y"
        assert sw.direction == FlowDirection.CONTRAVARIANT
        assert sw.origin == WiringOrigin.FEEDBACK


# ── Backwards compatibility ─────────────────────────────────


class TestCompileSystemBackwardsCompatible:
    def test_old_signature_still_works(self, block_a, block_b):
        """compile_system with only block_compiler (no wiring_emitter) works."""
        comp = block_a >> block_b

        def custom_bc(block: AtomicBlock) -> BlockIR:
            return BlockIR(name=block.name, block_type="compat")

        ir = compile_system("Test", comp, block_compiler=custom_bc)
        assert all(b.block_type == "compat" for b in ir.blocks)
        assert len(ir.wirings) >= 1
        assert ir.hierarchy is not None

    def test_wiring_emitter_param(self, block_a, block_b):
        """compile_system accepts wiring_emitter and uses it."""
        from gds.ir.models import WiringIR

        comp = block_a >> block_b
        ir = compile_system(
            "Test",
            comp,
            wiring_emitter=lambda sw: WiringIR(
                source=sw.source_block,
                target=sw.target_block,
                label=sw.source_port,
                direction=sw.direction,
                category="custom",
            ),
        )
        assert len(ir.wirings) >= 1
        assert ir.wirings[0].category == "custom"

    def test_wiring_ir_category_default(self, block_a, block_b):
        """Default emitter sets category='dataflow'."""
        comp = block_a >> block_b
        ir = compile_system("Test", comp)
        for w in ir.wirings:
            assert w.category == "dataflow"

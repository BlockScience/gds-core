"""Tests for IR models and serialization."""

import json

from gds.ir.models import (
    BlockIR,
    CompositionType,
    FlowDirection,
    HierarchyNodeIR,
    SystemIR,
    WiringIR,
)
from gds.ir.serialization import IRDocument, IRMetadata, load_ir, save_ir

# ── BlockIR ──────────────────────────────────────────────────


class TestBlockIR:
    def test_creation(self):
        b = BlockIR(name="A")
        assert b.name == "A"
        assert b.signature == ("", "", "", "")
        assert b.block_type == ""
        assert b.metadata == {}

    def test_with_signature(self):
        b = BlockIR(name="A", signature=("X", "Y", "R", "S"))
        assert b.signature == ("X", "Y", "R", "S")

    def test_json_round_trip(self):
        b = BlockIR(name="A", signature=("X", "Y", "", ""), color_code=2)
        data = b.model_dump_json()
        b2 = BlockIR.model_validate_json(data)
        assert b2.name == b.name
        assert b2.signature == b.signature
        assert b2.color_code == 2

    def test_metadata(self):
        b = BlockIR(name="A", metadata={"role": "mechanism"})
        assert b.metadata["role"] == "mechanism"


# ── WiringIR ─────────────────────────────────────────────────


class TestWiringIR:
    def test_creation(self):
        w = WiringIR(
            source="A", target="B", label="signal", direction=FlowDirection.COVARIANT
        )
        assert w.source == "A"
        assert w.is_feedback is False
        assert w.is_temporal is False

    def test_feedback_flag(self):
        w = WiringIR(
            source="A",
            target="B",
            label="cost",
            direction=FlowDirection.CONTRAVARIANT,
            is_feedback=True,
        )
        assert w.is_feedback is True

    def test_temporal_flag(self):
        w = WiringIR(
            source="A",
            target="B",
            label="state",
            direction=FlowDirection.COVARIANT,
            is_temporal=True,
        )
        assert w.is_temporal is True

    def test_json_round_trip(self):
        w = WiringIR(
            source="A", target="B", label="x", direction=FlowDirection.COVARIANT
        )
        data = w.model_dump_json()
        w2 = WiringIR.model_validate_json(data)
        assert w2.source == w.source
        assert w2.direction == w.direction


# ── HierarchyNodeIR ──────────────────────────────────────────


class TestHierarchyNodeIR:
    def test_leaf_node(self):
        node = HierarchyNodeIR(id="a", name="A", block_name="A")
        assert node.block_name == "A"
        assert node.children == []

    def test_group_node(self):
        child1 = HierarchyNodeIR(id="a", name="A", block_name="A")
        child2 = HierarchyNodeIR(id="b", name="B", block_name="B")
        group = HierarchyNodeIR(
            id="seq_1",
            name="A >> B",
            composition_type=CompositionType.SEQUENTIAL,
            children=[child1, child2],
        )
        assert len(group.children) == 2
        assert group.composition_type == CompositionType.SEQUENTIAL

    def test_json_round_trip(self):
        node = HierarchyNodeIR(
            id="a",
            name="A",
            block_name="A",
            exit_condition="done",
        )
        data = node.model_dump_json()
        node2 = HierarchyNodeIR.model_validate_json(data)
        assert node2.exit_condition == "done"


# ── SystemIR ─────────────────────────────────────────────────


class TestSystemIR:
    def test_creation(self):
        sys = SystemIR(name="Test")
        assert sys.name == "Test"
        assert sys.blocks == []
        assert sys.wirings == []

    def test_with_blocks_and_wirings(self, sample_system_ir):
        assert len(sample_system_ir.blocks) == 2
        assert len(sample_system_ir.wirings) == 1

    def test_json_round_trip(self, sample_system_ir):
        data = sample_system_ir.model_dump_json()
        sys2 = SystemIR.model_validate_json(data)
        assert sys2.name == sample_system_ir.name
        assert len(sys2.blocks) == 2
        assert len(sys2.wirings) == 1

    def test_defaults(self):
        sys = SystemIR(name="Test")
        assert sys.composition_type == CompositionType.SEQUENTIAL
        assert sys.hierarchy is None
        assert sys.source == ""


# ── IRDocument ───────────────────────────────────────────────


class TestIRDocument:
    def test_creation(self, sample_system_ir):
        doc = IRDocument(
            systems=[sample_system_ir],
            metadata=IRMetadata(),
        )
        assert len(doc.systems) == 1

    def test_json_round_trip(self, sample_system_ir):
        doc = IRDocument(
            systems=[sample_system_ir],
            metadata=IRMetadata(version="0.1.0"),
        )
        data = doc.model_dump_json()
        doc2 = IRDocument.model_validate_json(data)
        assert doc2.metadata.version == "0.1.0"
        assert len(doc2.systems) == 1


# ── save_ir / load_ir ────────────────────────────────────────


class TestSaveLoadIR:
    def test_save_and_load(self, tmp_path, sample_system_ir):
        path = tmp_path / "test_ir.json"
        doc = IRDocument(
            systems=[sample_system_ir],
            metadata=IRMetadata(),
        )
        save_ir(doc, path)
        loaded = load_ir(path)
        assert loaded.systems[0].name == "Sample"
        assert len(loaded.systems[0].blocks) == 2

    def test_file_is_valid_json(self, tmp_path, sample_system_ir):
        path = tmp_path / "test_ir.json"
        doc = IRDocument(
            systems=[sample_system_ir],
            metadata=IRMetadata(),
        )
        save_ir(doc, path)
        data = json.loads(path.read_text())
        assert "systems" in data
        assert "metadata" in data

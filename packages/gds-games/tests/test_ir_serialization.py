"""Tests for IR document serialization."""

from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    FlowIR,
    FlowType,
    GameType,
    InputIR,
    InputType,
    OpenGameIR,
    PatternIR,
)
from ogs.ir.serialization import IRDocument, IRMetadata, load_ir, save_ir


def _make_sample_document() -> IRDocument:
    pattern = PatternIR(
        name="Reactive Decision Pattern",
        games=[
            OpenGameIR(
                name="Context Builder",
                game_type=GameType.FUNCTION_COVARIANT,
                signature=("Sensor+Resources", "Observation", "", ""),
                color_code=1,
            ),
            OpenGameIR(
                name="Reactive Decision",
                game_type=GameType.DECISION,
                signature=("Observation+Policy", "Action", "Outcome", "Experience"),
                color_code=1,
            ),
        ],
        flows=[
            FlowIR(
                source="Context Builder",
                target="Reactive Decision",
                label="Observation, Context",
                flow_type=FlowType.OBSERVATION,
                direction=FlowDirection.COVARIANT,
            ),
        ],
        inputs=[
            InputIR(name="Sensor Input", input_type=InputType.SENSOR, shape="pill"),
        ],
        composition_type=CompositionType.FEEDBACK,
        source_canvas="Reactive Decision Pattern.canvas",
    )
    return IRDocument(
        patterns=[pattern],
        metadata=IRMetadata(source_canvases=["Reactive Decision Pattern.canvas"]),
    )


def test_save_and_load(tmp_path):
    doc = _make_sample_document()
    path = tmp_path / "ir.json"

    save_ir(doc, path)
    assert path.exists()

    loaded = load_ir(path)
    assert loaded.version == "1.0"
    assert len(loaded.patterns) == 1
    assert loaded.patterns[0].name == "Reactive Decision Pattern"
    assert len(loaded.patterns[0].games) == 2
    assert len(loaded.patterns[0].flows) == 1
    assert loaded.metadata.parser_version == "0.1.0"


def test_json_content_structure(tmp_path):
    import json

    doc = _make_sample_document()
    path = tmp_path / "ir.json"
    save_ir(doc, path)

    data = json.loads(path.read_text())
    assert "version" in data
    assert "patterns" in data
    assert "metadata" in data
    assert data["version"] == "1.0"
    assert len(data["patterns"]) == 1
    assert data["patterns"][0]["name"] == "Reactive Decision Pattern"


def test_round_trip_preserves_data(tmp_path):
    doc = _make_sample_document()
    path = tmp_path / "ir.json"

    save_ir(doc, path)
    loaded = load_ir(path)

    original_pattern = doc.patterns[0]
    loaded_pattern = loaded.patterns[0]

    assert loaded_pattern.name == original_pattern.name
    assert len(loaded_pattern.games) == len(original_pattern.games)
    assert loaded_pattern.games[0].signature == original_pattern.games[0].signature
    assert loaded_pattern.composition_type == original_pattern.composition_type

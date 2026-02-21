"""Tests for spec serialization."""

import json

import pytest

from gds.blocks.roles import Mechanism, Policy
from gds.serialize import spec_to_dict, spec_to_json
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef


@pytest.fixture
def serializable_spec():
    t = TypeDef(name="Prob", python_type=float)
    s = Space(name="Signal", fields={"prob": t})
    e = Entity(
        name="Agent",
        variables={"score": StateVariable(name="score", typedef=t, symbol="s")},
    )
    pol = Policy(
        name="Decide",
        interface=Interface(
            forward_in=(port("Input"),),
            forward_out=(port("Output"),),
        ),
        params_used=["threshold"],
        options=["greedy", "random"],
    )
    mech = Mechanism(
        name="Update",
        interface=Interface(forward_in=(port("Output"),)),
        updates=[("Agent", "score")],
        params_used=["rate"],
    )

    spec = GDSSpec(name="Test Spec", description="A test specification")
    spec.register_type(t)
    spec.register_space(s)
    spec.register_entity(e)
    spec.register_block(pol)
    spec.register_block(mech)
    spec.register_parameter("threshold", t)
    spec.register_parameter("rate", t)
    spec.register_wiring(
        SpecWiring(
            name="Main Flow",
            block_names=["Decide", "Update"],
            wires=[Wire(source="Decide", target="Update", space="Signal")],
            description="Main data flow",
        )
    )
    return spec


class TestSpecToDict:
    def test_returns_dict(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert isinstance(d, dict)

    def test_contains_all_sections(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "name" in d
        assert "types" in d
        assert "spaces" in d
        assert "entities" in d
        assert "blocks" in d
        assert "wirings" in d
        assert "parameters" in d

    def test_type_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "Prob" in d["types"]
        assert d["types"]["Prob"]["python_type"] == "float"

    def test_space_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "Signal" in d["spaces"]
        assert d["spaces"]["Signal"]["schema"]["prob"] == "Prob"

    def test_entity_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "Agent" in d["entities"]
        vars_ = d["entities"]["Agent"]["variables"]
        assert "score" in vars_
        assert vars_["score"]["type"] == "Prob"
        assert vars_["score"]["symbol"] == "s"

    def test_block_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "Decide" in d["blocks"]
        assert d["blocks"]["Decide"]["kind"] == "policy"
        assert d["blocks"]["Decide"]["options"] == ["greedy", "random"]
        assert "Update" in d["blocks"]
        assert d["blocks"]["Update"]["kind"] == "mechanism"
        assert d["blocks"]["Update"]["updates"] == [["Agent", "score"]]

    def test_wiring_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "Main Flow" in d["wirings"]
        w = d["wirings"]["Main Flow"]
        assert w["blocks"] == ["Decide", "Update"]
        assert len(w["wires"]) == 1
        assert w["wires"][0]["source"] == "Decide"

    def test_parameter_serialization(self, serializable_spec):
        d = spec_to_dict(serializable_spec)
        assert "threshold" in d["parameters"]
        assert d["parameters"]["threshold"]["python_type"] == "float"


class TestSpecToJson:
    def test_returns_string(self, serializable_spec):
        j = spec_to_json(serializable_spec)
        assert isinstance(j, str)

    def test_valid_json(self, serializable_spec):
        j = spec_to_json(serializable_spec)
        data = json.loads(j)
        assert data["name"] == "Test Spec"

    def test_custom_indent(self, serializable_spec):
        j = spec_to_json(serializable_spec, indent=4)
        # 4-space indent should produce longer string than 2-space
        j2 = spec_to_json(serializable_spec, indent=2)
        assert len(j) > len(j2)

    def test_round_trip_preserves_structure(self, serializable_spec):
        j = spec_to_json(serializable_spec)
        data = json.loads(j)
        assert len(data["blocks"]) == 2
        assert len(data["wirings"]) == 1
        assert data["description"] == "A test specification"

"""Tests for GDSSpec registration and validation."""

import pytest
from pydantic import ValidationError

from gds.blocks.base import AtomicBlock
from gds.blocks.roles import Mechanism, Policy
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.typedef import Probability, TypeDef

# ── Registration ─────────────────────────────────────────────


class TestGDSSpecRegistration:
    def test_register_type(self):
        spec = GDSSpec(name="Test")
        t = TypeDef(name="Prob", python_type=float)
        spec.register_type(t)
        assert "Prob" in spec.types

    def test_register_space(self):
        spec = GDSSpec(name="Test")
        s = Space(name="Signal", fields={"x": Probability})
        spec.register_space(s)
        assert "Signal" in spec.spaces

    def test_register_entity(self):
        spec = GDSSpec(name="Test")
        t = TypeDef(name="Pop", python_type=int)
        e = Entity(
            name="Agent",
            variables={"count": StateVariable(name="count", typedef=t)},
        )
        spec.register_entity(e)
        assert "Agent" in spec.entities

    def test_register_block(self):
        spec = GDSSpec(name="Test")
        b = AtomicBlock(name="A")
        spec.register_block(b)
        assert "A" in spec.blocks

    def test_register_wiring(self):
        spec = GDSSpec(name="Test")
        w = SpecWiring(name="Flow", block_names=["A", "B"])
        spec.register_wiring(w)
        assert "Flow" in spec.wirings

    def test_register_parameter(self):
        spec = GDSSpec(name="Test")
        t = TypeDef(name="Rate", python_type=float)
        spec.register_parameter("growth_rate", t)
        assert "growth_rate" in spec.parameters

    @pytest.mark.parametrize(
        "register_method, make_item",
        [
            ("register_type", lambda: TypeDef(name="Prob", python_type=float)),
            ("register_space", lambda: Space(name="Signal")),
            ("register_entity", lambda: Entity(name="Agent")),
            ("register_block", lambda: AtomicBlock(name="A")),
            ("register_wiring", lambda: SpecWiring(name="Flow")),
        ],
    )
    def test_duplicate_raises(self, register_method, make_item):
        spec = GDSSpec(name="Test")
        item = make_item()
        getattr(spec, register_method)(item)
        with pytest.raises(ValueError, match="already registered"):
            getattr(spec, register_method)(item)

    def test_duplicate_parameter_raises(self):
        spec = GDSSpec(name="Test")
        t = TypeDef(name="Rate", python_type=float)
        spec.register_parameter("rate", t)
        with pytest.raises(ValueError, match="already registered"):
            spec.register_parameter("rate", t)


# ── Chaining ─────────────────────────────────────────────────


class TestGDSSpecChaining:
    def test_chainable_registration(self):
        t = TypeDef(name="Prob", python_type=float)
        s = Space(name="Signal", fields={"x": t})
        spec = GDSSpec(name="Test")
        result = spec.register_type(t).register_space(s)
        assert result is spec
        assert "Prob" in spec.types
        assert "Signal" in spec.spaces


# ── Validation ───────────────────────────────────────────────


class TestGDSSpecValidation:
    def test_valid_spec_no_errors(self, sample_spec):
        errors = sample_spec.validate_spec()
        assert errors == []

    def test_unregistered_space_type(self):
        t = TypeDef(name="UnregisteredType", python_type=float)
        s = Space(name="Signal", fields={"x": t})
        spec = GDSSpec(name="Test")
        spec.register_space(s)
        # t is NOT registered as a type
        errors = spec.validate_spec()
        assert any("unregistered type" in e.lower() for e in errors)

    def test_unregistered_wiring_block(self):
        spec = GDSSpec(name="Test")
        spec.register_wiring(SpecWiring(name="Flow", block_names=["NonExistent"]))
        errors = spec.validate_spec()
        assert any("unregistered block" in e.lower() for e in errors)

    def test_invalid_mechanism_entity(self):
        spec = GDSSpec(name="Test")
        m = Mechanism(
            name="Bad Mech",
            updates=[("NonExistentEntity", "var")],
        )
        spec.register_block(m)
        errors = spec.validate_spec()
        assert any("unknown entity" in e.lower() for e in errors)

    def test_invalid_mechanism_variable(self):
        t = TypeDef(name="Pop", python_type=int)
        e = Entity(
            name="Agent",
            variables={"count": StateVariable(name="count", typedef=t)},
        )
        m = Mechanism(
            name="Bad Mech",
            updates=[("Agent", "nonexistent_var")],
        )
        spec = GDSSpec(name="Test")
        spec.register_entity(e)
        spec.register_block(m)
        errors = spec.validate_spec()
        assert any("unknown variable" in e.lower() for e in errors)

    def test_invalid_param_reference(self):
        p = Policy(
            name="Decide",
            params_used=["unregistered_param"],
        )
        spec = GDSSpec(name="Test")
        spec.register_block(p)
        errors = spec.validate_spec()
        assert any("unregistered parameter" in e.lower() for e in errors)

    def test_wiring_wire_invalid_source(self):
        spec = GDSSpec(name="Test")
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                wires=[Wire(source="NonExistent", target="Also NonExistent")],
            )
        )
        errors = spec.validate_spec()
        assert len(errors) >= 2  # both source and target

    def test_wiring_wire_invalid_space(self):
        b = AtomicBlock(name="A")
        spec = GDSSpec(name="Test")
        spec.register_block(b)
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                wires=[Wire(source="A", target="A", space="UnregisteredSpace")],
            )
        )
        errors = spec.validate_spec()
        assert any("unregistered space" in e.lower() for e in errors)


# ── Wire and SpecWiring ──────────────────────────────────────


class TestWire:
    def test_creation(self):
        w = Wire(source="A", target="B")
        assert w.source == "A"
        assert w.target == "B"
        assert w.space == ""
        assert w.optional is False

    def test_with_space(self):
        w = Wire(source="A", target="B", space="Signal")
        assert w.space == "Signal"

    def test_frozen(self):
        w = Wire(source="A", target="B")
        with pytest.raises(ValidationError):
            w.source = "C"  # type: ignore[misc]


class TestSpecWiring:
    def test_creation(self):
        sw = SpecWiring(name="Flow", block_names=["A", "B"])
        assert sw.name == "Flow"
        assert sw.block_names == ["A", "B"]

    def test_with_wires(self):
        sw = SpecWiring(
            name="Flow",
            block_names=["A", "B"],
            wires=[Wire(source="A", target="B")],
        )
        assert len(sw.wires) == 1

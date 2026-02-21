"""Tests for all GDS v0.2 features.

Covers:
- ParameterDef and ParameterSchema
- Canonical projection (CanonicalGDS, project_canonical)
- Verification checks SC-005, SC-006, SC-007
- Tagged mixin on Block, Entity, GDSSpec
- Backward compatibility
"""

import pytest
from pydantic import ValidationError

from gds.blocks.base import AtomicBlock
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.canonical import CanonicalGDS, project_canonical
from gds.parameters import ParameterDef, ParameterSchema
from gds.spec import GDSSpec
from gds.state import Entity, StateVariable
from gds.tagged import Tagged
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_parameter_references,
)

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def float_type():
    return TypeDef(name="Float", python_type=float)


@pytest.fixture
def int_type():
    return TypeDef(name="Int", python_type=int)


@pytest.fixture
def prob_type():
    return TypeDef(
        name="Probability",
        python_type=float,
        constraint=lambda x: 0.0 <= x <= 1.0,
    )


@pytest.fixture
def basic_spec(float_type):
    """A spec with one entity, one mechanism, and one policy."""
    spec = GDSSpec(name="Basic", description="basic test spec")
    spec.register_type(float_type)

    entity = Entity(
        name="Agent",
        variables={"balance": StateVariable(name="balance", typedef=float_type)},
    )
    spec.register_entity(entity)

    policy = Policy(
        name="decide",
        interface=Interface(
            forward_in=(port("state"),),
            forward_out=(port("action"),),
        ),
    )
    spec.register_block(policy)

    mech = Mechanism(
        name="update_balance",
        interface=Interface(forward_in=(port("action"),), forward_out=()),
        updates=[("Agent", "balance")],
    )
    spec.register_block(mech)

    return spec


# ══════════════════════════════════════════════════════════════
# ParameterDef and ParameterSchema
# ══════════════════════════════════════════════════════════════


class TestParameterDef:
    def test_basic_creation(self, float_type):
        p = ParameterDef(name="alpha", typedef=float_type)
        assert p.name == "alpha"
        assert p.typedef is float_type
        assert p.description == ""
        assert p.bounds is None

    def test_with_description_and_bounds(self, float_type):
        p = ParameterDef(
            name="rate",
            typedef=float_type,
            description="Growth rate",
            bounds=(0.0, 1.0),
        )
        assert p.description == "Growth rate"
        assert p.bounds == (0.0, 1.0)

    def test_frozen(self, float_type):
        p = ParameterDef(name="alpha", typedef=float_type)
        with pytest.raises(ValidationError):
            p.name = "beta"  # type: ignore[misc]

    def test_check_value_passes(self, prob_type):
        p = ParameterDef(name="rate", typedef=prob_type, bounds=(0.0, 1.0))
        assert p.check_value(0.5) is True

    def test_check_value_fails_type(self, prob_type):
        p = ParameterDef(name="rate", typedef=prob_type, bounds=(0.0, 1.0))
        assert p.check_value(-0.1) is False

    def test_check_value_fails_bounds(self, float_type):
        p = ParameterDef(name="rate", typedef=float_type, bounds=(0.0, 1.0))
        assert p.check_value(1.5) is False

    def test_check_value_no_bounds(self, float_type):
        p = ParameterDef(name="rate", typedef=float_type)
        assert p.check_value(999.0) is True


class TestParameterSchema:
    def test_empty_schema(self):
        schema = ParameterSchema()
        assert len(schema) == 0
        assert schema.names() == set()

    def test_add_returns_new_instance(self, float_type):
        schema = ParameterSchema()
        p = ParameterDef(name="alpha", typedef=float_type)
        new_schema = schema.add(p)
        assert len(schema) == 0  # original unchanged
        assert len(new_schema) == 1

    def test_add_multiple(self, float_type, int_type):
        schema = (
            ParameterSchema()
            .add(ParameterDef(name="alpha", typedef=float_type))
            .add(ParameterDef(name="n", typedef=int_type))
        )
        assert schema.names() == {"alpha", "n"}
        assert len(schema) == 2

    def test_add_duplicate_raises(self, float_type):
        schema = ParameterSchema().add(ParameterDef(name="alpha", typedef=float_type))
        with pytest.raises(ValueError, match="already registered"):
            schema.add(ParameterDef(name="alpha", typedef=float_type))

    def test_get(self, float_type):
        p = ParameterDef(name="alpha", typedef=float_type)
        schema = ParameterSchema().add(p)
        assert schema.get("alpha") is p

    def test_get_missing_raises(self):
        schema = ParameterSchema()
        with pytest.raises(KeyError):
            schema.get("nonexistent")

    def test_contains(self, float_type):
        schema = ParameterSchema().add(ParameterDef(name="alpha", typedef=float_type))
        assert "alpha" in schema
        assert "beta" not in schema

    def test_validate_references_valid(self, float_type):
        schema = ParameterSchema().add(ParameterDef(name="alpha", typedef=float_type))
        errors = schema.validate_references({"alpha"})
        assert errors == []

    def test_validate_references_missing(self, float_type):
        schema = ParameterSchema().add(ParameterDef(name="alpha", typedef=float_type))
        errors = schema.validate_references({"alpha", "beta"})
        assert len(errors) == 1
        assert "beta" in errors[0]

    def test_frozen(self, float_type):
        schema = ParameterSchema()
        with pytest.raises(ValidationError):
            schema.parameters = {"x": ParameterDef(name="x", typedef=float_type)}  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════
# GDSSpec Parameter Integration
# ══════════════════════════════════════════════════════════════


class TestSpecParameterIntegration:
    def test_register_parameter_def(self, float_type):
        spec = GDSSpec(name="Test")
        p = ParameterDef(name="alpha", typedef=float_type, description="Learning rate")
        spec.register_parameter(p)
        assert "alpha" in spec.parameter_schema
        assert spec.parameter_schema.get("alpha").description == "Learning rate"

    def test_register_parameter_legacy(self, float_type):
        spec = GDSSpec(name="Test")
        spec.register_parameter("alpha", float_type)
        assert "alpha" in spec.parameter_schema
        assert "alpha" in spec.parameters  # legacy property

    def test_legacy_parameters_property(self, float_type, int_type):
        spec = GDSSpec(name="Test")
        spec.register_parameter("alpha", float_type)
        spec.register_parameter("n", int_type)
        params = spec.parameters
        assert params["alpha"] is float_type
        assert params["n"] is int_type

    def test_register_parameter_string_without_typedef_raises(self):
        spec = GDSSpec(name="Test")
        with pytest.raises(ValueError, match="typedef is required"):
            spec.register_parameter("alpha")

    def test_chainable_registration(self, float_type, int_type):
        spec = GDSSpec(name="Test")
        result = spec.register_parameter("a", float_type).register_parameter(
            "b", int_type
        )
        assert result is spec
        assert len(spec.parameter_schema) == 2

    def test_default_empty_schema(self):
        spec = GDSSpec(name="Test")
        assert len(spec.parameter_schema) == 0
        assert spec.parameters == {}


# ══════════════════════════════════════════════════════════════
# Canonical Projection
# ══════════════════════════════════════════════════════════════


class TestCanonicalGDS:
    def test_empty_canonical(self):
        c = CanonicalGDS()
        assert c.state_variables == ()
        assert c.mechanism_blocks == ()
        assert c.policy_blocks == ()
        assert c.boundary_blocks == ()
        assert c.control_blocks == ()
        assert c.input_ports == ()
        assert c.decision_ports == ()
        assert c.update_map == ()

    def test_frozen(self):
        c = CanonicalGDS()
        with pytest.raises(ValidationError):
            c.state_variables = (("x", "y"),)  # type: ignore[misc]

    def test_formula_without_params(self):
        c = CanonicalGDS()
        assert c.formula() == "h : X → X  (h = f ∘ g)"

    def test_formula_with_params(self, float_type):
        schema = ParameterSchema().add(ParameterDef(name="a", typedef=float_type))
        c = CanonicalGDS(parameter_schema=schema)
        assert "θ" in c.formula()
        assert "Θ" in c.formula()

    def test_has_parameters(self, float_type):
        c_empty = CanonicalGDS()
        assert c_empty.has_parameters is False

        schema = ParameterSchema().add(ParameterDef(name="a", typedef=float_type))
        c_param = CanonicalGDS(parameter_schema=schema)
        assert c_param.has_parameters is True


class TestProjectCanonical:
    def test_empty_spec(self):
        spec = GDSSpec(name="Empty")
        canonical = project_canonical(spec)
        assert canonical.state_variables == ()
        assert canonical.mechanism_blocks == ()
        assert canonical.policy_blocks == ()

    def test_state_variables(self, float_type):
        spec = GDSSpec(name="Test")
        entity = Entity(
            name="Agent",
            variables={
                "x": StateVariable(name="x", typedef=float_type),
                "y": StateVariable(name="y", typedef=float_type),
            },
        )
        spec.register_entity(entity)
        canonical = project_canonical(spec)
        assert ("Agent", "x") in canonical.state_variables
        assert ("Agent", "y") in canonical.state_variables
        assert len(canonical.state_variables) == 2

    def test_block_classification(self, basic_spec):
        canonical = project_canonical(basic_spec)
        assert "decide" in canonical.policy_blocks
        assert "update_balance" in canonical.mechanism_blocks
        assert len(canonical.boundary_blocks) == 0
        assert len(canonical.control_blocks) == 0

    def test_boundary_action_ports(self, float_type):
        spec = GDSSpec(name="Test")
        ba = BoundaryAction(
            name="sensor",
            interface=Interface(forward_out=(port("reading"),)),
        )
        spec.register_block(ba)
        canonical = project_canonical(spec)
        assert ("sensor", "reading") in canonical.input_ports
        assert "sensor" in canonical.boundary_blocks

    def test_policy_decision_ports(self, float_type):
        spec = GDSSpec(name="Test")
        p = Policy(
            name="decide",
            interface=Interface(
                forward_in=(port("state"),),
                forward_out=(port("action"),),
            ),
        )
        spec.register_block(p)
        canonical = project_canonical(spec)
        assert ("decide", "action") in canonical.decision_ports
        assert "decide" in canonical.policy_blocks

    def test_control_action_classification(self):
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="governance",
            interface=Interface(forward_out=(port("config"),)),
        )
        spec.register_block(ca)
        canonical = project_canonical(spec)
        assert "governance" in canonical.control_blocks

    def test_mechanism_update_map(self, float_type):
        spec = GDSSpec(name="Test")
        entity = Entity(
            name="Agent",
            variables={"balance": StateVariable(name="balance", typedef=float_type)},
        )
        spec.register_entity(entity)
        mech = Mechanism(
            name="transfer",
            interface=Interface(forward_in=(port("amount"),), forward_out=()),
            updates=[("Agent", "balance")],
        )
        spec.register_block(mech)
        canonical = project_canonical(spec)
        assert len(canonical.update_map) == 1
        name, updates = canonical.update_map[0]
        assert name == "transfer"
        assert ("Agent", "balance") in updates

    def test_parameter_schema_passed_through(self, float_type):
        spec = GDSSpec(name="Test")
        spec.register_parameter("alpha", float_type)
        canonical = project_canonical(spec)
        assert canonical.has_parameters is True
        assert "alpha" in canonical.parameter_schema

    def test_deterministic(self, basic_spec):
        c1 = project_canonical(basic_spec)
        c2 = project_canonical(basic_spec)
        assert c1 == c2


# ══════════════════════════════════════════════════════════════
# Verification: SC-005 (Parameter References)
# ══════════════════════════════════════════════════════════════


class TestCheckParameterReferences:
    def test_all_resolved(self, float_type):
        spec = GDSSpec(name="Test")
        spec.register_parameter("alpha", float_type)
        mech = Mechanism(
            name="update",
            updates=[("Agent", "x")],
            params_used=["alpha"],
        )
        spec.register_block(mech)
        findings = check_parameter_references(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1
        assert passed[0].check_id == "SC-005"

    def test_unresolved_reference(self, float_type):
        spec = GDSSpec(name="Test")
        mech = Mechanism(
            name="update",
            updates=[("Agent", "x")],
            params_used=["nonexistent"],
        )
        spec.register_block(mech)
        findings = check_parameter_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert failed[0].severity == Severity.ERROR
        assert "nonexistent" in failed[0].message

    def test_no_params_used_passes(self):
        spec = GDSSpec(name="Test")
        mech = Mechanism(name="update", updates=[("Agent", "x")])
        spec.register_block(mech)
        findings = check_parameter_references(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_policy_params_checked(self, float_type):
        spec = GDSSpec(name="Test")
        policy = Policy(name="decide", params_used=["missing_param"])
        spec.register_block(policy)
        findings = check_parameter_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1


# ══════════════════════════════════════════════════════════════
# Verification: SC-006, SC-007 (Canonical Wellformedness)
# ══════════════════════════════════════════════════════════════


class TestCheckCanonicalWellformedness:
    def test_well_formed(self, basic_spec):
        findings = check_canonical_wellformedness(basic_spec)
        sc006 = [f for f in findings if f.check_id == "SC-006"]
        sc007 = [f for f in findings if f.check_id == "SC-007"]
        assert all(f.passed for f in sc006)
        assert all(f.passed for f in sc007)

    def test_empty_mechanisms_warns(self, float_type):
        spec = GDSSpec(name="Test")
        entity = Entity(
            name="Agent",
            variables={"x": StateVariable(name="x", typedef=float_type)},
        )
        spec.register_entity(entity)
        # No mechanisms
        findings = check_canonical_wellformedness(spec)
        sc006 = [f for f in findings if f.check_id == "SC-006"]
        assert len(sc006) == 1
        assert not sc006[0].passed
        assert sc006[0].severity == Severity.WARNING

    def test_empty_state_space_warns(self):
        spec = GDSSpec(name="Test")
        mech = Mechanism(name="update", updates=[("Agent", "x")])
        spec.register_block(mech)
        # No entities
        findings = check_canonical_wellformedness(spec)
        sc007 = [f for f in findings if f.check_id == "SC-007"]
        assert len(sc007) == 1
        assert not sc007[0].passed
        assert sc007[0].severity == Severity.WARNING

    def test_both_empty_warns_both(self):
        spec = GDSSpec(name="Empty")
        findings = check_canonical_wellformedness(spec)
        failed = [f for f in findings if not f.passed]
        check_ids = {f.check_id for f in failed}
        assert "SC-006" in check_ids
        assert "SC-007" in check_ids

    def test_mechanism_count_in_message(self, basic_spec):
        findings = check_canonical_wellformedness(basic_spec)
        sc006 = [f for f in findings if f.check_id == "SC-006" and f.passed]
        assert "1 mechanism" in sc006[0].message


# ══════════════════════════════════════════════════════════════
# Tagged Mixin
# ══════════════════════════════════════════════════════════════


class TestTaggedMixin:
    def test_default_empty_tags(self):
        block = AtomicBlock(name="A")
        assert block.tags == {}

    def test_with_tag_returns_new_instance(self):
        block = AtomicBlock(name="A")
        tagged = block.with_tag("role", "sensor")
        assert tagged.tags == {"role": "sensor"}
        assert block.tags == {}  # original unchanged
        assert tagged is not block

    def test_with_tags_multiple(self):
        block = AtomicBlock(name="A")
        tagged = block.with_tags(role="sensor", loop="outer")
        assert tagged.tags == {"role": "sensor", "loop": "outer"}

    def test_with_tag_preserves_type(self):
        mech = Mechanism(name="M", updates=[("A", "x")])
        tagged = mech.with_tag("subsystem", "core")
        assert isinstance(tagged, Mechanism)
        assert tagged.updates == [("A", "x")]

    def test_has_tag_exists(self):
        block = AtomicBlock(name="A").with_tag("role", "sensor")
        assert block.has_tag("role") is True
        assert block.has_tag("missing") is False

    def test_has_tag_with_value(self):
        block = AtomicBlock(name="A").with_tag("role", "sensor")
        assert block.has_tag("role", "sensor") is True
        assert block.has_tag("role", "actuator") is False

    def test_get_tag(self):
        block = AtomicBlock(name="A").with_tag("role", "sensor")
        assert block.get_tag("role") == "sensor"
        assert block.get_tag("missing") is None
        assert block.get_tag("missing", "default") == "default"

    def test_chaining(self):
        block = (
            AtomicBlock(name="A").with_tag("role", "sensor").with_tag("loop", "inner")
        )
        assert block.tags == {"role": "sensor", "loop": "inner"}


class TestTaggedEntity:
    def test_entity_tagging(self, float_type):
        entity = Entity(
            name="Agent",
            variables={"x": StateVariable(name="x", typedef=float_type)},
        )
        tagged = entity.with_tag("domain", "game_theory")
        assert tagged.tags == {"domain": "game_theory"}
        assert isinstance(tagged, Entity)
        assert tagged.name == "Agent"

    def test_frozen_entity_returns_new(self, float_type):
        entity = Entity(name="Agent")
        tagged = entity.with_tag("type", "player")
        assert entity.tags == {}
        assert tagged.tags == {"type": "player"}


class TestTaggedSpec:
    def test_spec_tagging(self):
        spec = GDSSpec(name="Test")
        tagged = spec.with_tags(version="0.2", domain="epidemiology")
        assert tagged.tags == {"version": "0.2", "domain": "epidemiology"}
        assert isinstance(tagged, GDSSpec)

    def test_spec_default_empty_tags(self):
        spec = GDSSpec(name="Test")
        assert spec.tags == {}


class TestTaggedRoleBlocks:
    def test_policy_tagging(self):
        p = Policy(name="decide").with_tag("agent", "alice")
        assert isinstance(p, Policy)
        assert p.get_tag("agent") == "alice"

    def test_boundary_action_tagging(self):
        ba = BoundaryAction(
            name="sensor",
            interface=Interface(forward_out=(port("reading"),)),
        ).with_tag("hardware", "thermometer")
        assert isinstance(ba, BoundaryAction)
        assert ba.has_tag("hardware")

    def test_control_action_tagging(self):
        ca = ControlAction(
            name="governance",
            interface=Interface(forward_out=(port("config"),)),
        ).with_tag("governance.level", "protocol")
        assert ca.get_tag("governance.level") == "protocol"


class TestTagCompileStripping:
    def test_tags_not_in_block_ir(self):
        from gds.compiler.compile import compile_system
        from gds.ir.models import BlockIR

        a = AtomicBlock(
            name="A",
            interface=Interface(forward_out=(port("x"),)),
        ).with_tag("role", "source")
        b = AtomicBlock(
            name="B",
            interface=Interface(forward_in=(port("x"),)),
        ).with_tag("role", "sink")

        ir = compile_system("test", a >> b)
        for block_ir in ir.blocks:
            assert isinstance(block_ir, BlockIR)
            assert not hasattr(block_ir, "tags")

    def test_tags_not_in_system_ir(self):
        from gds.compiler.compile import compile_system

        block = AtomicBlock(name="A").with_tag("key", "val")
        ir = compile_system("test", block)
        assert getattr(ir, "tags", {}) == {}

    def test_composition_ignores_tags(self):
        a = AtomicBlock(
            name="A",
            interface=Interface(forward_out=(port("x"),)),
        ).with_tag("group", "1")
        b = AtomicBlock(
            name="B",
            interface=Interface(forward_in=(port("x"),)),
        ).with_tag("group", "2")

        # Composition should work regardless of tags
        composed = a >> b
        assert composed.name == "A >> B"


# ══════════════════════════════════════════════════════════════
# Tagged base class directly
# ══════════════════════════════════════════════════════════════


class TestTaggedBase:
    def test_tagged_is_base_for_block(self):
        assert issubclass(AtomicBlock, Tagged)

    def test_tagged_is_base_for_entity(self):
        assert issubclass(Entity, Tagged)

    def test_tagged_is_base_for_spec(self):
        assert issubclass(GDSSpec, Tagged)

    def test_with_tags_overwrites(self):
        block = AtomicBlock(name="A").with_tag("k", "v1")
        updated = block.with_tag("k", "v2")
        assert updated.tags["k"] == "v2"


# ══════════════════════════════════════════════════════════════
# Backward Compatibility
# ══════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    def test_block_without_tags(self):
        block = AtomicBlock(name="A")
        assert block.tags == {}
        assert block.name == "A"

    def test_entity_without_tags(self, float_type):
        entity = Entity(
            name="Agent",
            variables={"x": StateVariable(name="x", typedef=float_type)},
        )
        assert entity.tags == {}

    def test_spec_without_params_or_tags(self):
        spec = GDSSpec(name="Test")
        assert len(spec.parameter_schema) == 0
        assert spec.parameters == {}
        assert spec.tags == {}

    def test_mechanism_without_params(self):
        mech = Mechanism(name="M", updates=[("A", "x")])
        assert mech.params_used == []

    def test_existing_serialization_works(self, basic_spec):
        from gds.serialize import spec_to_dict, spec_to_json

        d = spec_to_dict(basic_spec)
        assert "parameters" in d
        assert "blocks" in d

        j = spec_to_json(basic_spec)
        assert isinstance(j, str)
        assert "Basic" in j


# ══════════════════════════════════════════════════════════════
# Public API exports
# ══════════════════════════════════════════════════════════════


class TestPublicAPI:
    def test_all_v02_exports(self):
        import gds

        # Parameters
        assert hasattr(gds, "ParameterDef")
        assert hasattr(gds, "ParameterSchema")

        # Canonical
        assert hasattr(gds, "CanonicalGDS")
        assert hasattr(gds, "project_canonical")

        # Tagged
        assert hasattr(gds, "Tagged")

        # Verification
        assert hasattr(gds, "check_parameter_references")
        assert hasattr(gds, "check_canonical_wellformedness")

    def test_all_in_dunder_all(self):
        import gds

        for name in [
            "ParameterDef",
            "ParameterSchema",
            "CanonicalGDS",
            "project_canonical",
            "Tagged",
            "check_parameter_references",
            "check_canonical_wellformedness",
        ]:
            assert name in gds.__all__, f"{name} not in __all__"

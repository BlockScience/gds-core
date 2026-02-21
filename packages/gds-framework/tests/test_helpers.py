"""Tests for gds.helpers convenience functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from gds import (
    AtomicBlock,
    Entity,
    GDSSpec,
    Interface,
    ParameterDef,
    Severity,
    Space,
    StateVariable,
    TypeDef,
)
from gds.helpers import (
    _CUSTOM_CHECKS,
    all_checks,
    entity,
    gds_check,
    get_custom_checks,
    interface,
    space,
    state_var,
    typedef,
)
from gds.types.interface import port
from gds.verification.engine import ALL_CHECKS

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.verification.findings import Finding

# ── typedef ──────────────────────────────────────────────────


class TestTypedef:
    def test_basic(self):
        t = typedef("Count", int)
        assert isinstance(t, TypeDef)
        assert t.name == "Count"
        assert t.python_type is int
        assert t.description == ""
        assert t.constraint is None
        assert t.units is None

    def test_with_all_kwargs(self):
        t = typedef(
            "Rate",
            float,
            constraint=lambda x: x >= 0,
            description="A non-negative rate",
            units="per_day",
        )
        assert t.name == "Rate"
        assert t.python_type is float
        assert t.description == "A non-negative rate"
        assert t.units == "per_day"
        assert t.check_value(1.0)
        assert not t.check_value(-1.0)

    def test_frozen(self):
        t = typedef("X", int)
        with pytest.raises(ValidationError):
            t.name = "Y"  # type: ignore[misc]


# ── state_var ────────────────────────────────────────────────


class TestStateVar:
    def test_basic(self):
        Count = typedef("Count", int)
        sv = state_var(Count, symbol="S")
        assert isinstance(sv, StateVariable)
        assert sv.name == "Count"  # fallback name from typedef
        assert sv.typedef is Count
        assert sv.symbol == "S"
        assert sv.description == ""

    def test_with_description(self):
        Count = typedef("Count", int)
        sv = state_var(Count, symbol="N", description="Population count")
        assert sv.description == "Population count"


# ── entity ───────────────────────────────────────────────────


class TestEntity:
    def test_basic(self):
        Count = typedef("Count", int, constraint=lambda x: x >= 0)
        e = entity(
            "Susceptible",
            description="Susceptible compartment",
            count=state_var(Count, symbol="S"),
        )
        assert isinstance(e, Entity)
        assert e.name == "Susceptible"
        assert e.description == "Susceptible compartment"
        assert "count" in e.variables
        assert e.variables["count"].name == "count"  # name resolved from kwarg
        assert e.variables["count"].typedef is Count
        assert e.variables["count"].symbol == "S"

    def test_multiple_variables(self):
        Count = typedef("Count", int)
        Rate = typedef("Rate", float)
        e = entity("Pop", population=state_var(Count), growth_rate=state_var(Rate))
        assert set(e.variables.keys()) == {"population", "growth_rate"}
        assert e.variables["population"].name == "population"
        assert e.variables["growth_rate"].name == "growth_rate"

    def test_no_variables(self):
        e = entity("Empty")
        assert e.variables == {}

    def test_preserves_name_if_matches(self):
        """If name matches, no re-creation needed."""
        Count = typedef("Count", int)
        sv = StateVariable(name="count", typedef=Count, symbol="C")
        e = entity("Test", count=sv)
        assert e.variables["count"].name == "count"


# ── space ────────────────────────────────────────────────────


class TestSpace:
    def test_basic(self):
        Count = typedef("Count", int, constraint=lambda x: x >= 0)
        s = space("DeltaSpace", description="Population change", delta=Count)
        assert isinstance(s, Space)
        assert s.name == "DeltaSpace"
        assert s.description == "Population change"
        assert "delta" in s.fields
        assert s.fields["delta"] is Count

    def test_multiple_fields(self):
        Count = typedef("Count", int)
        Rate = typedef("Rate", float)
        s = space("Mixed", count=Count, rate=Rate)
        assert set(s.fields.keys()) == {"count", "rate"}

    def test_empty_fields(self):
        s = space("Empty")
        assert s.fields == {}


# ── interface ────────────────────────────────────────────────


class TestInterface:
    def test_basic(self):
        iface = interface(
            forward_in=["Contact Signal"],
            forward_out=["S Delta", "I Delta", "R Delta"],
        )
        assert isinstance(iface, Interface)
        assert len(iface.forward_in) == 1
        assert iface.forward_in[0].name == "Contact Signal"
        assert len(iface.forward_out) == 3
        assert iface.backward_in == ()
        assert iface.backward_out == ()

    def test_all_directions(self):
        iface = interface(
            forward_in=["A"],
            forward_out=["B"],
            backward_in=["C"],
            backward_out=["D"],
        )
        assert len(iface.forward_in) == 1
        assert len(iface.forward_out) == 1
        assert len(iface.backward_in) == 1
        assert len(iface.backward_out) == 1

    def test_empty(self):
        iface = interface()
        assert iface == Interface()

    def test_equivalent_to_manual(self):
        """Helper produces identical result to manual construction."""
        manual = Interface(
            forward_in=(port("X"),),
            forward_out=(port("Y"), port("Z")),
        )
        helper = interface(forward_in=["X"], forward_out=["Y", "Z"])
        assert manual == helper


# ── GDSSpec.collect ──────────────────────────────────────────


class TestCollect:
    def test_mixed_objects(self):
        Count = typedef("Count", int)
        s = space("S", delta=Count)
        e = entity("E", count=state_var(Count))
        b = AtomicBlock(name="B", interface=Interface())
        p = ParameterDef(name="rate", typedef=Count)

        spec = GDSSpec(name="test")
        spec.collect(Count, s, e, b, p)

        assert "Count" in spec.types
        assert "S" in spec.spaces
        assert "E" in spec.entities
        assert "B" in spec.blocks
        assert "rate" in spec.parameter_schema

    def test_chainable(self):
        Count = typedef("Count", int)
        Rate = typedef("Rate", float)
        spec = GDSSpec(name="test")
        result = spec.collect(Count, Rate)
        assert result is spec
        assert len(spec.types) == 2

    def test_type_error_for_unknown(self):
        spec = GDSSpec(name="test")
        with pytest.raises(TypeError, match="collect\\(\\) does not accept 'str'"):
            spec.collect("not a valid object")  # type: ignore[arg-type]

    def test_duplicate_raises(self):
        Count = typedef("Count", int)
        spec = GDSSpec(name="test")
        spec.collect(Count)
        with pytest.raises(ValueError, match="already registered"):
            spec.collect(Count)

    def test_empty(self):
        spec = GDSSpec(name="test")
        spec.collect()  # no-op, should not raise


# ── @gds_check decorator ────────────────────────────────────


class TestGdsCheck:
    def setup_method(self):
        """Clear custom check registry before each test."""
        _CUSTOM_CHECKS.clear()

    def teardown_method(self):
        """Clear custom check registry after each test."""
        _CUSTOM_CHECKS.clear()

    def test_registers_check(self):
        @gds_check("TEST-001", Severity.WARNING)
        def my_check(system: SystemIR) -> list[Finding]:
            return []

        checks = get_custom_checks()
        assert len(checks) == 1
        assert checks[0] is my_check

    def test_attaches_attributes(self):
        @gds_check("TEST-002", Severity.ERROR)
        def my_check(system: SystemIR) -> list[Finding]:
            return []

        assert my_check.check_id == "TEST-002"  # type: ignore[attr-defined]
        assert my_check.severity == Severity.ERROR  # type: ignore[attr-defined]

    def test_default_severity(self):
        @gds_check("TEST-003")
        def my_check(system: SystemIR) -> list[Finding]:
            return []

        assert my_check.severity == Severity.ERROR  # type: ignore[attr-defined]

    def test_all_checks_includes_builtins_and_custom(self):
        @gds_check("TEST-004")
        def my_check(system: SystemIR) -> list[Finding]:
            return []

        combined = all_checks()
        assert len(combined) == len(ALL_CHECKS) + 1
        assert my_check in combined
        for builtin in ALL_CHECKS:
            assert builtin in combined

    def test_get_custom_checks_returns_copy(self):
        @gds_check("TEST-005")
        def my_check(system: SystemIR) -> list[Finding]:
            return []

        checks1 = get_custom_checks()
        checks2 = get_custom_checks()
        assert checks1 == checks2
        assert checks1 is not checks2  # returns a copy

    def test_multiple_checks(self):
        @gds_check("TEST-A")
        def check_a(system: SystemIR) -> list[Finding]:
            return []

        @gds_check("TEST-B", Severity.WARNING)
        def check_b(system: SystemIR) -> list[Finding]:
            return []

        checks = get_custom_checks()
        assert len(checks) == 2
        assert checks[0] is check_a
        assert checks[1] is check_b

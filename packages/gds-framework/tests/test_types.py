"""Tests for the type system: tokens, Port, Interface, and TypeDef."""

import pytest
from pydantic import ValidationError

from gds.types.interface import Interface, port
from gds.types.tokens import tokenize, tokens_overlap, tokens_subset
from gds.types.typedef import (
    AgentID,
    NonNegativeFloat,
    PositiveInt,
    Probability,
    Timestamp,
    TokenAmount,
    TypeDef,
)

# ── tokenize() ──────────────────────────────────────────────


class TestTokenize:
    def test_empty_string(self):
        assert tokenize("") == frozenset()

    def test_single_token(self):
        assert tokenize("Temperature") == frozenset({"temperature"})

    def test_comma_separated(self):
        assert tokenize("Temperature, Pressure") == frozenset(
            {"temperature", "pressure"}
        )

    def test_plus_separated(self):
        assert tokenize("Temperature + Pressure") == frozenset(
            {"temperature", "pressure"}
        )

    def test_mixed_separators(self):
        result = tokenize("Temperature + Humidity, Pressure")
        assert result == frozenset({"temperature", "humidity", "pressure"})

    def test_whitespace_stripped(self):
        assert tokenize("  Temperature  ") == frozenset({"temperature"})

    def test_case_normalization(self):
        assert tokenize("TEMPERATURE") == frozenset({"temperature"})


# ── tokens_subset() ─────────────────────────────────────────


class TestTokensSubset:
    def test_exact_match(self):
        assert tokens_subset("Temperature", "Temperature") is True

    def test_subset_of_compound(self):
        assert tokens_subset("Temperature", "Temperature + Pressure") is True

    def test_whole_token_only(self):
        assert tokens_subset("Temp", "Temperature") is False

    def test_vacuous_truth(self):
        assert tokens_subset("", "Temperature") is True

    def test_empty_parent(self):
        assert tokens_subset("Temperature", "") is False


# ── tokens_overlap() ────────────────────────────────────────


class TestTokensOverlap:
    def test_shared_token(self):
        assert tokens_overlap("Temperature", "Temperature + Pressure") is True

    def test_disjoint(self):
        assert tokens_overlap("Temperature", "Pressure") is False

    def test_empty_a(self):
        assert tokens_overlap("", "Temperature") is False

    def test_empty_b(self):
        assert tokens_overlap("Temperature", "") is False


# ── Port ─────────────────────────────────────────────────────


class TestPort:
    def test_port_factory(self):
        p = port("Temperature")
        assert p.name == "Temperature"
        assert p.type_tokens == frozenset({"temperature"})

    def test_auto_tokenization(self):
        p = port("Temperature + Pressure")
        assert "temperature" in p.type_tokens
        assert "pressure" in p.type_tokens

    def test_frozen(self):
        p = port("Temperature")
        with pytest.raises(ValidationError):
            p.name = "Something Else"  # type: ignore[misc]

    def test_equality(self):
        assert port("Temperature") == port("Temperature")
        assert port("Temperature") != port("Pressure")

    def test_hashable(self):
        s = {port("Temperature"), port("Temperature")}
        assert len(s) == 1


# ── Interface ────────────────────────────────────────────────


class TestInterface:
    def test_empty_default(self):
        iface = Interface()
        assert iface.forward_in == ()
        assert iface.forward_out == ()
        assert iface.backward_in == ()
        assert iface.backward_out == ()

    def test_with_ports(self):
        iface = Interface(
            forward_in=(port("Temperature"),),
            forward_out=(port("Command"),),
        )
        assert len(iface.forward_in) == 1
        assert len(iface.forward_out) == 1

    def test_frozen(self):
        iface = Interface()
        with pytest.raises(ValidationError):
            iface.forward_in = (port("X"),)  # type: ignore[misc]

    def test_equality(self):
        i1 = Interface(forward_in=(port("X"),))
        i2 = Interface(forward_in=(port("X"),))
        assert i1 == i2


# ── TypeDef ──────────────────────────────────────────────────


class TestTypeDef:
    def test_creation(self):
        t = TypeDef(name="Prob", python_type=float)
        assert t.name == "Prob"
        assert t.python_type is float

    def test_validate_passes(self):
        t = TypeDef(name="Prob", python_type=float)
        assert t.check_value(0.5) is True

    def test_validate_wrong_type(self):
        t = TypeDef(name="Prob", python_type=float)
        assert t.check_value("not a float") is False

    def test_validate_constraint_passes(self):
        t = TypeDef(name="Pos", python_type=float, constraint=lambda x: x > 0)
        assert t.check_value(1.0) is True

    def test_validate_constraint_fails(self):
        t = TypeDef(name="Pos", python_type=float, constraint=lambda x: x > 0)
        assert t.check_value(-1.0) is False

    def test_units(self):
        t = TypeDef(name="Tokens", python_type=float, units="tokens")
        assert t.units == "tokens"

    def test_equality_by_name(self):
        t1 = TypeDef(name="Prob", python_type=float)
        t2 = TypeDef(name="Prob", python_type=float)
        assert t1 == t2

    def test_frozen(self):
        t = TypeDef(name="Prob", python_type=float)
        with pytest.raises(ValidationError):
            t.name = "Other"  # type: ignore[misc]


# ── Built-in types ───────────────────────────────────────────


class TestBuiltInTypes:
    @pytest.mark.parametrize(
        "typedef, value, expected",
        [
            (Probability, 0.0, True),
            (Probability, 0.5, True),
            (Probability, 1.0, True),
            (Probability, 1.5, False),
            (Probability, -0.1, False),
            (Probability, "half", False),
            (NonNegativeFloat, 0.0, True),
            (NonNegativeFloat, 100.0, True),
            (NonNegativeFloat, -0.01, False),
            (PositiveInt, 1, True),
            (PositiveInt, 100, True),
            (PositiveInt, 0, False),
            (PositiveInt, -1, False),
            (TokenAmount, 0.0, True),
            (TokenAmount, 100.5, True),
            (TokenAmount, -1.0, False),
            (AgentID, "agent-1", True),
            (AgentID, 42, False),
            (Timestamp, 0.0, True),
            (Timestamp, 1000.0, True),
            (Timestamp, -1.0, False),
        ],
    )
    def test_validate(self, typedef, value, expected):
        assert typedef.check_value(value) is expected

    @pytest.mark.parametrize(
        "typedef, attr, expected",
        [
            (TokenAmount, "units", "tokens"),
            (Timestamp, "units", "seconds"),
        ],
    )
    def test_units(self, typedef, attr, expected):
        assert getattr(typedef, attr) == expected

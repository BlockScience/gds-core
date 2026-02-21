"""Tests for typed product spaces."""

import pytest
from pydantic import ValidationError

from gds.spaces import EMPTY, TERMINAL, Space
from gds.types.typedef import NonNegativeFloat, Probability


class TestSpace:
    def test_creation(self):
        s = Space(name="Signal", fields={"prob": Probability})
        assert s.name == "Signal"
        assert "prob" in s.fields

    def test_empty_fields(self):
        s = Space(name="Empty")
        assert s.fields == {}

    def test_validate_valid_data(self):
        s = Space(name="Signal", fields={"prob": Probability})
        errors = s.validate_data({"prob": 0.5})
        assert errors == []

    def test_validate_invalid_value(self):
        s = Space(name="Signal", fields={"prob": Probability})
        errors = s.validate_data({"prob": 1.5})
        assert len(errors) == 1
        assert "prob" in errors[0]

    def test_validate_missing_field(self):
        s = Space(name="Signal", fields={"prob": Probability})
        errors = s.validate_data({})
        assert len(errors) == 1
        assert "Missing field" in errors[0]

    def test_validate_extra_field(self):
        s = Space(name="Signal", fields={"prob": Probability})
        errors = s.validate_data({"prob": 0.5, "extra": 42})
        assert len(errors) == 1
        assert "Unexpected fields" in errors[0]

    def test_validate_wrong_type(self):
        s = Space(name="Signal", fields={"prob": Probability})
        errors = s.validate_data({"prob": "not a float"})
        assert len(errors) == 1

    def test_is_compatible_same_structure(self):
        s1 = Space(name="A", fields={"x": Probability})
        s2 = Space(name="B", fields={"x": Probability})
        assert s1.is_compatible(s2) is True

    def test_is_compatible_different_fields(self):
        s1 = Space(name="A", fields={"x": Probability})
        s2 = Space(name="B", fields={"y": Probability})
        assert s1.is_compatible(s2) is False

    def test_is_compatible_different_types(self):
        s1 = Space(name="A", fields={"x": Probability})
        s2 = Space(name="B", fields={"x": NonNegativeFloat})
        assert s1.is_compatible(s2) is False

    def test_frozen(self):
        s = Space(name="Signal")
        with pytest.raises(ValidationError):
            s.name = "Other"  # type: ignore[misc]

    def test_equality_by_name(self):
        s1 = Space(name="Signal")
        s2 = Space(name="Signal")
        assert s1 == s2

    def test_multi_field_validate(self):
        s = Space(
            name="Complex",
            fields={"prob": Probability, "count": NonNegativeFloat},
        )
        assert s.validate_data({"prob": 0.5, "count": 10.0}) == []
        errors = s.validate_data({"prob": 1.5, "count": 10.0})
        assert len(errors) == 1


class TestSentinels:
    def test_empty_has_no_fields(self):
        assert EMPTY.fields == {}

    def test_terminal_has_no_fields(self):
        assert TERMINAL.fields == {}

    def test_empty_name(self):
        assert EMPTY.name == "empty"

    def test_terminal_name(self):
        assert TERMINAL.name == "terminal"

    def test_sentinels_are_different(self):
        assert EMPTY != TERMINAL

"""Tests for runtime constraint enforcement."""

import pytest
from gds.constraints import AdmissibleInputConstraint

from gds_analysis.constraints import ConstraintViolation, guarded_policy


def _simple_policy(state, params, **kw):
    return {"value": state.get("x", 0) + 1}


def _always_valid(state, signal):
    return True


def _always_invalid(state, signal):
    return False


def _range_check(state, signal):
    return 0 <= signal.get("value", 0) <= 10


class TestGuardedPolicy:
    def test_passes_valid_signal(self) -> None:
        ac = AdmissibleInputConstraint(
            name="check", boundary_block="b", constraint=_always_valid
        )
        guarded = guarded_policy(_simple_policy, [ac])
        result = guarded({"x": 5}, {})
        assert result == {"value": 6}

    def test_warn_on_violation(self) -> None:
        ac = AdmissibleInputConstraint(
            name="check", boundary_block="b", constraint=_always_invalid
        )
        guarded = guarded_policy(_simple_policy, [ac], on_violation="warn")
        # Should still return the signal (with warning)
        result = guarded({"x": 5}, {})
        assert result == {"value": 6}

    def test_raise_on_violation(self) -> None:
        ac = AdmissibleInputConstraint(
            name="check", boundary_block="b", constraint=_always_invalid
        )
        guarded = guarded_policy(_simple_policy, [ac], on_violation="raise")
        with pytest.raises(ConstraintViolation, match="check"):
            guarded({"x": 5}, {})

    def test_zero_on_violation(self) -> None:
        ac = AdmissibleInputConstraint(
            name="check", boundary_block="b", constraint=_always_invalid
        )
        guarded = guarded_policy(_simple_policy, [ac], on_violation="zero")
        result = guarded({"x": 5}, {})
        assert result == {}

    def test_range_constraint(self) -> None:
        ac = AdmissibleInputConstraint(
            name="range", boundary_block="b", constraint=_range_check
        )
        guarded = guarded_policy(_simple_policy, [ac], on_violation="raise")
        # x=5 → value=6, within [0, 10] → passes
        result = guarded({"x": 5}, {})
        assert result == {"value": 6}

        # x=10 → value=11, outside [0, 10] → fails
        with pytest.raises(ConstraintViolation):
            guarded({"x": 10}, {})

    def test_none_constraint_skipped(self) -> None:
        ac = AdmissibleInputConstraint(
            name="no_fn", boundary_block="b", constraint=None
        )
        guarded = guarded_policy(_simple_policy, [ac])
        result = guarded({"x": 5}, {})
        assert result == {"value": 6}

    def test_preserves_name(self) -> None:
        ac = AdmissibleInputConstraint(
            name="check", boundary_block="b", constraint=_always_valid
        )
        guarded = guarded_policy(_simple_policy, [ac])
        assert "simple_policy" in guarded.__name__

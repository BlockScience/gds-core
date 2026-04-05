"""Tests for ParameterSpace <-> ParameterSchema integration.

Covers from_parameter_schema(), validate_against_schema(), and the
PSUU-001 check function.
"""

from __future__ import annotations

import pytest
from gds.parameters import ParameterDef, ParameterSchema
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity

from gds_analysis.psuu.checks import check_parameter_space_compatibility
from gds_analysis.psuu.space import Continuous, Integer, ParameterSpace

# ── Helpers ──────────────────────────────────────────────────

_float_td = TypeDef(name="Rate", python_type=float)
_int_td = TypeDef(name="Count", python_type=int)
_str_td = TypeDef(name="Label", python_type=str)
_positive_float = TypeDef(
    name="PositiveFloat",
    python_type=float,
    constraint=lambda x: x > 0.0,
)


def _schema(*params: ParameterDef) -> ParameterSchema:
    """Build a ParameterSchema from a list of ParameterDef."""
    s = ParameterSchema()
    for p in params:
        s = s.add(p)
    return s


# ── from_parameter_schema ────────────────────────────────────


class TestFromParameterSchema:
    def test_float_with_bounds(self) -> None:
        schema = _schema(
            ParameterDef(name="alpha", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace.from_parameter_schema(schema)
        dim = space.params["alpha"]
        assert isinstance(dim, Continuous)
        assert dim.min_val == 0.0
        assert dim.max_val == 1.0

    def test_int_with_bounds(self) -> None:
        schema = _schema(ParameterDef(name="n", typedef=_int_td, bounds=(1, 10)))
        space = ParameterSpace.from_parameter_schema(schema)
        dim = space.params["n"]
        assert isinstance(dim, Integer)
        assert dim.min_val == 1
        assert dim.max_val == 10

    def test_mixed_params(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.01, 0.5)),
            ParameterDef(name="count", typedef=_int_td, bounds=(1, 100)),
        )
        space = ParameterSpace.from_parameter_schema(schema)
        assert len(space.params) == 2
        assert isinstance(space.params["rate"], Continuous)
        assert isinstance(space.params["count"], Integer)

    def test_no_bounds_raises(self) -> None:
        schema = _schema(ParameterDef(name="alpha", typedef=_float_td))
        with pytest.raises(ValueError, match="no bounds declared"):
            ParameterSpace.from_parameter_schema(schema)

    def test_unsupported_type_raises(self) -> None:
        schema = _schema(ParameterDef(name="label", typedef=_str_td, bounds=("a", "z")))
        with pytest.raises(TypeError, match="only float and int"):
            ParameterSpace.from_parameter_schema(schema)


# ── validate_against_schema ──────────────────────────────────


class TestValidateAgainstSchema:
    def test_compatible_returns_empty(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Continuous(min_val=0.0, max_val=1.0)})
        violations = space.validate_against_schema(schema)
        assert violations == []

    def test_missing_from_schema(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(
            params={"unknown_param": Continuous(min_val=0.0, max_val=1.0)}
        )
        violations = space.validate_against_schema(schema)
        assert len(violations) == 1
        assert violations[0].violation_type == "missing_from_schema"
        assert violations[0].param == "unknown_param"

    def test_sweep_min_below_bound(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Continuous(min_val=-0.5, max_val=0.5)})
        violations = space.validate_against_schema(schema)
        types = [v.violation_type for v in violations]
        assert "out_of_bounds" in types

    def test_sweep_max_above_bound(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Continuous(min_val=0.5, max_val=1.5)})
        violations = space.validate_against_schema(schema)
        types = [v.violation_type for v in violations]
        assert "out_of_bounds" in types

    def test_type_mismatch_continuous_vs_int(self) -> None:
        schema = _schema(ParameterDef(name="n", typedef=_int_td, bounds=(1, 10)))
        space = ParameterSpace(params={"n": Continuous(min_val=1.0, max_val=10.0)})
        violations = space.validate_against_schema(schema)
        types = [v.violation_type for v in violations]
        assert "type_mismatch" in types

    def test_type_mismatch_integer_vs_float(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Integer(min_val=0, max_val=1)})
        violations = space.validate_against_schema(schema)
        types = [v.violation_type for v in violations]
        assert "type_mismatch" in types

    def test_typedef_constraint_violation(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_positive_float, bounds=(0.0, 1.0))
        )
        # min_val=0.0 fails the constraint (x > 0.0)
        space = ParameterSpace(params={"rate": Continuous(min_val=0.0, max_val=0.5)})
        violations = space.validate_against_schema(schema)
        assert any(
            v.violation_type == "out_of_bounds" and "typedef constraint" in v.message
            for v in violations
        )

    def test_schema_without_bounds_skips_bound_check(self) -> None:
        """If the schema has no bounds, only type/existence is checked."""
        schema = _schema(ParameterDef(name="rate", typedef=_float_td))
        space = ParameterSpace(
            params={"rate": Continuous(min_val=-100.0, max_val=100.0)}
        )
        violations = space.validate_against_schema(schema)
        assert violations == []

    def test_multiple_violations(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(
            params={
                "rate": Continuous(min_val=-1.0, max_val=2.0),
                "ghost": Continuous(min_val=0.0, max_val=1.0),
            }
        )
        violations = space.validate_against_schema(schema)
        # "ghost" missing + "rate" has two bound violations
        assert len(violations) >= 3


# ── check_parameter_space_compatibility (PSUU-001) ──────────


class TestPSUU001:
    def test_compatible_returns_info_pass(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Continuous(min_val=0.0, max_val=1.0)})
        findings = check_parameter_space_compatibility(space, schema)
        assert len(findings) == 1
        assert findings[0].passed is True
        assert findings[0].check_id == "PSUU-001"
        assert findings[0].severity == Severity.INFO

    def test_out_of_bounds_returns_error(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"rate": Continuous(min_val=-1.0, max_val=0.5)})
        findings = check_parameter_space_compatibility(space, schema)
        assert any(f.severity == Severity.ERROR and not f.passed for f in findings)

    def test_missing_param_returns_warning(self) -> None:
        schema = _schema(
            ParameterDef(name="rate", typedef=_float_td, bounds=(0.0, 1.0))
        )
        space = ParameterSpace(params={"ghost": Continuous(min_val=0.0, max_val=1.0)})
        findings = check_parameter_space_compatibility(space, schema)
        warnings = [f for f in findings if f.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert warnings[0].passed is False
        assert "ghost" in warnings[0].source_elements

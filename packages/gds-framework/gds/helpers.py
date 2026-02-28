"""Convenience helpers to reduce GDS boilerplate.

Each helper is a plain factory function that returns existing Pydantic types —
no new abstractions, no wrapper classes. All original constructors still work;
helpers are opt-in sugar.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gds.ir.models import SystemIR
from gds.spaces import Space
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, Port
from gds.types.interface import port as _port
from gds.types.typedef import TypeDef
from gds.verification.findings import Finding, Severity

# ── Type & data helpers ──────────────────────────────────────


def typedef(
    name: str,
    python_type: type,
    *,
    constraint: Callable[[Any], bool] | None = None,
    description: str = "",
    units: str | None = None,
) -> TypeDef:
    """Create a TypeDef with positional name + type, keyword-only rest.

    Args:
        name: Unique type name (e.g. ``"Temperature"``).
        python_type: Python type for isinstance checks (e.g. ``float``).
        constraint: Optional predicate for runtime validation
            (e.g. ``lambda x: x >= 0``).
        description: Human-readable description.
        units: Optional unit label (e.g. ``"celsius"``).

    Returns:
        A frozen ``TypeDef`` instance.
    """
    return TypeDef(
        name=name,
        python_type=python_type,
        constraint=constraint,
        description=description,
        units=units,
    )


def state_var(
    td: TypeDef,
    *,
    symbol: str = "",
    description: str = "",
) -> StateVariable:
    """Create a StateVariable from a TypeDef, deferring name resolution to ``entity()``.

    The variable name defaults to ``td.name`` but is overridden by the kwarg key
    when passed to ``entity()``. Use this instead of constructing ``StateVariable``
    directly to avoid specifying the name twice.

    Args:
        td: The TypeDef that defines this variable's type and constraints.
        symbol: Optional math symbol (e.g. ``"x"``).
        description: Human-readable description.

    Returns:
        A frozen ``StateVariable`` instance.
    """
    return StateVariable(
        name=td.name, typedef=td, symbol=symbol, description=description
    )


def entity(name: str, *, description: str = "", **variables: StateVariable) -> Entity:
    """Create an Entity with variables as keyword arguments.

    Each kwarg key becomes the variable name. If the ``StateVariable`` was created
    via ``state_var()`` (which uses the typedef name as a placeholder), the name
    is replaced with the kwarg key.

    Args:
        name: Entity name (e.g. ``"Room"``, ``"Agent"``).
        description: Human-readable description.
        **variables: Named state variables. Keys become variable names.

    Returns:
        A frozen ``Entity`` instance.

    Example::

        temp = gds.typedef("Temperature", float)
        room = gds.entity("Room", temperature=gds.state_var(temp))
    """
    resolved: dict[str, StateVariable] = {}
    for var_name, sv in variables.items():
        if sv.name != var_name:
            # Re-create the frozen StateVariable with the correct name
            sv = StateVariable(
                name=var_name,
                typedef=sv.typedef,
                symbol=sv.symbol,
                description=sv.description,
            )
        resolved[var_name] = sv
    return Entity(name=name, variables=resolved, description=description)


def space(name: str, *, description: str = "", **fields: TypeDef) -> Space:
    """Create a Space with fields as keyword arguments.

    Args:
        name: Space name (e.g. ``"TemperatureSignal"``).
        description: Human-readable description.
        **fields: Named fields mapping to TypeDef instances.

    Returns:
        A frozen ``Space`` instance.
    """
    return Space(name=name, fields=fields, description=description)


# ── Interface helper ─────────────────────────────────────────


def interface(
    *,
    forward_in: list[str] | None = None,
    forward_out: list[str] | None = None,
    backward_in: list[str] | None = None,
    backward_out: list[str] | None = None,
) -> Interface:
    """Create an Interface from lists of port name strings.

    Each string is auto-converted to a ``Port`` via ``port()``, which
    tokenizes the name for structural matching (e.g. ``"Heater Command"``
    becomes tokens ``{"heater", "command"}``).

    Args:
        forward_in: Covariant input port names.
        forward_out: Covariant output port names.
        backward_in: Contravariant input port names.
        backward_out: Contravariant output port names.

    Returns:
        A frozen ``Interface`` instance.
    """

    def _to_ports(names: list[str] | None) -> tuple[Port, ...]:
        if names is None:
            return ()
        return tuple(_port(n) for n in names)

    return Interface(
        forward_in=_to_ports(forward_in),
        forward_out=_to_ports(forward_out),
        backward_in=_to_ports(backward_in),
        backward_out=_to_ports(backward_out),
    )


# ── Verification check decorator ────────────────────────────

CheckFn = Callable[[SystemIR], list[Finding]]

_CUSTOM_CHECKS: list[CheckFn] = []


def gds_check(
    check_id: str,
    severity: Severity = Severity.ERROR,
) -> Callable[[CheckFn], CheckFn]:
    """Decorator that registers a verification check function.

    Attaches ``check_id`` and ``severity`` as function attributes and
    adds it to the module-level custom check registry.

    Usage::

        @gds_check("CUSTOM-001", Severity.WARNING)
        def check_no_orphan_spaces(system: SystemIR) -> list[Finding]:
            ...
    """

    def decorator(fn: CheckFn) -> CheckFn:
        fn.check_id = check_id  # type: ignore[attr-defined]
        fn.severity = severity  # type: ignore[attr-defined]
        _CUSTOM_CHECKS.append(fn)
        return fn

    return decorator


def get_custom_checks() -> list[CheckFn]:
    """Return all check functions registered via ``@gds_check``."""
    return list(_CUSTOM_CHECKS)


def all_checks() -> list[CheckFn]:
    """Return built-in generic checks + all custom-registered checks."""
    from gds.verification.engine import ALL_CHECKS

    return list(ALL_CHECKS) + list(_CUSTOM_CHECKS)

"""Deliberately broken models for demonstrating GDS verification.

Each function returns a model or IR that contains a specific structural
error. The docstring explains what is wrong and which verification check
detects it.

Error classes demonstrated:
    1. Dangling wirings         (G-004)
    2. Type mismatches          (G-001, G-005)
    3. Covariant cycles         (G-006)
    4. Direction contradictions  (G-003)
    5. Incomplete signatures     (G-002)
    6. Orphan state variables    (SC-001)
    7. Write conflicts           (SC-002)
    8. Missing mechanisms        (SC-006, SC-007)
"""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.ir.models import BlockIR, FlowDirection, SystemIR, WiringIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Generic check models (operate on SystemIR)
# ══════════════════════════════════════════════════════════════════


def dangling_wiring_system() -> SystemIR:
    """A system where a wiring references a non-existent block.

    The wiring from 'Ghost' to 'B' is dangling because 'Ghost' does
    not exist in the block list. Detected by G-004 (dangling wirings).

    Expected findings:
        G-004: source 'Ghost' unknown
    """
    return SystemIR(
        name="Dangling Wiring Demo",
        blocks=[
            BlockIR(name="A", signature=("", "Signal", "", "")),
            BlockIR(name="B", signature=("Signal", "", "", "")),
        ],
        wirings=[
            WiringIR(
                source="Ghost",
                target="B",
                label="signal",
                direction=FlowDirection.COVARIANT,
            ),
        ],
    )


def type_mismatch_system() -> SystemIR:
    """A system with incompatible port types in sequential composition.

    Block A outputs 'Temperature' but Block B expects 'Pressure'. The
    wiring label 'humidity' matches neither. Detected by G-001
    (domain/codomain matching) and G-005 (sequential type compatibility).

    Expected findings:
        G-001: wiring label does not match source out or target in
        G-005: type mismatch in stack composition
    """
    return SystemIR(
        name="Type Mismatch Demo",
        blocks=[
            BlockIR(name="A", signature=("", "Temperature", "", "")),
            BlockIR(name="B", signature=("Pressure", "", "", "")),
        ],
        wirings=[
            WiringIR(
                source="A",
                target="B",
                label="humidity",
                direction=FlowDirection.COVARIANT,
            ),
        ],
    )


def covariant_cycle_system() -> SystemIR:
    """A system with a cycle in the covariant flow graph.

    Blocks A -> B -> C -> A form a cycle via non-temporal covariant
    wirings. This creates an algebraic loop within a single timestep.
    Detected by G-006 (covariant acyclicity).

    Expected findings:
        G-006: covariant flow graph contains a cycle
    """
    return SystemIR(
        name="Covariant Cycle Demo",
        blocks=[
            BlockIR(name="A", signature=("Signal", "Signal", "", "")),
            BlockIR(name="B", signature=("Signal", "Signal", "", "")),
            BlockIR(name="C", signature=("Signal", "Signal", "", "")),
        ],
        wirings=[
            WiringIR(
                source="A",
                target="B",
                label="signal",
                direction=FlowDirection.COVARIANT,
            ),
            WiringIR(
                source="B",
                target="C",
                label="signal",
                direction=FlowDirection.COVARIANT,
            ),
            WiringIR(
                source="C",
                target="A",
                label="signal",
                direction=FlowDirection.COVARIANT,
            ),
        ],
    )


def direction_contradiction_system() -> SystemIR:
    """A system with contradictory direction flags on a wiring.

    A wiring marked COVARIANT but also is_feedback=True is a
    contradiction: feedback implies contravariant flow. Detected by
    G-003 (direction consistency).

    Expected findings:
        G-003: COVARIANT + is_feedback -- contradiction
    """
    return SystemIR(
        name="Direction Contradiction Demo",
        blocks=[
            BlockIR(name="A", signature=("", "Command", "", "")),
            BlockIR(name="B", signature=("Command", "", "", "")),
        ],
        wirings=[
            WiringIR(
                source="A",
                target="B",
                label="command",
                direction=FlowDirection.COVARIANT,
                is_feedback=True,
            ),
        ],
    )


def incomplete_signature_system() -> SystemIR:
    """A system containing a block with no inputs and no outputs.

    Block 'Orphan' has a completely empty signature -- no forward or
    backward ports. Detected by G-002 (signature completeness).

    Expected findings:
        G-002: block has no inputs and no outputs
    """
    return SystemIR(
        name="Incomplete Signature Demo",
        blocks=[
            BlockIR(name="Valid", signature=("In", "Out", "", "")),
            BlockIR(name="Orphan", signature=("", "", "", "")),
        ],
        wirings=[],
    )


def fixed_pipeline_system() -> SystemIR:
    """A correctly wired sequential pipeline that passes all generic checks.

    This is the 'repaired' counterpart to the broken models above.
    Demonstrates a clean A -> B -> C pipeline with matching port types.
    """
    return SystemIR(
        name="Fixed Pipeline",
        blocks=[
            BlockIR(
                name="Sensor",
                signature=("Environment", "Temperature", "", ""),
            ),
            BlockIR(
                name="Controller",
                signature=("Temperature", "Command", "", ""),
            ),
            BlockIR(name="Actuator", signature=("Command", "Output", "", "")),
        ],
        wirings=[
            WiringIR(
                source="Sensor",
                target="Controller",
                label="temperature",
                direction=FlowDirection.COVARIANT,
            ),
            WiringIR(
                source="Controller",
                target="Actuator",
                label="command",
                direction=FlowDirection.COVARIANT,
            ),
        ],
    )


# ══════════════════════════════════════════════════════════════════
# Semantic check models (operate on GDSSpec)
# ══════════════════════════════════════════════════════════════════

# Shared types used across semantic models
_Count = TypeDef(
    name="Count",
    python_type=int,
    constraint=lambda x: x >= 0,
    description="Non-negative count",
)

_Rate = TypeDef(
    name="Rate",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Positive rate",
)


def orphan_state_spec() -> GDSSpec:
    """A spec where a state variable is never updated by any mechanism.

    Entity 'Reservoir' has variable 'level' but no mechanism lists
    ('Reservoir', 'level') in its updates. Detected by SC-001
    (completeness).

    Expected findings:
        SC-001: orphan state variable Reservoir.level
    """
    spec = GDSSpec(name="Orphan State Demo")

    spec.register_type(_Count)

    reservoir = Entity(
        name="Reservoir",
        variables={
            "level": StateVariable(name="level", typedef=_Count, symbol="L"),
        },
    )
    spec.register_entity(reservoir)

    # A policy that observes but no mechanism updates the reservoir
    observe = Policy(
        name="Observe Level",
        interface=Interface(forward_out=(port("Level Signal"),)),
    )
    spec.register_block(observe)

    return spec


def write_conflict_spec() -> GDSSpec:
    """A spec where two mechanisms update the same state variable.

    Both 'Increment Counter' and 'Decrement Counter' update
    ('Counter', 'value') within the same wiring. Detected by SC-002
    (determinism).

    Expected findings:
        SC-002: write conflict -- Counter.value updated by two mechanisms
    """
    spec = GDSSpec(name="Write Conflict Demo")

    spec.register_type(_Count)

    counter = Entity(
        name="Counter",
        variables={
            "value": StateVariable(name="value", typedef=_Count, symbol="C"),
        },
    )
    spec.register_entity(counter)

    signal_space = Space(
        name="DeltaSpace",
        fields={"delta": _Count},
    )
    spec.register_space(signal_space)

    source = BoundaryAction(
        name="Source",
        interface=Interface(forward_out=(port("Delta Signal"),)),
    )
    spec.register_block(source)

    inc = Mechanism(
        name="Increment Counter",
        interface=Interface(forward_in=(port("Delta Signal"),)),
        updates=[("Counter", "value")],
    )
    spec.register_block(inc)

    dec = Mechanism(
        name="Decrement Counter",
        interface=Interface(forward_in=(port("Delta Signal"),)),
        updates=[("Counter", "value")],
    )
    spec.register_block(dec)

    spec.register_wiring(
        SpecWiring(
            name="Counter Pipeline",
            block_names=["Source", "Increment Counter", "Decrement Counter"],
            wires=[
                Wire(source="Source", target="Increment Counter"),
                Wire(source="Source", target="Decrement Counter"),
            ],
        )
    )

    return spec


def empty_canonical_spec() -> GDSSpec:
    """A spec with no mechanisms and no entities -- empty canonical form.

    The spec has a policy block but no mechanisms or entities, so the
    canonical projection has empty f (state transition) and empty X
    (state space). Detected by SC-006 and SC-007.

    Expected findings:
        SC-006: no mechanisms found -- state transition f is empty
        SC-007: state space X is empty
    """
    spec = GDSSpec(name="Empty Canonical Demo")

    observe = Policy(
        name="Observer",
        interface=Interface(
            forward_in=(port("Input Signal"),),
            forward_out=(port("Output Signal"),),
        ),
    )
    spec.register_block(observe)

    return spec


def fixed_spec() -> GDSSpec:
    """A complete, well-formed spec that passes all semantic checks.

    Demonstrates a minimal but correct GDS specification:
    - Entity with state variable updated by a mechanism (SC-001 pass)
    - No write conflicts (SC-002 pass)
    - Mechanisms exist (SC-006 pass)
    - State space is non-empty (SC-007 pass)
    """
    spec = GDSSpec(name="Fixed Model")

    spec.register_type(_Count)
    spec.register_type(_Rate)

    tank = Entity(
        name="Tank",
        variables={
            "level": StateVariable(name="level", typedef=_Count, symbol="L"),
        },
    )
    spec.register_entity(tank)

    signal_space = Space(
        name="FlowSignal",
        fields={"rate": _Rate},
    )
    spec.register_space(signal_space)

    source = BoundaryAction(
        name="Inflow Source",
        interface=Interface(forward_out=(port("Flow Signal"),)),
        params_used=["flow_rate"],
    )
    spec.register_block(source)

    controller = Policy(
        name="Flow Controller",
        interface=Interface(
            forward_in=(port("Flow Signal"),),
            forward_out=(port("Tank Update"),),
        ),
    )
    spec.register_block(controller)

    update = Mechanism(
        name="Update Tank",
        interface=Interface(forward_in=(port("Tank Update"),)),
        updates=[("Tank", "level")],
    )
    spec.register_block(update)

    spec.register_parameter("flow_rate", _Rate)

    spec.register_wiring(
        SpecWiring(
            name="Tank Pipeline",
            block_names=["Inflow Source", "Flow Controller", "Update Tank"],
            wires=[
                Wire(
                    source="Inflow Source",
                    target="Flow Controller",
                    space="FlowSignal",
                ),
                Wire(source="Flow Controller", target="Update Tank"),
            ],
        )
    )

    return spec

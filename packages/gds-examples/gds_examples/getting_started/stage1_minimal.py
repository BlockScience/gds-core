"""Stage 1 — Your First GDS Model.

Build a minimal thermostat: a heater warms a room.
We define a single Entity (the Room), two blocks (a BoundaryAction for
the heater input and a Mechanism for the state update), compose them
with >>, and register everything in a GDSSpec.

GDS Decomposition:
    X = (temperature,)          -- one state variable
    U = heater_signal           -- exogenous heat input
    f = update_temperature      -- state transition
    g = (none)                  -- no policy yet (added in stage 2)

Composition:
    heater >> update_temperature
"""

from gds.blocks.roles import BoundaryAction, Mechanism
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ── Types ────────────────────────────────────────────────────
# TypeDef wraps a Python type with an optional runtime constraint.
# Temperature can be any float; HeatRate must be non-negative.

Temperature = TypeDef(
    name="Temperature",
    python_type=float,
    description="Temperature in degrees Celsius",
)

HeatRate = TypeDef(
    name="HeatRate",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Heat input rate (watts)",
)

# ── Entity ───────────────────────────────────────────────────
# An Entity is a named component of the system state X.
# The Room has one state variable: temperature.

room = Entity(
    name="Room",
    variables={
        "temperature": StateVariable(
            name="temperature",
            typedef=Temperature,
            symbol="T",
            description="Current room temperature",
        ),
    },
    description="The room being heated",
)

# ── Blocks ───────────────────────────────────────────────────
# BoundaryAction: exogenous input — the heater delivers heat.
#   forward_in must be empty (boundary actions receive nothing).
#   forward_out emits a "Heat Signal" port.

heater = BoundaryAction(
    name="Heater",
    interface=Interface(
        forward_out=(port("Heat Signal"),),
    ),
)

# Mechanism: state update — writes new temperature to the entity.
#   forward_in receives the "Heat Signal".
#   backward_in and backward_out must be empty (mechanism constraint).
#   updates declares which entity variables this mechanism modifies.

update_temperature = Mechanism(
    name="Update Temperature",
    interface=Interface(
        forward_in=(port("Heat Signal"),),
    ),
    updates=[("Room", "temperature")],
)

# ── Composition ──────────────────────────────────────────────
# The >> operator chains blocks sequentially. Port tokens must
# overlap: "Heat Signal" tokens = {"heat", "signal"} match on both sides.

pipeline = heater >> update_temperature


def build_spec() -> GDSSpec:
    """Register all components in a GDSSpec and return it."""
    spec = GDSSpec(
        name="Minimal Thermostat",
        description="Heater warms a room — the simplest possible GDS model",
    )

    # Register types
    spec.register_type(Temperature)
    spec.register_type(HeatRate)

    # Register entity
    spec.register_entity(room)

    # Register blocks
    spec.register_block(heater)
    spec.register_block(update_temperature)

    # Register wiring
    spec.register_wiring(
        SpecWiring(
            name="Heat Pipeline",
            block_names=["Heater", "Update Temperature"],
            wires=[
                Wire(source="Heater", target="Update Temperature"),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Compile the composition tree to a flat SystemIR."""
    return compile_system(name="Minimal Thermostat", root=pipeline)


if __name__ == "__main__":
    spec = build_spec()
    print(f"Spec: {spec.name}")
    print(f"  Entities: {list(spec.entities.keys())}")
    print(f"  Blocks:   {list(spec.blocks.keys())}")
    print(f"  Errors:   {spec.validate_spec()}")

    system = build_system()
    print(f"\nSystemIR: {system.name}")
    print(f"  Blocks:  {[b.name for b in system.blocks]}")
    print(f"  Wirings: {len(system.wirings)}")

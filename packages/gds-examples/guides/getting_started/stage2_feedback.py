"""Stage 2 — Adding Feedback.

Extend the minimal thermostat with a feedback loop: a Sensor reads the
room temperature, a Policy (thermostat controller) decides the heat
command, and a TemporalLoop feeds updated state back to the sensor
across timesteps.

New concepts:
    - Policy block (decision logic)
    - Parallel composition (|) for the input tier
    - TemporalLoop (.loop()) for cross-timestep state feedback
    - Explicit Wiring for the temporal connection

GDS Decomposition:
    X = (temperature,)
    U = heater_signal
    g = thermostat_controller     -- policy: maps observation to command
    f = update_temperature        -- mechanism: writes state
    Theta = {setpoint}            -- desired temperature

Composition:
    (heater | sensor) >> controller >> update_temperature
        .loop([Update Temperature -> Sensor COVARIANT])
"""

from gds.blocks.composition import Wiring
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ── Types ────────────────────────────────────────────────────

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

SetpointParam = TypeDef(
    name="SetpointParam",
    python_type=float,
    description="Desired temperature setpoint",
)

# ── Entity ───────────────────────────────────────────────────

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

# BoundaryAction: exogenous heat input (same as stage 1)
heater = BoundaryAction(
    name="Heater",
    interface=Interface(
        forward_out=(port("Heat Signal"),),
    ),
)

# Policy (observer): reads the room temperature from the temporal loop.
# forward_in receives "Temperature Reading" from the mechanism's output
# at the previous timestep. forward_out emits "Temperature Observation"
# for the controller.
sensor = Policy(
    name="Sensor",
    interface=Interface(
        forward_in=(port("Temperature Reading"),),
        forward_out=(port("Temperature Observation"),),
    ),
)

# Policy (controller): reads the observation and heat signal, decides command.
# params_used declares that this block depends on the "setpoint" parameter.
controller = Policy(
    name="Controller",
    interface=Interface(
        forward_in=(
            port("Temperature Observation"),
            port("Heat Signal"),
        ),
        forward_out=(port("Heat Command"),),
    ),
    params_used=["setpoint"],
)

# Mechanism: updates room temperature. Now also has forward_out so the
# temporal loop can feed the updated temperature back to the sensor.
update_temperature = Mechanism(
    name="Update Temperature",
    interface=Interface(
        forward_in=(port("Heat Command"),),
        forward_out=(port("Temperature Reading"),),
    ),
    updates=[("Room", "temperature")],
)


def build_spec() -> GDSSpec:
    """Build the full thermostat spec with feedback."""
    spec = GDSSpec(
        name="Thermostat with Feedback",
        description="Thermostat controller with temporal feedback loop",
    )

    # Types
    spec.register_type(Temperature)
    spec.register_type(HeatRate)
    spec.register_type(SetpointParam)

    # Entity
    spec.register_entity(room)

    # Blocks
    spec.register_block(heater)
    spec.register_block(sensor)
    spec.register_block(controller)
    spec.register_block(update_temperature)

    # Parameter
    spec.register_parameter("setpoint", SetpointParam)

    # Wiring
    spec.register_wiring(
        SpecWiring(
            name="Thermostat Loop",
            block_names=["Heater", "Sensor", "Controller", "Update Temperature"],
            wires=[
                Wire(source="Heater", target="Controller"),
                Wire(source="Sensor", target="Controller"),
                Wire(source="Controller", target="Update Temperature"),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build the composition tree with a temporal loop and compile.

    The composition follows the tiered pattern:
        Tier 1: (heater | sensor)       -- exogenous input + observer in parallel
        Tier 2: controller              -- decision logic
        Tier 3: update_temperature      -- state update

    The .loop() wraps the whole pipeline with a COVARIANT temporal wiring
    from the mechanism's forward_out back to the sensor's forward_in.
    This creates cross-timestep feedback: at timestep t+1, the sensor
    receives the temperature that was computed at timestep t.
    """
    # Tier 1: inputs and observers in parallel
    input_tier = heater | sensor

    # Tier 2 >> Tier 3: controller into state update
    # Sequential composition: tokens overlap on "Heat Command"
    forward_pipeline = input_tier >> controller >> update_temperature

    # Temporal loop: mechanism output feeds sensor input at next timestep
    system_with_loop = forward_pipeline.loop(
        [
            Wiring(
                source_block="Update Temperature",
                source_port="Temperature Reading",
                target_block="Sensor",
                target_port="Temperature Reading",
                direction=FlowDirection.COVARIANT,
            )
        ],
    )

    return compile_system(name="Thermostat with Feedback", root=system_with_loop)


if __name__ == "__main__":
    spec = build_spec()
    print(f"Spec: {spec.name}")
    print(f"  Entities:   {list(spec.entities.keys())}")
    print(f"  Blocks:     {list(spec.blocks.keys())}")
    print(f"  Parameters: {list(spec.parameters.keys())}")
    print(f"  Errors:     {spec.validate_spec()}")

    system = build_system()
    print(f"\nSystemIR: {system.name}")
    print(f"  Blocks:   {[b.name for b in system.blocks]}")
    print(f"  Wirings:  {len(system.wirings)}")

    temporal = [w for w in system.wirings if w.is_temporal]
    print(f"  Temporal: {[(w.source, w.target) for w in temporal]}")

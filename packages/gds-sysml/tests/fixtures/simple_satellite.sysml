/* Simple Satellite Thermal Control System
 *
 * A minimal SysML v2 model with @GDS* annotations demonstrating
 * the SysML→GDS pipeline. Models a satellite's thermal control
 * loop with sensors, controllers, and actuators.
 *
 * GDS decomposition:
 *   BoundaryAction: SolarFluxSensor, TemperatureSensor
 *   Policy: ThermalController
 *   Mechanism: HeaterActuator, RadiatorActuator
 *   Entities: ThermalState (temperature, heaterPower, radiatorAngle)
 */

package SimpleSatellite {

    // ── GDS metadata definitions ──────────────────────────────

    metadata def GDSBoundaryAction;
    metadata def GDSPolicy;
    metadata def GDSMechanism;
    metadata def GDSControlAction;
    metadata def GDSStateVariable;
    metadata def GDSParameter;
    metadata def GDSDynamics;

    // ── Type definitions ──────────────────────────────────────

    part def Temperature;
    part def Power;
    part def Angle;
    part def HeatFlux;

    // ── State entity ──────────────────────────────────────────

    part def ThermalState {
        @GDSStateVariable { symbol = "T"; }
        attribute temperature : Real;

        @GDSStateVariable { symbol = "P_h"; }
        attribute heaterPower : Real;

        @GDSStateVariable { symbol = "alpha"; }
        attribute radiatorAngle : Real;

        @GDSParameter { units = "W/m^2"; }
        attribute solarConstant : Real;

        @GDSParameter { units = "kg/m^2"; }
        attribute thermalMass : Real;
    }

    // ── Boundary actions (exogenous inputs) ───────────────────

    @GDSBoundaryAction
    action def SolarFluxSensor {
        out port solarFluxOut : HeatFlux;
    }

    @GDSBoundaryAction
    action def TemperatureSensor {
        out port temperatureOut : Temperature;
    }

    // ── Policy (decision logic) ───────────────────────────────

    @GDSPolicy
    action def ThermalController {
        in port temperatureIn : Temperature;
        in port solarFluxIn : HeatFlux;
        out port heaterCommandOut : Power;
        out port radiatorCommandOut : Angle;
    }

    // ── Mechanisms (state updates) ────────────────────────────

    @GDSMechanism
    @GDSDynamics { reads = [temperature, heaterPower]; writes = [temperature]; }
    action def HeaterActuator {
        in port heaterCommandIn : Power;
    }

    @GDSMechanism
    @GDSDynamics { reads = [temperature, radiatorAngle]; writes = [radiatorAngle]; }
    action def RadiatorActuator {
        in port radiatorCommandIn : Angle;
    }

    // ── Connections (wiring) ──────────────────────────────────

    connect SolarFluxSensor.solarFluxOut to ThermalController.solarFluxIn;
    connect TemperatureSensor.temperatureOut to ThermalController.temperatureIn;
    connect ThermalController.heaterCommandOut to HeaterActuator.heaterCommandIn;
    connect ThermalController.radiatorCommandOut to RadiatorActuator.radiatorCommandIn;
}

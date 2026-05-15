"""Lesson 2 -- Proportional Control and Performance Metrics.

Close the loop with a proportional (P) controller: V = Kp * (theta_ref - theta).
Simulate the step response for different gain values and extract standard
performance metrics: rise time, settling time, overshoot, steady-state error.

New concepts:
    - Closed-loop control via ODE parameter (Kp, theta_ref)
    - step_response_metrics() / StepMetrics (from gds_analysis.response)
    - step_response_plot() with metric annotations (from gds_viz.response)
    - compare_responses() for gain sweep visualization

GDS Decomposition:
    X  = (theta, omega)
    U  = theta_ref (reference position)
    g  = p_controller:  V = Kp * (theta_ref - theta)
    f  = motor_dynamics
    Theta = {J, b, K_t, Kp, theta_ref}

Composition:
    (reference | position_sensor) >> p_controller >> motor_dynamics
        .loop(dynamics -> position_sensor)
"""

from typing import Any

from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.symbolic.elements import OutputEquation, StateEquation
from gds_domains.symbolic.model import SymbolicControlModel

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------


def build_model() -> SymbolicControlModel:
    """DC motor with proportional position controller.

    The controller law V = Kp * (theta_ref - theta) is embedded in the
    state equation for omega. In GDS terms, the controller is a Policy
    block whose behavioral implementation is this proportional law.
    """
    return SymbolicControlModel(
        name="DC Motor P Control",
        states=[
            State(name="theta", initial=0.0),
            State(name="omega", initial=0.0),
        ],
        inputs=[
            Input(name="theta_ref"),
        ],
        sensors=[
            Sensor(name="position_sensor", observes=["theta"]),
        ],
        controllers=[
            Controller(
                name="p_controller",
                reads=["position_sensor", "theta_ref"],
                drives=["theta", "omega"],
            ),
        ],
        state_equations=[
            StateEquation(state_name="theta", expr_str="omega"),
            StateEquation(
                state_name="omega",
                expr_str=(f"-({b}/{J})*omega + ({K_t}/{J})*Kp*(theta_ref - theta)"),
            ),
        ],
        output_equations=[
            OutputEquation(sensor_name="position_sensor", expr_str="theta"),
        ],
        symbolic_params=["Kp"],
        description="DC motor with proportional position control",
    )


def simulate_p_control(
    kp: float = 5.0,
    theta_ref: float = 1.0,
    t_end: float = 5.0,
) -> tuple[list[float], list[float]]:
    """Simulate closed-loop P control step response.

    Returns (times, theta_values).
    """
    from gds_continuous import ODEModel, ODESimulation

    model = build_model()
    ode_fn, state_order = model.to_ode_function()

    ode_model = ODEModel(
        state_names=state_order,
        initial_state={"theta": 0.0, "omega": 0.0},
        rhs=ode_fn,
        params={"theta_ref": [theta_ref], "Kp": [kp]},
    )
    sim = ODESimulation(model=ode_model, t_span=(0.0, t_end), solver="RK45")
    results = sim.run()
    return results.times, results.state_array("theta")


def analyze_step_response(
    kp: float = 5.0,
    theta_ref: float = 1.0,
) -> tuple[list[float], list[float], Any]:
    """Simulate and compute step response metrics.

    Returns (times, theta_values, StepMetrics).
    """
    from gds_analysis.response import step_response_metrics

    times, theta = simulate_p_control(kp=kp, theta_ref=theta_ref)
    metrics = step_response_metrics(times, theta, setpoint=theta_ref)
    return times, theta, metrics


if __name__ == "__main__":
    print("=== Lesson 2: Proportional Control ===\n")

    # --- Gain sweep ---
    gains = [1.0, 5.0, 10.0]
    print(f"{'Kp':>6}  {'Rise':>8}  {'Settle':>8}  {'OS%':>8}  {'SSE':>8}")
    print("-" * 50)

    responses = []
    for kp in gains:
        times, theta, metrics = analyze_step_response(kp=kp)
        print(
            f"{kp:6.1f}  {metrics.rise_time:8.3f}  "
            f"{metrics.settling_time:8.3f}  {metrics.overshoot_pct:8.2f}  "
            f"{metrics.steady_state_error:8.4f}"
        )
        responses.append((times, theta, f"Kp={kp}"))

    print("\n  Higher Kp -> faster rise but more overshoot.")
    print("  P control alone has steady-state error for this 2nd-order plant.")
    print("  (Lesson 3 adds integral action to eliminate SSE.)")

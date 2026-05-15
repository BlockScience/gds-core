"""Lesson 4 -- Disturbance Rejection and Sensitivity Analysis.

Add a load torque disturbance to the motor and analyze how the
feedback loop handles it. Introduce feedforward compensation and
the Gang of Six sensitivity functions that quantify the trade-offs
between reference tracking, disturbance rejection, and noise immunity.

New concepts:
    - 2-input plant (voltage V + load torque tau_load)
    - Feedforward disturbance compensation
    - sensitivity() -> Gang of Six (S, T, CS, PS, KS, KPS)
    - Sensitivity function Bode plots

GDS Decomposition:
    X  = (theta, omega)
    U  = (theta_ref, tau_load)
    g  = pid_controller + feedforward
    f  = motor_dynamics (with disturbance)
    Theta = {J, b, K_t, Kp, Ki, Kd}

Composition:
    (reference | disturbance | sensor) >> (controller | feedforward)
        >> motor_dynamics .loop(dynamics -> sensor)
"""

from gds_domains.symbolic.transfer import TransferFunction, sensitivity

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Transfer function helpers
# ---------------------------------------------------------------------------


def get_plant_tf() -> TransferFunction:
    """Open-loop plant: P(s) = K_t/J / (s^2 + (b/J)*s).

    H(s) = (K_t/J) / (s^2 + (b/J)*s) = 1.0 / (s^2 + 10*s)
    """
    return TransferFunction(
        num=[K_t / J],
        den=[1.0, b / J, 0.0],  # s^2 + 10s
    )


def get_pid_tf(kp: float = 10.0, ki: float = 5.0, kd: float = 0.5) -> TransferFunction:
    """PID controller: K(s) = Kp + Ki/s + Kd*s = (Kd*s^2 + Kp*s + Ki) / s."""
    return TransferFunction(
        num=[kd, kp, ki],  # Kd*s^2 + Kp*s + Ki
        den=[1.0, 0.0],  # s
    )


def analyze_sensitivity(
    kp: float = 10.0, ki: float = 5.0, kd: float = 0.5
) -> dict[str, TransferFunction]:
    """Compute the Gang of Six sensitivity functions.

    Returns dict with keys S, T, CS, PS, KS, KPS.
    """
    plant = get_plant_tf()
    controller = get_pid_tf(kp, ki, kd)
    return sensitivity(plant, controller)


def simulate_disturbance(
    kp: float = 10.0,
    ki: float = 5.0,
    kd: float = 0.5,
    tau_load: float = 0.005,
    use_feedforward: bool = False,
    t_end: float = 10.0,
) -> tuple[list[float], list[float]]:
    """Simulate motor with step disturbance at t=t_end/2.

    The disturbance tau_load is applied as a constant after halfway.
    If use_feedforward=True, adds V_ff = tau_load / K_t to cancel it.

    Returns (times, theta_values).
    """
    from gds_continuous import ODEModel, ODESimulation

    t_disturb = t_end / 2

    def motor_with_disturbance(t, y, params):
        theta, omega, err_int = y
        ref = params.get("theta_ref", 1.0)
        kp_ = params.get("Kp", kp)
        ki_ = params.get("Ki", ki)
        kd_ = params.get("Kd", kd)

        error = ref - theta
        v_fb = kp_ * error + ki_ * err_int + kd_ * (0 - omega)

        # Disturbance: step at t_disturb
        d = tau_load if t >= t_disturb else 0.0

        # Feedforward: cancel known disturbance
        v_ff = (d / K_t) if use_feedforward else 0.0

        v = v_fb + v_ff

        dtheta = omega
        domega = -(b / J) * omega + (K_t / J) * v - (1 / J) * d
        derr = error
        return [dtheta, domega, derr]

    ode_model = ODEModel(
        state_names=["theta", "omega", "error_int"],
        initial_state={"theta": 0.0, "omega": 0.0, "error_int": 0.0},
        rhs=motor_with_disturbance,
        params={"theta_ref": [1.0], "Kp": [kp], "Ki": [ki], "Kd": [kd]},
    )
    sim = ODESimulation(model=ode_model, t_span=(0.0, t_end), solver="RK45")
    results = sim.run()
    return results.times, results.state_array("theta")


if __name__ == "__main__":
    print("=== Lesson 4: Disturbance Rejection + Gang of Six ===\n")

    # --- Gang of Six ---
    gang = analyze_sensitivity()
    print("Gang of Six sensitivity functions:")
    for name, tf in gang.items():
        print(
            f"  {name:>4}: num={[f'{c:.3f}' for c in tf.num]}, "
            f"den={[f'{c:.3f}' for c in tf.den]}"
        )

    # Evaluate S(0) and T(0) — DC sensitivity
    s_dc = gang["S"].num[-1] / gang["S"].den[-1]
    t_dc = gang["T"].num[-1] / gang["T"].den[-1]
    print(f"\n  S(0) = {s_dc:.4f}  (ideal: 0 for perfect disturbance rejection)")
    print(f"  T(0) = {t_dc:.4f}  (ideal: 1 for perfect reference tracking)")
    print(f"  S(0) + T(0) = {s_dc + t_dc:.4f}  (must equal 1)")

    # --- Disturbance simulation ---
    print("\n--- Step disturbance at t=5s (tau_load=0.005 N*m) ---")
    t_fb, y_fb = simulate_disturbance(use_feedforward=False)
    t_ff, y_ff = simulate_disturbance(use_feedforward=True)

    # Measure disturbance effect (deviation from setpoint after disturbance)
    mid = len(t_fb) // 2
    max_dev_fb = max(abs(v - 1.0) for v in y_fb[mid:])
    max_dev_ff = max(abs(v - 1.0) for v in y_ff[mid:])

    print(f"  FB-only:  max deviation = {max_dev_fb:.4f} rad")
    print(f"  FF+FB:    max deviation = {max_dev_ff:.4f} rad")
    print(
        f"  Feedforward reduces disturbance effect by "
        f"{(1 - max_dev_ff / max_dev_fb) * 100:.0f}%"
    )

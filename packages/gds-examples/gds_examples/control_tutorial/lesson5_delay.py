"""Lesson 5 -- Sensor Delay, Pade Approximation, and Stability Margins.

Real sensors have sampling delay, communication latency, and processing
time. We model this as a pure time delay e^{-s*tau}, approximate it
with a Pade rational polynomial, and analyze how the delay degrades
gain and phase margins. The Nyquist plot shows how close the delayed
system comes to encircling the critical point (-1, 0).

New concepts:
    - pade_approximation() (from gds_domains.symbolic.delay)
    - delay_system() for cascading delay with plant TF
    - gain_margin(), phase_margin() (from gds_analysis.linear)
    - nyquist_plot(), root_locus_plot() (from gds_viz.frequency)
    - Stability margin degradation analysis

GDS Decomposition:
    X  = (theta, omega)
    U  = theta_ref
    g  = pid_controller (with delayed measurement)
    f  = motor_dynamics
    Theta = {J, b, K_t, Kp, Ki, Kd, tau_delay}

Composition:
    reference >> pid_controller >> motor_dynamics >> [DELAY] >> sensor
        .loop(sensor -> pid_controller)
"""

from gds_domains.symbolic.delay import pade_approximation
from gds_domains.symbolic.transfer import TransferFunction, _tf_multiply

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Transfer function construction
# ---------------------------------------------------------------------------


def get_plant_tf() -> TransferFunction:
    """Open-loop plant: P(s) = (K_t/J) / (s^2 + (b/J)*s)."""
    return TransferFunction(num=[K_t / J], den=[1.0, b / J, 0.0])


def get_pid_tf(kp: float = 10.0, ki: float = 5.0, kd: float = 0.5) -> TransferFunction:
    """PID controller TF: K(s) = (Kd*s^2 + Kp*s + Ki) / s."""
    return TransferFunction(num=[kd, kp, ki], den=[1.0, 0.0])


def get_loop_tf(delay: float = 0.0, pade_order: int = 3) -> TransferFunction:
    """Open-loop transfer function L(s) = K(s) * P(s) [* Pade(s)].

    If delay > 0, cascades the Pade approximation of e^{-s*tau}.
    """
    plant = get_plant_tf()
    controller = get_pid_tf()
    loop = _tf_multiply(controller, plant)

    if delay > 0:
        pade_tf = pade_approximation(delay, order=pade_order)
        loop = _tf_multiply(loop, pade_tf)

    return loop


def compare_margins(
    delays: list[float] | None = None,
) -> list[dict]:
    """Compute gain/phase margins for multiple delay values.

    Returns list of dicts with keys: delay, gm_db, gm_freq, pm_deg, pm_freq.
    """
    from gds_analysis.linear import gain_margin, phase_margin

    if delays is None:
        delays = [0.0, 0.02, 0.05, 0.1]

    results = []
    for tau in delays:
        loop = get_loop_tf(delay=tau)
        gm_db, gm_freq = gain_margin(loop.num, loop.den)
        pm_deg, pm_freq = phase_margin(loop.num, loop.den)
        results.append(
            {
                "delay": tau,
                "gm_db": gm_db,
                "gm_freq": gm_freq,
                "pm_deg": pm_deg,
                "pm_freq": pm_freq,
            }
        )
    return results


def get_nyquist_data(
    delay: float = 0.05,
) -> tuple[list[float], list[float]]:
    """Compute Nyquist plot data for the delayed loop TF.

    Returns (real_parts, imag_parts) of L(jw).
    """

    loop = get_loop_tf(delay=delay)

    # Build a state-space from the TF for frequency_response
    # For simplicity, use the TF coefficients directly
    import numpy as np

    w = np.logspace(-2, 3, 2000)
    s_vals = 1j * w

    # Evaluate L(jw) directly from polynomial coefficients
    num = np.array(loop.num)
    den = np.array(loop.den)

    def eval_poly(coeffs, s):
        n = len(coeffs) - 1
        return sum(c * s ** (n - i) for i, c in enumerate(coeffs))

    H = np.array([eval_poly(num, s) / eval_poly(den, s) for s in s_vals])

    return np.real(H).tolist(), np.imag(H).tolist()


if __name__ == "__main__":
    print("=== Lesson 5: Sensor Delay and Stability Margins ===\n")

    # --- Pade approximation ---
    pade = pade_approximation(0.05, order=3)
    print("Pade(tau=0.05s, order=3):")
    print(f"  num = {[f'{c:.6f}' for c in pade.num]}")
    print(f"  den = {[f'{c:.6f}' for c in pade.den]}")

    # --- Margin comparison ---
    print(
        f"\n{'Delay':>8}  {'GM (dB)':>10}  {'GM freq':>10}  "
        f"{'PM (deg)':>10}  {'PM freq':>10}"
    )
    print("-" * 58)

    margins = compare_margins()
    for m in margins:
        gm = f"{m['gm_db']:.1f}" if m["gm_db"] != float("inf") else "inf"
        pm = f"{m['pm_deg']:.1f}" if m["pm_deg"] != float("inf") else "inf"
        gf = f"{m['gm_freq']:.2f}" if m["gm_freq"] == m["gm_freq"] else "n/a"
        pf = f"{m['pm_freq']:.2f}" if m["pm_freq"] == m["pm_freq"] else "n/a"
        print(f"{m['delay']:8.3f}  {gm:>10}  {gf:>10}  {pm:>10}  {pf:>10}")

    # --- Stability warning ---
    for m in margins:
        if m["pm_deg"] != float("inf") and m["pm_deg"] < 30:
            print(
                f"\n  WARNING: Phase margin at delay={m['delay']}s is "
                f"{m['pm_deg']:.1f} deg — below 30 deg safety threshold!"
            )

    print("\n  As delay increases, phase margin shrinks.")
    print("  At some point the system becomes unstable.")
    print("  This is why sensor bandwidth matters in control design.")

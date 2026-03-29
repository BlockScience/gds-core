"""Gordon-Schaefer Fishery — Variant 3: Disturbed.

Adds environmental disturbance to the regulated fishery (V2). The
disturbance is an exogenous shock to the growth rate that bypasses
all decision-makers — fishers cannot observe it before deciding,
the regulator cannot prevent it. It enters the state update directly.

STATUS: Stub — requires roadmap features before implementation.

TODO (T1-3 — Disturbance formalization, #161):
    - BoundaryAction with tags={"role": "disturbance"} convention
    - DST-001 domain check: disturbance must not wire to Policy blocks
    - CanonicalGDS gains disturbance_ports field
    - project_canonical() partitions input_ports into U_c (controlled) and W (disturbance)
    - Extended canonical: f: X x D x W -> X (disturbance enters f directly)

TODO (T2-2 — Behavioral verification, #164):
    - BV-001 (universal invariant): N >= 0 for all timesteps
      Expected: PASS for small disturbance, FAIL for large disturbance
    - BV-002 (fixed-point): stock converges to steady state
      Expected: PASS under normal conditions, FAIL under persistent shock
    - BehavioralPredicate protocol: DSL registers concrete predicates
    - Abstract check runner in gds-analysis

TODO (T2-4 — Continuous-time formalization, #166):
    - Same fishery as continuous-time ODE:
        dN/dt = (r + w(t)) * N * (1 - N/K) - q * E * N - m * N
    - ExecutionContract(time_domain="continuous")
    - SolverInterface protocol in gds-continuous
    - spec_to_ode_model() adapter
    - Verify discrete and continuous converge to same steady state
"""

from gds.blocks.roles import BoundaryAction, Policy
from gds.spec import GDSSpec
from gds.types.interface import Interface, port

# --- Disturbance block ---
# TODO(T1-3): Add tags={"role": "disturbance"} once the tagging
# convention is formalized and DST-001 check exists.
#
# environmental_shock = BoundaryAction(
#     name="Environmental Shock",
#     interface=Interface(
#         forward_out=(port("Growth Rate Perturbation"),),
#     ),
#     tags={"role": "disturbance", "domain": "Environment"},
# )
#
# Routing: Environmental Shock wires DIRECTLY to Growth Rate (which
# feeds Population Dynamics). It does NOT wire to any Policy block.
# DST-001 verifies this invariant.
#
# The growth rate computation becomes:
#   G = (r + w) * N * (1 - N/K) - m * N
# where w is the disturbance signal.

environmental_shock_stub = BoundaryAction(
    name="Environmental Shock",
    interface=Interface(
        forward_out=(port("Growth Rate Perturbation"),),
    ),
    tags={"domain": "Environment", "note": "Should have role=disturbance tag after T1-3"},
)

# --- Modified growth rate (accepts disturbance input) ---

growth_rate_disturbed = Policy(
    name="Growth Rate",
    interface=Interface(
        forward_in=(
            port("Population Level"),
            port("Growth Rate Perturbation"),
        ),
        forward_out=(port("Natural Growth"),),
    ),
    params_used=["r", "K", "m"],
    tags={"domain": "Computation"},
)

# TODO(T2-2): Behavioral predicates
#
# from gds_analysis.behavioral import BehavioralPredicate
#
# class StockNonNegativity(BehavioralPredicate):
#     """BV-001: Fish stock must remain non-negative at all timesteps."""
#     channel = "Fish Population Level"
#     check_type = "invariant"
#
#     def evaluate(self, value):
#         return value >= 0
#
# class StockConvergence(BehavioralPredicate):
#     """BV-002: Fish stock should converge to steady state."""
#     channel = "Fish Population Level"
#     check_type = "fixed_point"
#
#     def converged(self, prev, curr):
#         return abs(curr - prev) < 1.0  # within 1 tonne

# TODO(T2-2): Falsification test cases
#
# | System configuration          | BV-001 (N>=0) | BV-002 (converge) |
# |-------------------------------|---------------|-------------------|
# | Small disturbance (sigma=0.1) | PASS          | PASS              |
# | Large disturbance (sigma=2.0) | FAIL          | FAIL              |
# | No disturbance, r > 2        | PASS          | FAIL (oscillation)|
# | Optimal quota, no disturbance | PASS          | PASS              |

# TODO(T2-4): Continuous-time variant
#
# from gds.execution import ExecutionContract
#
# continuous_contract = ExecutionContract(time_domain="continuous")
#
# The continuous-time ODE:
#   dN/dt = (r + w(t)) * N * (1 - N/K) - q * E * N - m * N
#
# Same wiring topology. Same canonical decomposition. Different solver.
# Verify: discrete (gds-sim) and continuous (gds-continuous) converge
# to the same steady state within solver tolerance.
#
# from gds_continuous.solver import SolverInterface, RK4Solver
# from gds_analysis.adapter import spec_to_ode_model
#
# ode_model = spec_to_ode_model(spec)
# results = ode_model.simulate(solver=RK4Solver(), t_span=(0, 100))
# assert abs(results.final("N") - N_MSY) < tolerance


def build_v3_spec() -> GDSSpec:
    """Build disturbed fishery spec.

    Blocked on: T1-3 (disturbance tags), T2-2 (behavioral verification).
    Currently returns a stub without formal disturbance semantics.
    """
    from model import build_spec

    spec = build_spec()

    # Add disturbance block (without formal tagging until T1-3)
    spec.register_block(environmental_shock_stub)

    return spec

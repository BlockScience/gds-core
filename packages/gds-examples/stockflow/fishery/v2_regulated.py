"""Gordon-Schaefer Fishery — Variant 2: Regulated.

Adds a regulator who observes total catch (ControlAction output map)
and sets a quota (control action on fishers). This variant exercises
the controller-plant duality: catch observation is simultaneously the
system's output and the regulator's input.

STATUS: Partial — T0-3 (ControlAction) is implemented. Remaining TODOs
below require further roadmap items.

Duality at work:
    From INSIDE the fishery, Catch Observation is an output map y = C(N, H) —
    it produces the observable signal y.
    From OUTSIDE (the regulator's perspective), y is the input signal the
    regulator acts on. This perspective inversion occurs at the >> boundary
    between the fishery subsystem and the regulator.

TODO (T1-1 — ExecutionContract, #159):
    - Attach ExecutionContract to GDSSpec:
        ExecutionContract(time_domain="discrete", synchrony="synchronous",
                          update_ordering="Moore")
    - SC-011: cross-composition contract compatibility
    - gds-sim validation gate: read contract before running

TODO (T1-2 — PSUU connection to Theta, #160):
    - ParameterSpace.from_parameter_schema() to derive sweep bounds from spec
    - ParameterSpace.validate_against_schema() before sweeping quota
    - PSUU-001 check: swept space ⊆ declared Theta

TODO (T2-1 — Structural reachability, #163):
    - structural_reachability(system_ir): can disturbance reach stock?
    - structural_distinguishability(system_ir): can regulator observe profit?
      (Answer: No — profit has no path to Catch Observation)

TODO (T2-3 — Cross-lens queries, #165):
    - is_nash_equilibrium_a_fixed_point(pattern_ir, canonical_gds)
      Expected: True (Nash at N_MSY under optimal quota)
    - is_stable_attractor_incentive_compatible(canonical_gds, pattern_ir, N_MSY)
      Expected: True (under quota, MSY IS incentive-compatible)
"""

from gds.blocks.roles import ControlAction, Policy
from gds.canonical import CanonicalGDS, project_canonical
from gds.spec import GDSSpec
from gds.types.interface import Interface, port

# --- ControlAction: Catch Observation is the output map y = C(N, H) ---

catch_observation = ControlAction(
    name="Catch Observation",
    interface=Interface(
        forward_in=(port("Total Harvest"), port("Population Level")),
        forward_out=(port("Observed Total Catch"),),
    ),
    observes=[("Fish Population", "level")],
    tags={"domain": "Observation"},
)

# --- Policy: Regulator sets quota based on observed catch ---

regulator_policy = Policy(
    name="Regulator Policy",
    interface=Interface(
        forward_in=(port("Observed Total Catch"),),
        forward_out=(port("Quota Signal"),),
    ),
    params_used=["N_target"],
    tags={"domain": "Regulation"},
)

# TODO(T1-1): Attach ExecutionContract to the compiled GDSSpec
#
# from gds.execution import ExecutionContract  # does not exist yet
#
# contract = ExecutionContract(
#     time_domain="discrete",
#     synchrony="synchronous",
#     observation_delay=0,
#     update_ordering="Moore",
# )
# spec.execution_contract = contract

# TODO(T1-2): PSUU sweep over quota parameter
#
# from gds_psuu.space import ParameterSpace, Continuous
#
# space = ParameterSpace.from_parameter_schema(spec.parameter_schema)
# space = ParameterSpace(params={
#     "N_target": Continuous(10_000, 80_000),
# })
# violations = space.validate_against_schema(spec.parameter_schema)
# assert len(violations) == 0, f"PSUU-001 violations: {violations}"

# TODO(T2-1): Structural distinguishability query
#
# from gds_analysis.structural import structural_distinguishability
# dist = structural_distinguishability(system_ir)
# assert ("Fish Population", "level") in dist  # regulator CAN observe stock (via catch)
# assert ("Fisher 1", "cumulative_profit") not in dist  # regulator CANNOT observe profit

# TODO(T2-3): Cross-lens queries (the publishable result)
#
# from gds_analysis.cross_lens import CrossLensQuery
# query = CrossLensQuery(pattern_ir, canonical_gds)
#
# # Under optimal quota Q* = rK/4:
# assert query.is_nash_equilibrium_a_fixed_point()  # True
# assert query.is_stable_attractor_incentive_compatible(
#     attractor_state={"Fish Population": {"level": N_MSY}}
# )  # True — regulation aligns the lenses


def build_v2_spec() -> GDSSpec:
    """Build regulated fishery spec.

    Extends V1 (unregulated) with:
    - Catch Observation (ControlAction) — output map y = C(N, H)
    - Regulator Policy — quota decision based on observed catch

    Blocked on: T1-1 (ExecutionContract) for full execution semantics.
    """
    from fishery.model import build_spec

    spec = build_spec()
    spec.register_block(catch_observation)
    spec.register_block(regulator_policy)

    from gds.parameters import ParameterDef
    from fishery.model import Biomass

    spec.register_parameter(
        ParameterDef(
            name="N_target",
            typedef=Biomass,
            description="Target stock level for regulator",
            bounds=(0.0, 100_000.0),
        )
    )

    return spec


def build_v2_canonical() -> CanonicalGDS:
    """Project canonical form — should now include output_ports from ControlAction."""
    return project_canonical(build_v2_spec())

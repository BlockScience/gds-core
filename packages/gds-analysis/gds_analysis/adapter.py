"""Adapt GDSSpec structural annotations to gds-sim execution primitives.

The adapter reads the block composition, wiring topology, and structural
annotations from a GDSSpec and produces a gds_sim.Model that can be run.

Users must supply the behavioral functions (policies, SUFs) that
gds-framework deliberately leaves as R3. The adapter wires them together
using the structural skeleton.

State Key Convention
--------------------
State dict keys use the format ``"EntityName.VariableName"`` throughout
gds-analysis. This convention is used by:

- ``_default_initial_state()`` when building initial state from entities
- ``guarded_policy()`` when projecting state to ``depends_on`` fields
- ``_extract_metric_state()`` when extracting metric variables
- ``_state_fingerprint()`` when deduplicating reached states

SUF callables must return ``("EntityName.VariableName", value)`` tuples
matching this convention.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds_sim import Model
from gds_sim.types import StateUpdateBlock

from gds_analysis.constraints import guarded_policy

if TYPE_CHECKING:
    from gds import GDSSpec


def spec_to_model(
    spec: GDSSpec,
    *,
    policies: dict[str, Any] | None = None,
    sufs: dict[str, Any] | None = None,
    initial_state: dict[str, Any] | None = None,
    params: dict[str, list[Any]] | None = None,
    enforce_constraints: bool = True,
) -> Model:
    """Build a gds_sim.Model from a GDSSpec and user-supplied functions.

    Parameters
    ----------
    spec
        The GDS specification with registered blocks, wirings, and
        structural annotations.
    policies
        Mapping of block name -> policy callable. Required for every
        BoundaryAction, Policy, and ControlAction block.
    sufs
        Mapping of block name -> state update callable. Required for
        every Mechanism block.
    initial_state
        Initial state dict. If None, builds a zero-valued state from
        the spec's entities and variables.
    params
        Parameter sweep dict (passed through to gds_sim.Model).
    enforce_constraints
        If True, wrap BoundaryAction policies with
        AdmissibleInputConstraint guards.

    Returns
    -------
    gds_sim.Model
        A runnable simulation model.

    Raises
    ------
    ValueError
        If required policies or SUFs are missing.
    """
    policies = policies or {}
    sufs = sufs or {}

    if initial_state is None:
        initial_state = _default_initial_state(spec)

    blocks = _build_state_update_blocks(spec, policies, sufs, enforce_constraints)

    return Model(
        initial_state=initial_state,
        state_update_blocks=blocks,
        params=params or {},
    )


def _default_initial_state(spec: GDSSpec) -> dict[str, Any]:
    """Build a zero-valued initial state from spec entities."""
    state: dict[str, Any] = {}
    for entity in spec.entities.values():
        for var_name, sv in entity.variables.items():
            key = f"{entity.name}.{var_name}"
            python_type = sv.typedef.python_type
            if python_type is float:
                state[key] = 0.0
            elif python_type is int:
                state[key] = 0
            elif python_type is bool:
                state[key] = False
            else:
                state[key] = ""
    return state


def _build_state_update_blocks(
    spec: GDSSpec,
    policies: dict[str, Any],
    sufs: dict[str, Any],
    enforce_constraints: bool,
) -> list[StateUpdateBlock]:
    """Map spec blocks to gds-sim StateUpdateBlocks.

    All blocks are packed into a single StateUpdateBlock. All policies
    run in parallel (signal aggregation via dict.update), then all SUFs
    run. Multi-wiring topologies with sequential tier dependencies are
    not yet modeled — this is a known simplification.
    """
    block_policies: dict[str, Any] = {}
    block_sufs: dict[str, Any] = {}

    for name, block in spec.blocks.items():
        if isinstance(block, (BoundaryAction, Policy, ControlAction)):
            if name not in policies:
                raise ValueError(
                    f"Missing policy function for block '{name}' "
                    f"({type(block).__name__})"
                )
            fn = policies[name]
            if enforce_constraints and isinstance(block, BoundaryAction):
                fn = _apply_constraint_guard(spec, name, fn)
            elif enforce_constraints and not isinstance(block, BoundaryAction):
                # Warn if constraints were registered for non-BoundaryAction
                mismatched = [
                    ac
                    for ac in spec.admissibility_constraints.values()
                    if ac.boundary_block == name
                ]
                if mismatched:
                    warnings.warn(
                        f"AdmissibleInputConstraint targets block "
                        f"'{name}' ({type(block).__name__}), but "
                        f"constraints are only enforced on "
                        f"BoundaryAction blocks.",
                        stacklevel=3,
                    )
            block_policies[name] = fn

        elif isinstance(block, Mechanism):
            if name not in sufs:
                raise ValueError(
                    f"Missing state update function for block '{name}' (Mechanism)"
                )
            # Key by target state variable, not block name.
            # gds-sim validates that SUF dict keys exist in
            # initial_state.
            #
            # WARNING: if a Mechanism updates multiple variables,
            # the same SUF is registered for each. The SUF must
            # return the correct (key, value) for each state_key.
            # gds-sim calls each SUF independently.
            if len(block.updates) > 1:
                warnings.warn(
                    f"Mechanism '{name}' updates "
                    f"{len(block.updates)} variables. The same "
                    f"SUF will be called once per variable — "
                    f"ensure it returns the correct key each time.",
                    stacklevel=3,
                )
            for entity_name, var_name in block.updates:
                state_key = f"{entity_name}.{var_name}"
                block_sufs[state_key] = sufs[name]

    return [
        StateUpdateBlock(
            policies=block_policies,
            variables=block_sufs,
        )
    ]


def _apply_constraint_guard(
    spec: GDSSpec,
    block_name: str,
    policy_fn: Any,
) -> Any:
    """Wrap a policy with AdmissibleInputConstraint guards."""
    constraints = [
        ac
        for ac in spec.admissibility_constraints.values()
        if ac.boundary_block == block_name and ac.constraint is not None
    ]
    if not constraints:
        return policy_fn

    return guarded_policy(policy_fn, constraints)

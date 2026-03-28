"""Hypothesis strategies for generating random GDS objects.

Used by property-based round-trip tests to verify that the OWL export/import
preserves structural fidelity across randomly generated specifications.

See: docs/research/verification-plan.md (Phase 3a)
"""

from hypothesis import strategies as st

import gds
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    interface,
)

# ---------------------------------------------------------------------------
# Atomic strategies
# ---------------------------------------------------------------------------

# Simple identifiers for names (no spaces, no delimiters)
# Filter out Python keyword args used by gds factory functions
_reserved = {"name", "description", "symbol"}
_ident = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=2,
    max_size=8,
).filter(lambda s: s not in _reserved)

# Port names: single-token lowercase words (no + or , delimiters)
_port_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=2,
    max_size=10,
)

# Python types that round-trip cleanly through OWL (gds-owl built-in type map)
_python_types = st.sampled_from([int, float, str, bool])


# ---------------------------------------------------------------------------
# GDSSpec
# ---------------------------------------------------------------------------


@st.composite
def gds_specs(draw, min_blocks=3, max_blocks=5) -> GDSSpec:
    """Generate a random, structurally valid GDSSpec.

    Produces a spec with:
    - 1-3 TypeDefs
    - 1-2 Spaces referencing drawn types
    - 1 Entity referencing a drawn space
    - min_blocks..max_blocks blocks (1 BoundaryAction, 1+ Policy,
      1 Mechanism)
    - 1 SpecWiring connecting blocks sequentially

    All R3 fields (constraints) are None by design — lossiness of
    real constraints is covered by fixture tests in test_roundtrip.py.
    """
    # --- Types ---
    n_types = draw(st.integers(min_value=1, max_value=3))
    type_names = draw(
        st.lists(
            _ident, min_size=n_types, max_size=n_types, unique=True
        )
    )
    types = [
        gds.typedef(
            tname,
            draw(_python_types),
            units=draw(st.one_of(st.none(), _ident)),
        )
        for tname in type_names
    ]

    # --- Spaces ---
    n_spaces = draw(st.integers(min_value=1, max_value=2))
    space_names = draw(
        st.lists(
            _ident, min_size=n_spaces, max_size=n_spaces, unique=True
        )
    )
    spaces = []
    for sname in space_names:
        n_fields = draw(st.integers(min_value=1, max_value=2))
        field_names = draw(
            st.lists(
                _ident,
                min_size=n_fields,
                max_size=n_fields,
                unique=True,
            )
        )
        fields = {
            fname: draw(st.sampled_from(types))
            for fname in field_names
        }
        spaces.append(gds.space(sname, **fields))

    # --- Entity ---
    entity_name = draw(_ident)
    n_vars = draw(st.integers(min_value=1, max_value=2))
    var_names = draw(
        st.lists(
            _ident, min_size=n_vars, max_size=n_vars, unique=True
        )
    )
    variables = {
        vname: gds.state_var(draw(st.sampled_from(types)))
        for vname in var_names
    }
    entity = gds.entity(entity_name, **variables)

    # --- Blocks ---
    n_blocks = draw(
        st.integers(min_value=min_blocks, max_value=max_blocks)
    )
    port_names = draw(
        st.lists(
            _port_name,
            min_size=n_blocks,
            max_size=n_blocks,
            unique=True,
        )
    )
    block_names = draw(
        st.lists(
            _ident, min_size=n_blocks, max_size=n_blocks, unique=True
        )
    )

    blocks = []

    # First block: BoundaryAction (no forward_in)
    blocks.append(
        BoundaryAction(
            name=block_names[0],
            interface=interface(forward_out=[port_names[0]]),
        )
    )

    # Middle blocks: Policy (forward_in from prev, forward_out to next)
    for i in range(1, n_blocks - 1):
        blocks.append(
            Policy(
                name=block_names[i],
                interface=interface(
                    forward_in=[port_names[i - 1]],
                    forward_out=[port_names[i]],
                ),
            )
        )

    # Last block: Mechanism (forward_in from previous)
    update_var = draw(st.sampled_from(list(variables.keys())))
    last_in = port_names[-2] if n_blocks > 2 else port_names[0]
    blocks.append(
        Mechanism(
            name=block_names[-1],
            interface=interface(forward_in=[last_in]),
            updates=[(entity_name, update_var)],
        )
    )

    # --- Wiring ---
    wires = []
    for i in range(len(blocks) - 1):
        space_for_wire = draw(st.sampled_from(spaces))
        wires.append(
            Wire(
                source=blocks[i].name,
                target=blocks[i + 1].name,
                space=space_for_wire.name,
            )
        )

    wiring = SpecWiring(
        name="main",
        block_names=[b.name for b in blocks],
        wires=wires,
    )

    # --- Assemble spec ---
    spec_name = draw(_ident)
    spec = GDSSpec(name=spec_name)
    for t in types:
        spec.collect(t)
    for s in spaces:
        spec.collect(s)
    spec.collect(entity)
    for b in blocks:
        spec.collect(b)
    spec.register_wiring(wiring)

    return spec

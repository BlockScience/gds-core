"""Cross-Domain Canonical Comparison — the Rosetta Stone.

Side-by-side canonical analysis of the resource pool modeled in all
three DSLs (stock-flow, control, game theory). Each DSL compiles to
a GDSSpec, and project_canonical() extracts the formal h = f . g
decomposition. This module prints a comparison table showing how the
same real-world concept maps to different mathematical structures.

The key insight: all three views share the same underlying GDS structure
(blocks with typed interfaces, composed via operators) but decompose
the resource management problem differently:

    Stock-Flow:  Accumulation dynamics (X changes via rates)
    Control:     Regulation dynamics (X tracks a reference)
    Game Theory: Strategic interaction (no X, pure policy)
"""

from gds.canonical import CanonicalGDS, project_canonical
from guides.rosetta.control_view import build_spec as build_control_spec
from guides.rosetta.game_view import build_spec as build_game_spec
from guides.rosetta.stockflow_view import build_spec as build_sf_spec


def build_all_canonicals() -> dict[str, CanonicalGDS]:
    """Build canonical projections for all three views."""
    return {
        "Stock-Flow": project_canonical(build_sf_spec()),
        "Control": project_canonical(build_control_spec()),
        "Game Theory": project_canonical(build_game_spec()),
    }


def canonical_spectrum_table() -> str:
    """Generate a formatted comparison table of canonical spectra.

    Columns: View, |X|, |U|, |g|, |f|, Form, Character
    """
    canonicals = build_all_canonicals()

    rows: list[tuple[str, int, int, int, int, str, str]] = []
    for view_name, c in canonicals.items():
        x_dim = len(c.state_variables)
        u_dim = len(c.input_ports)
        g_dim = len(c.policy_blocks)
        f_dim = len(c.mechanism_blocks)

        if f_dim > 0 and g_dim > 0:
            form = "h = f . g"
            character = "Dynamical"
        elif f_dim == 0 and g_dim > 0:
            form = "h = g"
            character = "Strategic"
        elif g_dim == 0 and f_dim > 0:
            form = "h = f"
            character = "Autonomous"
        else:
            form = "h = id"
            character = "Trivial"

        if c.has_parameters:
            form = form.replace("h", "h_theta")

        rows.append((view_name, x_dim, u_dim, g_dim, f_dim, form, character))

    # Format table
    header = (
        f"{'View':<15} {'|X|':>4} {'|U|':>4} {'|g|':>4} {'|f|':>4}"
        f"  {'Form':<20} {'Character':<12}"
    )
    separator = "-" * len(header)
    lines = [header, separator]
    for row in rows:
        lines.append(
            f"{row[0]:<15} {row[1]:>4} {row[2]:>4} {row[3]:>4} {row[4]:>4}"
            f"  {row[5]:<20} {row[6]:<12}"
        )
    return "\n".join(lines)


def print_comparison() -> None:
    """Print the full cross-domain comparison to stdout."""
    print("=" * 72)
    print("  Cross-Domain Rosetta Stone: Resource Pool")
    print("=" * 72)
    print()
    print("Canonical Spectrum:")
    print()
    print(canonical_spectrum_table())
    print()

    canonicals = build_all_canonicals()
    for view_name, c in canonicals.items():
        print(f"\n--- {view_name} ---")
        print(f"  Formula:    {c.formula()}")
        print(f"  State X:    {list(c.state_variables)}")
        print(f"  Input U:    {list(c.input_ports)}")
        print(f"  Boundary:   {list(c.boundary_blocks)}")
        print(f"  Policy g:   {list(c.policy_blocks)}")
        print(f"  Mechanism f:{list(c.mechanism_blocks)}")
        if c.update_map:
            print(f"  Updates:    {list(c.update_map)}")
    print()


if __name__ == "__main__":
    print_comparison()

"""Stage 4 — Verification and Visualization.

Run structural and semantic checks on the thermostat model, then
generate Mermaid diagrams showing three different views of the system.

New concepts:
    - Generic checks (G-001..G-006) on SystemIR — structural topology
    - Semantic checks (SC-001..SC-007) on GDSSpec — domain properties
    - verify() engine and VerificationReport
    - gds-viz: system_to_mermaid, spec_to_mermaid, canonical_to_mermaid

Verification answers: "Is my specification well-formed?"
    - G-001: Do wiring labels match source/target port types?
    - G-003: Are direction flags consistent (no covariant feedback)?
    - G-004: Do all wiring endpoints reference known blocks?
    - G-005: In sequential composition, do types match both sides?
    - G-006: Is the covariant flow graph acyclic (a DAG)?
    - SC-001: Is every state variable updated by some mechanism?
    - SC-002: Are there write conflicts (two mechanisms updating same var)?
    - SC-004: Do wire space references resolve?
    - SC-005: Do block parameter references resolve?
    - SC-006: Does the mechanism layer f exist?
    - SC-007: Is the state space X non-empty?

Visualization answers: "What does my system look like?"
    - Structural view: compiled block graph with wiring arrows
    - Architecture view: blocks grouped by GDS role
    - Canonical view: mathematical decomposition X_t -> U -> g -> f -> X_{t+1}
"""

from gds.canonical import project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds.verification.engine import verify
from gds.verification.findings import VerificationReport
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
    check_parameter_references,
    check_type_safety,
)
from gds_viz import canonical_to_mermaid, spec_to_mermaid, system_to_mermaid


def run_generic_checks(system: SystemIR) -> VerificationReport:
    """Run generic structural checks G-001..G-006 on the SystemIR.

    These checks validate the topology of the compiled block graph
    without any domain-specific knowledge. They catch wiring mismatches,
    dangling references, direction contradictions, and cycles.

    Note: G-002 (signature completeness) is skipped because BoundaryActions
    legitimately have no forward_in and terminal Mechanisms may have no
    forward_out.
    """
    checks = [
        check_g001_domain_codomain_matching,
        check_g003_direction_consistency,
        check_g004_dangling_wirings,
        check_g005_sequential_type_compatibility,
        check_g006_covariant_acyclicity,
    ]
    return verify(system, checks=checks)


def run_semantic_checks(spec: GDSSpec) -> list[str]:
    """Run semantic checks on the GDSSpec.

    These checks validate domain-level properties:
    - Completeness: every variable is updated by some mechanism
    - Determinism: no two mechanisms update the same variable in one wiring
    - Type safety: wire space references are valid
    - Parameter references: block params_used entries resolve
    - Canonical wellformedness: f and X are non-empty

    Returns a list of human-readable result strings.
    """
    results: list[str] = []

    for check_fn in [
        check_completeness,
        check_determinism,
        check_type_safety,
        check_parameter_references,
        check_canonical_wellformedness,
    ]:
        findings = check_fn(spec)
        for f in findings:
            status = "PASS" if f.passed else "FAIL"
            results.append(f"[{f.check_id}] {status}: {f.message}")

    return results


def generate_structural_view(system: SystemIR) -> str:
    """Generate a Mermaid diagram of the compiled block graph.

    Shows blocks as nodes and wirings as arrows. Block shapes indicate
    roles: stadium for BoundaryAction, double-bracket for Mechanism.
    Temporal wirings appear as dashed arrows.
    """
    return system_to_mermaid(system)


def generate_architecture_view(spec: GDSSpec) -> str:
    """Generate an architecture diagram with blocks grouped by GDS role.

    Blocks are organized into subgraphs: Boundary (U), Policy (g),
    Mechanism (f). Entity cylinders show state variables. Wires show
    data dependencies.
    """
    return spec_to_mermaid(spec)


def generate_canonical_view(spec: GDSSpec) -> str:
    """Generate the canonical GDS diagram: X_t -> U -> g -> f -> X_{t+1}.

    Shows the formal mathematical decomposition with parameter space
    Theta, role subgraphs, and update edges from mechanisms to X_{t+1}.
    """
    canonical = project_canonical(spec)
    return canonical_to_mermaid(canonical)


if __name__ == "__main__":
    from guides.getting_started.stage3_dsl import build_spec, build_system

    spec = build_spec()
    system = build_system()

    # Run verification
    print("=== Generic Checks (SystemIR) ===")
    report = run_generic_checks(system)
    print(f"Passed: {report.checks_passed}/{report.checks_total}")
    print(f"Errors: {report.errors}")
    for f in report.findings:
        status = "PASS" if f.passed else "FAIL"
        print(f"  [{f.check_id}] {status}: {f.message}")

    print("\n=== Semantic Checks (GDSSpec) ===")
    for line in run_semantic_checks(spec):
        print(f"  {line}")

    # Generate visualizations
    print("\n=== Structural View ===")
    print(generate_structural_view(system))

    print("\n=== Architecture View ===")
    print(generate_architecture_view(spec))

    print("\n=== Canonical View ===")
    print(generate_canonical_view(spec))

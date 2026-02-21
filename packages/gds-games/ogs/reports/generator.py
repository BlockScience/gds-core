"""Report generator — produces Markdown documentation from a PatternIR.

Generates six report types from Jinja2 templates:

1. **System Overview** — high-level summary with composition formula,
   lifecycle stages, flowchart, sequence diagram, and verification results.
2. **Interface Contracts** — per-game incoming/outgoing flow specifications.
3. **Schema Catalog** — data spaces grouped by flow label.
4. **State Machine** — execution sequence, GDS functions, feedback loops,
   and initial conditions.
5. **Implementation Checklist** — actionable TODO list for each game,
   terminal conditions, decision spaces, and constraints.
6. **Verification Summary** — detailed pass/fail results for all checks.

The CLI ``ogs report`` command calls ``generate_reports()`` which writes
all requested report types to an output directory.
"""

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, PackageLoader

from ogs.ir.models import FlowIR, PatternIR
from ogs.reports.domain_analysis import generate_domain_analysis
from ogs.reports.mermaid import generate_flowchart, generate_sequence_diagram
from ogs.verification.engine import verify
from ogs.verification.findings import VerificationReport


@dataclass
class FlowGroup:
    """Incoming and outgoing flows for a game."""

    incoming: list[FlowIR] = field(default_factory=list)
    outgoing: list[FlowIR] = field(default_factory=list)


def _build_flows_by_game(pattern: PatternIR) -> dict[str, FlowGroup]:
    """Group flows by game name for the interface contracts template."""
    groups: dict[str, FlowGroup] = {g.name: FlowGroup() for g in pattern.games}
    for flow in pattern.flows:
        if flow.target in groups:
            groups[flow.target].incoming.append(flow)
        if flow.source in groups:
            groups[flow.source].outgoing.append(flow)
    return groups


def _build_composition_formula(pattern: PatternIR) -> str:
    """Build a human-readable composition formula using mathematical notation.

    Maps composition types to their standard symbols:
    sequential → ``;``, parallel → ``⊗``, feedback → ``feedback(...)``,
    corecursive → ``corec(...)``.
    """
    game_names = [g.name for g in pattern.games]
    if not game_names:
        return "∅"

    comp = pattern.composition_type.value
    if comp == "sequential":
        return " ; ".join(game_names)
    elif comp == "parallel":
        return " ⊗ ".join(game_names)
    elif comp == "feedback":
        sequential = " ; ".join(game_names)
        return f"feedback({sequential})"
    elif comp == "corecursive":
        return f"corec({', '.join(game_names)})"
    return " ; ".join(game_names)


def _build_lifecycle_stages(pattern: PatternIR) -> list[str]:
    """Derive lifecycle stages from topological order of covariant flows."""
    from ogs.reports.mermaid import _topological_sort

    game_names = [g.name for g in pattern.games]
    return _topological_sort(game_names, pattern.flows)


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment loading from the templates directory."""
    return Environment(
        loader=PackageLoader("ogs.reports", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_system_overview(
    pattern: PatternIR,
    report: VerificationReport | None = None,
) -> str:
    """Render the system overview report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("system_overview.md.j2")

    failed_findings = []
    if report:
        failed_findings = [f for f in report.findings if not f.passed]

    return template.render(
        pattern=pattern,
        composition_formula=_build_composition_formula(pattern),
        lifecycle_stages=_build_lifecycle_stages(pattern),
        flowchart=generate_flowchart(pattern),
        sequence_diagram=generate_sequence_diagram(pattern),
        verification=report,
        failed_findings=failed_findings,
    )


def generate_interface_contracts(pattern: PatternIR) -> str:
    """Render the interface contracts report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("interface_contracts.md.j2")

    return template.render(
        pattern=pattern,
        flows_by_game=_build_flows_by_game(pattern),
    )


def _build_spaces(pattern: PatternIR) -> dict[str, dict]:
    """Build per-space data for the schema catalog.

    Groups flows by their label (as the space name), with source/target info.
    """
    spaces: dict[str, dict] = {}
    for flow in pattern.flows:
        label = flow.label or flow.flow_type.value
        if label not in spaces:
            spaces[label] = {"flows": []}
        spaces[label]["flows"].append(
            {
                "label": label,
                "direction": flow.direction.value,
                "source": flow.source,
                "target": flow.target,
                "flow_type": flow.flow_type.value,
            }
        )
    return spaces


def generate_schema_catalog(pattern: PatternIR) -> str:
    """Render the data schema catalog report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("schema_catalog.md.j2")

    return template.render(
        pattern=pattern,
        spaces=_build_spaces(pattern),
    )


def generate_state_machine(
    pattern: PatternIR,
    order_of_events: list[str] | None = None,
) -> str:
    """Render the state machine / execution sequence report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("state_machine.md.j2")

    gds_games = [g for g in pattern.games if g.gds_function]
    feedback_flows = [f for f in pattern.flows if f.is_feedback]
    has_feedback = bool(feedback_flows)

    return template.render(
        pattern=pattern,
        lifecycle_stages=_build_lifecycle_stages(pattern),
        sequence_diagram=generate_sequence_diagram(pattern),
        gds_games=gds_games,
        feedback_flows=feedback_flows,
        has_feedback=has_feedback,
        order_of_events=order_of_events or [],
    )


def generate_implementation_checklist(pattern: PatternIR) -> str:
    """Render the implementation checklist report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("implementation_checklist.md.j2")

    feedback_flows = [f for f in pattern.flows if f.is_feedback]
    has_feedback = bool(feedback_flows)

    # Collect all constraints by game
    all_constraints: dict[str, list[str]] = {}
    for game in pattern.games:
        if game.constraints:
            all_constraints[game.name] = game.constraints

    return template.render(
        pattern=pattern,
        feedback_flows=feedback_flows,
        has_feedback=has_feedback,
        all_constraints=all_constraints,
    )


def generate_verification_summary(
    pattern: PatternIR,
    report: VerificationReport | None = None,
) -> str:
    """Render the verification summary report as Markdown."""
    env = _get_jinja_env()
    template = env.get_template("verification_summary.md.j2")

    if report is None:
        report = verify(pattern)

    failed_findings = [f for f in report.findings if not f.passed]

    return template.render(
        pattern=pattern,
        report=report,
        failed_findings=failed_findings,
    )


def generate_reports(
    pattern: PatternIR,
    output_dir: Path,
    report_types: list[str] | None = None,
    verification_report: VerificationReport | None = None,
) -> list[Path]:
    """Generate all requested reports and write them to output_dir.

    Creates a subdirectory named after the pattern (slugified) and puts
    all reports in that subdirectory for organized storage.

    Args:
        pattern: The pattern to generate reports for.
        output_dir: Base directory to write reports into. A subdirectory
            for the pattern will be created here.
        report_types: List of report types to generate. Defaults to all.
            Options: "overview", "contracts", "schema", "state_machine",
            "checklist", "verification"
        verification_report: Optional pre-computed verification report.

    Returns:
        List of paths to generated report files.
    """
    all_types = [
        "overview",
        "contracts",
        "schema",
        "state_machine",
        "checklist",
        "verification",
        "domain_analysis",
    ]
    if report_types is None:
        report_types = all_types

    needs_verification = any(t in report_types for t in ("overview", "verification"))
    if verification_report is None and needs_verification:
        verification_report = verify(pattern)

    # Create pattern-specific subdirectory
    slug = pattern.name.lower().replace(" ", "_")
    pattern_dir = output_dir / slug
    pattern_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if "overview" in report_types:
        content = generate_system_overview(pattern, verification_report)
        path = pattern_dir / f"{slug}_system_overview.md"
        path.write_text(content)
        written.append(path)

    if "contracts" in report_types:
        content = generate_interface_contracts(pattern)
        path = pattern_dir / f"{slug}_interface_contracts.md"
        path.write_text(content)
        written.append(path)

    if "schema" in report_types:
        content = generate_schema_catalog(pattern)
        path = pattern_dir / f"{slug}_schema_catalog.md"
        path.write_text(content)
        written.append(path)

    if "state_machine" in report_types:
        content = generate_state_machine(pattern)
        path = pattern_dir / f"{slug}_state_machine.md"
        path.write_text(content)
        written.append(path)

    if "checklist" in report_types:
        content = generate_implementation_checklist(pattern)
        path = pattern_dir / f"{slug}_implementation_checklist.md"
        path.write_text(content)
        written.append(path)

    if "verification" in report_types:
        content = generate_verification_summary(pattern, verification_report)
        path = pattern_dir / f"{slug}_verification_summary.md"
        path.write_text(content)
        written.append(path)

    if "domain_analysis" in report_types:
        content = generate_domain_analysis(pattern)
        path = pattern_dir / f"{slug}_domain_analysis.md"
        path.write_text(content)
        written.append(path)

    return written

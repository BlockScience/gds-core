"""CLI entry point for the open-games package."""

import importlib.util
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="ogs",
    help="Open Games — typed DSL for compositional game theory.",
    no_args_is_help=True,
)


@app.command(name="compile")
def compile_dsl(
    dsl_file: Annotated[
        Path,
        typer.Argument(help="Path to a Python DSL file defining a 'pattern' variable"),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output IR JSON path")
    ] = None,
) -> None:
    """Compile a Python DSL file into IR JSON."""
    from ogs.dsl.compile import compile_to_ir
    from ogs.ir.serialization import IRDocument, IRMetadata, save_ir

    if not dsl_file.exists():
        typer.echo(f"Error: DSL file not found: {dsl_file}", err=True)
        raise typer.Exit(1)

    # Load the Python file as a module
    spec = importlib.util.spec_from_file_location("_dsl_input", dsl_file)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: could not load {dsl_file}", err=True)
        raise typer.Exit(1)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "pattern"):
        typer.echo(f"Error: {dsl_file} must define a 'pattern' variable", err=True)
        raise typer.Exit(1)

    ir = compile_to_ir(mod.pattern)
    doc = IRDocument(
        patterns=[ir],
        metadata=IRMetadata(source_canvases=[str(dsl_file)]),
    )

    out_path = output or Path(dsl_file.stem + ".json")
    save_ir(doc, out_path)
    typer.echo(f"IR written to {out_path}")
    typer.echo(f"  Pattern: {ir.name}")
    typer.echo(
        f"  Games: {len(ir.games)}, Flows: {len(ir.flows)}, Inputs: {len(ir.inputs)}"
    )


@app.command(name="verify")
def verify_cmd(
    ir_file: Annotated[Path, typer.Argument(help="Path to IR JSON file")],
) -> None:
    """Run verification checks against an IR file."""
    from ogs.ir.serialization import load_ir
    from ogs.verification.engine import verify
    from ogs.verification.findings import Severity

    if not ir_file.exists():
        typer.echo(f"Error: IR file not found: {ir_file}", err=True)
        raise typer.Exit(1)

    doc = load_ir(ir_file)

    for pattern in doc.patterns:
        report = verify(pattern)
        typer.echo(f"\nVerification: {report.pattern_name}")
        typer.echo(f"  Checks: {report.checks_passed}/{report.checks_total} passed")
        typer.echo(
            f"  Errors: {report.errors}, Warnings: {report.warnings}, "
            f"Info: {report.info_count}"
        )

        failed = [f for f in report.findings if not f.passed]
        if failed:
            typer.echo("\nFindings:")
            for f in failed:
                marker = (
                    "ERROR"
                    if f.severity == Severity.ERROR
                    else f.severity.value.upper()
                )
                typer.echo(f"  [{marker}] {f.check_id}: {f.message}")
        else:
            typer.echo("\n  All checks passed.")

        if report.errors > 0:
            raise typer.Exit(1)


@app.command()
def report(
    ir_file: Annotated[Path, typer.Argument(help="Path to IR JSON file")],
    output_dir: Annotated[
        Path, typer.Option("--output", "-o", help="Base output directory for reports")
    ] = Path("reports"),
    report_type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="Report type: all, overview, contracts, schema, "
            "state_machine, checklist, or verification",
        ),
    ] = "all",
) -> None:
    """Generate Markdown specification reports from an IR file.

    Creates a subdirectory for each pattern under the output directory,
    organizing all reports by pattern name.
    """
    from ogs.ir.serialization import load_ir
    from ogs.reports.generator import generate_reports

    if not ir_file.exists():
        typer.echo(f"Error: IR file not found: {ir_file}", err=True)
        raise typer.Exit(1)

    doc = load_ir(ir_file)
    types = None if report_type == "all" else [report_type]

    for pattern in doc.patterns:
        paths = generate_reports(pattern, output_dir, report_types=types)
        slug = pattern.name.lower().replace(" ", "_")
        typer.echo(f"\nReports for {pattern.name} in {output_dir}/{slug}/:")
        for p in paths:
            typer.echo(f"  {p.name}")


if __name__ == "__main__":
    app()

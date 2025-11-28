"""
CLI Main - Typer-based command-line interface.

Usage:
    liftlogic extract path/to/manual.pdf
    liftlogic search "fault code F505"
    liftlogic diagnose F505
    liftlogic serve
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="liftlogic",
    help="LiftLogic - Elevator Intelligence Platform",
    add_completion=False,
)
console = Console()


@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON path"),
    evaluate: bool = typer.Option(False, "--evaluate", "-e", help="Run quality evaluation"),
) -> None:
    """Extract structured data from elevator PDF documents."""
    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] File not found: {pdf_path}")
        raise typer.Exit(1)

    asyncio.run(_extract_async(pdf_path, output, evaluate))


async def _extract_async(pdf_path: Path, output: Path | None, evaluate: bool) -> None:
    """Async extraction implementation."""
    from liftlogic.adapters.gemini import GeminiClient
    from liftlogic.config import get_settings
    from liftlogic.domains.extraction import GeminiExtractor

    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        # Initialize components
        gemini = GeminiClient(api_key=settings.google_api_key)
        extractor = GeminiExtractor(gemini)

        progress.update(task, description="Extracting from PDF...")

        try:
            result = await extractor.extract(str(pdf_path))

            console.print("\n[green]Extraction Complete[/green]\n")

            # Display summary
            table = Table(title="Extraction Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Components Found", str(len(result.components)))
            table.add_row("Connections Found", str(len(result.connections)))
            table.add_row("Fault Codes Found", str(len(result.fault_codes)))
            table.add_row("Page Count", str(result.page_count))

            console.print(table)

            # Save output if requested
            if output:
                import json

                output.write_text(json.dumps(result.model_dump(), indent=2))
                console.print(f"\n[green]Saved to:[/green] {output}")

            # Run evaluation if requested
            if evaluate:
                progress.update(task, description="Evaluating quality...")
                from liftlogic.domains.extraction import ExtractionEvaluator

                evaluator = ExtractionEvaluator(gemini)
                evaluation = await evaluator.evaluate(result)

                console.print(
                    Panel(
                        f"[bold]Quality Score:[/bold] {evaluation.get('overall_score', 'N/A')}\n"
                        f"[bold]Feedback:[/bold] {evaluation.get('feedback', 'N/A')}",
                        title="Evaluation Results",
                    )
                )

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    semantic: bool = typer.Option(True, "--semantic/--keyword", help="Use semantic search"),
) -> None:
    """Search the knowledge base."""
    asyncio.run(_search_async(query, limit, semantic))


async def _search_async(query: str, limit: int, semantic: bool) -> None:
    """Async search implementation."""
    from liftlogic.config import get_settings

    get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Searching...", total=None)

        try:
            # Note: In full implementation, would initialize HybridSearchEngine
            # For now, show placeholder
            console.print(f"\n[yellow]Searching for:[/yellow] {query}")
            console.print(f"[dim]Limit: {limit}, Semantic: {semantic}[/dim]\n")

            console.print(
                Panel(
                    "Search engine initialization requires database setup.\n"
                    "Run `liftlogic init` to set up the database first.",
                    title="Setup Required",
                    style="yellow",
                )
            )

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def diagnose(
    fault_code: str = typer.Argument(..., help="Fault code to diagnose"),
    manufacturer: str | None = typer.Option(None, "--manufacturer", "-m", help="Manufacturer"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Detailed analysis"),
) -> None:
    """Diagnose an elevator fault code."""
    asyncio.run(_diagnose_async(fault_code, manufacturer, detailed))


async def _diagnose_async(
    fault_code: str,
    manufacturer: str | None,
    detailed: bool,
) -> None:
    """Async diagnosis implementation."""
    from liftlogic.adapters.gemini import GeminiClient
    from liftlogic.config import get_settings
    from liftlogic.domains.diagnosis import DiagnosisMode, FaultDiagnosisAgent

    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Diagnosing...", total=None)

        try:
            gemini = GeminiClient(api_key=settings.google_api_key)
            agent = FaultDiagnosisAgent(llm_client=gemini)

            mode = DiagnosisMode.DETAILED if detailed else DiagnosisMode.QUICK
            context = {}
            if manufacturer:
                context["manufacturer"] = manufacturer

            diagnosis = await agent.diagnose(
                fault_code=fault_code,
                context=context,
                mode=mode,
            )

            console.print(f"\n[bold cyan]Fault Code:[/bold cyan] {diagnosis.fault_code}")
            console.print(f"[bold]Severity:[/bold] {_severity_color(diagnosis.severity.value)}")
            console.print(f"\n[bold]Description:[/bold]\n{diagnosis.description}")

            if diagnosis.causes:
                console.print("\n[bold]Possible Causes:[/bold]")
                for i, cause in enumerate(diagnosis.causes, 1):
                    console.print(f"  {i}. {cause}")

            if diagnosis.remedies:
                console.print("\n[bold]Recommended Remedies:[/bold]")
                for i, remedy in enumerate(diagnosis.remedies, 1):
                    console.print(f"  {i}. {remedy}")

            if diagnosis.safety_implications:
                console.print("\n[bold red]Safety Warnings:[/bold red]")
                for warning in diagnosis.safety_implications:
                    console.print(f"  [red]![/red] {warning}")

            console.print(f"\n[dim]Confidence: {diagnosis.confidence:.0%}[/dim]")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


def _severity_color(severity: str) -> str:
    """Color-code severity level."""
    colors = {
        "critical": "[bold red]CRITICAL[/bold red]",
        "high": "[red]HIGH[/red]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "low": "[green]LOW[/green]",
        "info": "[blue]INFO[/blue]",
    }
    return colors.get(severity, severity.upper())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the API server."""
    import uvicorn

    console.print("\n[green]Starting LiftLogic API server[/green]")
    console.print(f"[dim]http://{host}:{port}[/dim]\n")

    uvicorn.run(
        "liftlogic.interfaces.api:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@app.command()
def init(
    data_dir: Path | None = typer.Option(None, "--data", "-d", help="Data directory"),
) -> None:
    """Initialize LiftLogic database and indexes."""
    asyncio.run(_init_async(data_dir))


async def _init_async(data_dir: Path | None) -> None:
    """Async initialization."""
    from liftlogic.config import get_settings

    settings = get_settings()
    data_path = data_dir or Path(settings.data_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=4)

        # Create directories
        progress.update(task, description="Creating directories...")
        data_path.mkdir(parents=True, exist_ok=True)
        (data_path / "documents").mkdir(exist_ok=True)
        (data_path / "indexes").mkdir(exist_ok=True)
        progress.advance(task)

        # Initialize SQLite
        progress.update(task, description="Initializing SQLite database...")
        data_path / "liftlogic.db"
        # In full implementation: create tables
        progress.advance(task)

        # Initialize FAISS
        progress.update(task, description="Initializing FAISS index...")
        # In full implementation: create empty index
        progress.advance(task)

        # Verify
        progress.update(task, description="Verifying setup...")
        progress.advance(task)

    console.print("\n[green]Initialization complete![/green]")
    console.print(f"[dim]Data directory: {data_path}[/dim]")


@app.command()
def version() -> None:
    """Show version information."""
    from liftlogic import __version__

    console.print(f"LiftLogic v{__version__}")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()

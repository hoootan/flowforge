"""Main CLI entry point for FlowForge."""

import typer
from rich.console import Console

from flowforge_cli.commands import dev, send, functions, runs

app = typer.Typer(
    name="flowforge",
    help="FlowForge CLI - AI workflow orchestration",
    no_args_is_help=True,
)

console = Console()

# Add subcommands
app.add_typer(dev.app, name="dev", help="Start local development server")
app.command(name="send")(send.send_event)
app.add_typer(functions.app, name="functions", help="Manage functions")
app.add_typer(runs.app, name="runs", help="Manage runs")


@app.command()
def version() -> None:
    """Show FlowForge CLI version."""
    from flowforge_cli import __version__

    console.print(f"FlowForge CLI v{__version__}")


@app.callback()
def main() -> None:
    """
    FlowForge CLI - Build reliable AI workflows.

    Use 'flowforge dev' to start a local development server,
    or 'flowforge send' to trigger events.
    """
    pass


if __name__ == "__main__":
    app()

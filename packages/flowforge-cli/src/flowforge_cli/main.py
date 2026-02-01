"""Main CLI entry point for FlowForge."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from flowforge_cli.commands import dev, send, functions, runs
from flowforge_cli.config import get_config, find_config_file, load_config, YAML_AVAILABLE

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


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    path: bool = typer.Option(False, "--path", "-p", help="Show config file path"),
    init: bool = typer.Option(False, "--init", "-i", help="Create a default config file"),
) -> None:
    """Manage CLI configuration."""
    if path:
        config_path = find_config_file()
        if config_path:
            console.print(f"Config file: {config_path}")
        else:
            console.print("[dim]No configuration file found[/dim]")
        return

    if init:
        create_config_file()
        return

    if show or not (path or init):
        show_config()


def show_config() -> None:
    """Display current configuration."""
    config = get_config()
    config_path = find_config_file()

    console.print("\n[bold]FlowForge CLI Configuration[/bold]\n")

    if config_path:
        console.print(f"[dim]Loaded from: {config_path}[/dim]\n")
    else:
        console.print("[dim]Using default configuration[/dim]\n")

    # Server config
    table = Table(title="Server", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("URL", config.server.url)
    table.add_row("API Key", "***" if config.server.api_key else "[dim]not set[/dim]")
    table.add_row("Timeout", f"{config.server.timeout}s")
    console.print(table)
    console.print()

    # Dev config
    table = Table(title="Development Server", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("Host", config.dev.host)
    table.add_row("Port", str(config.dev.port))
    table.add_row("App ID", config.dev.app_id)
    table.add_row("Watch", "enabled" if config.dev.watch else "disabled")
    console.print(table)
    console.print()

    # General options
    table = Table(title="Options", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("Output Format", config.output_format)
    table.add_row("Color", "enabled" if config.color else "disabled")
    table.add_row("Verbose", "enabled" if config.verbose else "disabled")
    console.print(table)


def create_config_file() -> None:
    """Create a default configuration file."""
    if not YAML_AVAILABLE:
        console.print(
            "[red]Error:[/red] pyyaml is required to create config files. "
            "Install with: pip install pyyaml"
        )
        raise typer.Exit(1)

    config_path = Path.cwd() / ".flowforge.yml"

    if config_path.exists():
        overwrite = typer.confirm(f"{config_path} already exists. Overwrite?")
        if not overwrite:
            raise typer.Exit(0)

    default_config = """\
# FlowForge CLI Configuration
# https://flowforge.dev/docs/cli/configuration

# Server connection settings
server:
  url: http://localhost:8000
  # api_key: ff_live_your_api_key_here
  timeout: 30

# Development server settings
dev:
  host: 0.0.0.0
  port: 8080
  app_id: dev-app
  watch: false
  directory: .

# Output options
output_format: table  # table, json, yaml
color: true
verbose: false
"""

    config_path.write_text(default_config)
    console.print(f"[green]Created config file:[/green] {config_path}")


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

"""Development server command."""

import importlib.util
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def load_module_from_file(file_path: Path) -> object:
    """Dynamically load a Python module from a file path."""
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def discover_functions(directory: Path) -> list:
    """Discover FlowForge functions in a directory."""
    from flowforge.decorators import FlowForgeFunction

    functions = []

    # Look for Python files
    for py_file in directory.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            module = load_module_from_file(py_file)

            # Find FlowForgeFunction instances
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, FlowForgeFunction):
                    functions.append(obj)
                    console.print(f"  [green]✓[/green] Found function: {obj.id} ({py_file.name})")

        except Exception as e:
            console.print(f"  [yellow]![/yellow] Error loading {py_file}: {e}")

    return functions


@app.callback(invoke_without_command=True)
def dev(
    ctx: typer.Context,
    directory: Path = typer.Argument(
        Path("."),
        help="Directory containing FlowForge functions",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Port to listen on",
    ),
    app_id: str = typer.Option(
        "dev-app",
        "--app-id",
        help="Application ID",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        "-w",
        help="Watch for file changes and reload",
    ),
) -> None:
    """
    Start local development server.

    Discovers FlowForge functions in the specified directory and
    starts a local server for testing.

    Examples:
        flowforge dev
        flowforge dev ./src --port 3000
        flowforge dev --watch
    """
    if ctx.invoked_subcommand is not None:
        return

    console.print("\n[bold blue]FlowForge Dev Server[/bold blue]\n")
    console.print(f"Discovering functions in: {directory.absolute()}\n")

    # Add directory to Python path
    sys.path.insert(0, str(directory.absolute()))

    try:
        # Import FlowForge SDK
        from flowforge import FlowForge
        from flowforge.dev.server import run_dev_server
    except ImportError:
        console.print(
            "[red]Error:[/red] FlowForge SDK not installed. "
            "Install with: pip install flowforge-sdk"
        )
        raise typer.Exit(1)

    # Discover functions
    functions = discover_functions(directory)

    if not functions:
        console.print("\n[yellow]No FlowForge functions found.[/yellow]")
        console.print("Create a function using the @flowforge.function decorator.\n")
        console.print("Example:")
        console.print("""
from flowforge import FlowForge, Context, step

flowforge = FlowForge(app_id="my-app")

@flowforge.function(
    id="hello-world",
    trigger=flowforge.trigger.event("test/hello"),
)
async def hello_world(ctx: Context):
    name = ctx.event.data.get("name", "World")
    return {"message": f"Hello, {name}!"}
""")
        raise typer.Exit(1)

    console.print(f"\nFound {len(functions)} function(s)\n")

    # Create FlowForge client
    flowforge = FlowForge(app_id=app_id)

    # Start server
    if watch:
        console.print("[yellow]Watch mode enabled - restart on file changes[/yellow]\n")
        # TODO: Implement watch mode with watchfiles
        run_dev_server(flowforge, functions, host=host, port=port)
    else:
        run_dev_server(flowforge, functions, host=host, port=port)

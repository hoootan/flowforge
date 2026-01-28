"""Functions management commands."""

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command("list")
def list_functions(
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """List all registered functions."""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/functions",
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        functions = data.get("functions", [])

        if not functions:
            console.print("\n[yellow]No functions registered.[/yellow]\n")
            return

        table = Table(title="Registered Functions")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Trigger", style="yellow")
        table.add_column("Active", style="blue")

        for fn in functions:
            trigger = f"{fn.get('trigger_type', '')}={fn.get('trigger_value', '')}"
            active = "✓" if fn.get("is_active") else "✗"
            table.add_row(
                fn.get("function_id", ""),
                fn.get("name", ""),
                trigger,
                active,
            )

        console.print()
        console.print(table)
        console.print()

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("get")
def get_function(
    function_id: str = typer.Argument(..., help="Function ID"),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """Get details for a specific function."""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/functions/{function_id}",
            timeout=30.0,
        )

        if response.status_code == 404:
            console.print(f"[red]Error:[/red] Function '{function_id}' not found")
            raise typer.Exit(1)

        response.raise_for_status()
        fn = response.json()

        console.print(f"\n[bold cyan]Function: {fn.get('function_id')}[/bold cyan]\n")
        console.print(f"  Name:       {fn.get('name')}")
        console.print(f"  Trigger:    {fn.get('trigger_type')}={fn.get('trigger_value')}")
        if fn.get("trigger_expression"):
            console.print(f"  Expression: {fn.get('trigger_expression')}")
        console.print(f"  Endpoint:   {fn.get('endpoint_url')}")
        console.print(f"  Active:     {'Yes' if fn.get('is_active') else 'No'}")
        console.print(f"  Config:     {fn.get('config')}")
        console.print()

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

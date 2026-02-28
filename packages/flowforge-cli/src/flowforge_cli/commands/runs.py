"""Runs management commands."""


import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command("list")
def list_runs(
    function_id: str | None = typer.Option(
        None,
        "--function",
        "-f",
        help="Filter by function ID",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Maximum number of runs to show",
    ),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """List function runs."""
    try:
        params = {"page_size": limit}
        if function_id:
            params["function_id"] = function_id
        if status:
            params["status"] = status

        response = httpx.get(
            f"{api_url}/api/v1/runs",
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        runs = data.get("runs", [])

        if not runs:
            console.print("\n[yellow]No runs found.[/yellow]\n")
            return

        table = Table(title=f"Function Runs (showing {len(runs)} of {data.get('total', 0)})")
        table.add_column("ID", style="cyan", max_width=12)
        table.add_column("Function", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Attempt", style="blue")
        table.add_column("Created", style="dim")

        status_colors = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "dim",
            "paused": "magenta",
        }

        for run in runs:
            run_id = run.get("id", "")[:12]
            status = run.get("status", "")
            status_color = status_colors.get(status, "white")
            created = run.get("created_at", "")[:19]  # Truncate to datetime

            table.add_row(
                run_id,
                run.get("function_id", "")[:20],
                f"[{status_color}]{status}[/{status_color}]",
                f"{run.get('attempt', 1)}/{run.get('max_attempts', 3)}",
                created,
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
def get_run(
    run_id: str = typer.Argument(..., help="Run ID"),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """Get details for a specific run."""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/runs/{run_id}",
            timeout=30.0,
        )

        if response.status_code == 404:
            console.print(f"[red]Error:[/red] Run '{run_id}' not found")
            raise typer.Exit(1)

        response.raise_for_status()
        run = response.json()

        console.print(f"\n[bold cyan]Run: {run.get('id')}[/bold cyan]\n")
        console.print(f"  Function:   {run.get('function_id')}")
        console.print(f"  Status:     {run.get('status')}")
        console.print(f"  Trigger:    {run.get('trigger_type')}")
        console.print(f"  Attempt:    {run.get('attempt')}/{run.get('max_attempts')}")
        console.print(f"  Created:    {run.get('created_at')}")

        if run.get("started_at"):
            console.print(f"  Started:    {run.get('started_at')}")
        if run.get("ended_at"):
            console.print(f"  Ended:      {run.get('ended_at')}")

        if run.get("output"):
            console.print("\n  [bold]Output:[/bold]")
            console.print(f"    {run.get('output')}")

        if run.get("error"):
            console.print("\n  [bold red]Error:[/bold red]")
            console.print(f"    {run.get('error')}")

        steps = run.get("steps", [])
        if steps:
            console.print(f"\n  [bold]Steps ({len(steps)}):[/bold]")
            for step in steps:
                status_icon = {
                    "completed": "[green]✓[/green]",
                    "failed": "[red]✗[/red]",
                    "running": "[blue]→[/blue]",
                    "pending": "[dim]○[/dim]",
                    "sleeping": "[yellow]⏸[/yellow]",
                    "waiting": "[magenta]⌛[/magenta]",
                }.get(step.get("status", ""), "○")

                console.print(f"    {status_icon} {step.get('step_id')} ({step.get('step_type')})")

        console.print()

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("cancel")
def cancel_run(
    run_id: str = typer.Argument(..., help="Run ID to cancel"),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """Cancel a running or pending run."""
    try:
        response = httpx.post(
            f"{api_url}/api/v1/runs/{run_id}/cancel",
            timeout=30.0,
        )

        if response.status_code == 404:
            console.print(f"[red]Error:[/red] Run '{run_id}' not found")
            raise typer.Exit(1)

        if response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json().get('detail', 'Cannot cancel run')}")
            raise typer.Exit(1)

        response.raise_for_status()
        console.print(f"[green]✓[/green] Run {run_id} cancelled")

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("replay")
def replay_run(
    run_id: str = typer.Argument(..., help="Run ID to replay"),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
) -> None:
    """Replay a failed or completed run."""
    try:
        response = httpx.post(
            f"{api_url}/api/v1/runs/{run_id}/replay",
            timeout=30.0,
        )

        if response.status_code == 404:
            console.print(f"[red]Error:[/red] Run '{run_id}' not found")
            raise typer.Exit(1)

        response.raise_for_status()
        new_run = response.json()
        console.print("[green]✓[/green] Run replayed")
        console.print(f"  New run ID: {new_run.get('id')}")

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

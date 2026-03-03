"""Send event command."""

import json

import httpx
import typer
from rich.console import Console

from flowforge_cli.config import get_config

console = Console()


def send_event(
    event_name: str = typer.Argument(
        ...,
        help="Event name (e.g., 'order/created')",
    ),
    data: str | None = typer.Option(
        None,
        "--data",
        "-d",
        help="Event data as JSON string",
    ),
    data_file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to JSON file containing event data",
    ),
    api_url: str = typer.Option(
        "http://localhost:8080",
        "--api-url",
        "-u",
        help="FlowForge API URL",
    ),
    event_id: str | None = typer.Option(
        None,
        "--id",
        help="Event ID for idempotency",
    ),
) -> None:
    """
    Send an event to trigger functions.

    Examples:
        flowforge send order/created -d '{"order_id": "123"}'
        flowforge send user/signup -f user_data.json
        flowforge send test/hello
    """
    # Parse event data
    event_data = {}

    if data_file:
        try:
            with open(data_file) as f:
                event_data = json.load(f)
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] File not found: {data_file}")
            raise typer.Exit(1)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON in file: {e}")
            raise typer.Exit(1)
    elif data:
        try:
            event_data = json.loads(data)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON data: {e}")
            raise typer.Exit(1)

    # Build event payload
    payload = {
        "name": event_name,
        "data": event_data,
    }
    if event_id:
        payload["id"] = event_id

    console.print(f"\n[bold]Sending event:[/bold] {event_name}")
    console.print(f"[bold]To:[/bold] {api_url}/api/v1/events")
    if event_data:
        console.print(f"[bold]Data:[/bold] {json.dumps(event_data, indent=2)}")
    console.print()

    # Send event
    try:
        config = get_config()
        headers = {}
        if config.server.api_key:
            headers["X-FlowForge-API-Key"] = config.server.api_key

        response = httpx.post(
            f"{api_url}/api/v1/events",
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code == 201:
            result = response.json()
            console.print("[green]✓[/green] Event sent successfully")
            console.print(f"  Event ID: {result.get('id', 'unknown')}")
        else:
            console.print("[red]✗[/red] Failed to send event")
            console.print(f"  Status: {response.status_code}")
            console.print(f"  Response: {response.text}")
            raise typer.Exit(1)

    except httpx.ConnectError:
        console.print(f"[red]Error:[/red] Cannot connect to {api_url}")
        console.print("Make sure the FlowForge server is running.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

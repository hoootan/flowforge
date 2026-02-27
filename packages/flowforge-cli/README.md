# flowforge-cli

Command-line interface for [FlowForge](https://github.com/flowforge/flowforge) — the AI workflow orchestration platform.

## Installation

```bash
pip install flowforge-cli
```

Requires Python 3.11+.

## Commands

| Command | Description |
|---------|-------------|
| `flowforge dev <dir>` | Start a local development server watching `<dir>` for workflow files |
| `flowforge send <event> -d <json>` | Send an event to the running server |
| `flowforge logs [run-id]` | Stream logs for all runs or a specific run |

### Examples

```bash
# Start development server (auto-reloads on file changes)
flowforge dev .

# Send an event with JSON data
flowforge send order/created -d '{"order_id": "123", "customer": "Alice", "total": 99.99}'

# Stream logs for a specific run
flowforge logs run_abc123
```

## Configuration

The CLI reads configuration from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOWFORGE_API_URL` | `http://localhost:8000` | FlowForge server URL |
| `FLOWFORGE_API_KEY` | — | API key for authentication (`ff_test_...` for development) |

You can also set these in a `.env` file in your project directory.

## Development

To work on the CLI itself, install it in editable mode from the repository root:

```bash
git clone https://github.com/flowforge/flowforge
cd flowforge
pip install -e packages/flowforge-cli
```

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full development setup.

## License

MIT — see [LICENSE](../../LICENSE) for details.

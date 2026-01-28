# Database Migrations

This directory contains database migrations for the FlowForge server.

## Available Migrations

### `add_agent_tool_approval_support` (2026-01-23)

Adds support for AI agent tool calling with Human-in-the-Loop approval.

**Changes:**
- Adds tool-specific columns to `steps` table: `tool_name`, `tool_call_id`, `tool_input`, `tool_output`, `agent_state`
- Creates new `tool_approvals` table for approval requests
- Adds appropriate indexes for performance

**SQL Version:**
```bash
psql -U flowforge -d flowforge < add_agent_tool_approval_support.sql
```

**Python Version:**
```bash
python add_agent_tool_approval_support.py
```

## Migration Notes

The FlowForge server currently uses SQLAlchemy's `Base.metadata.create_all()` for automatic table creation in development mode. For production deployments, you should:

1. Use the SQL migration files directly with your database
2. Or integrate a proper migration tool like Alembic

## Future: Alembic Integration

For production use, consider setting up Alembic:

```bash
# Install alembic
pip install alembic

# Initialize alembic
alembic init alembic

# Generate migration from models
alembic revision --autogenerate -m "migration message"

# Apply migrations
alembic upgrade head
```

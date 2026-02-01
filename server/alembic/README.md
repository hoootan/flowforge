# FlowForge Database Migrations

This directory contains Alembic database migrations for FlowForge.

## Setup

Ensure you have the database URL configured:

```bash
export FLOWFORGE_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/flowforge"
```

## Commands

### Generate a new migration (auto-detect changes)

```bash
cd server
alembic revision --autogenerate -m "description of changes"
```

### Run pending migrations

```bash
cd server
alembic upgrade head
```

### Rollback one migration

```bash
cd server
alembic downgrade -1
```

### View migration history

```bash
cd server
alembic history
```

### View current revision

```bash
cd server
alembic current
```

## Migration Guidelines

1. **Always review generated migrations** - Autogenerate can miss things or generate incorrect changes
2. **Test migrations locally** before deploying
3. **Never edit applied migrations** - Create a new migration instead
4. **Include both upgrade() and downgrade()** functions
5. **Use data migrations carefully** - Consider backwards compatibility

## Naming Convention

Migrations are named: `{date}_{time}_{revision}_{description}.py`

Example: `20240115_1430_a1b2c3d4_add_user_table.py`

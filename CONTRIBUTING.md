# Contributing to FlowForge

Thank you for your interest in contributing to FlowForge! This guide will help you get set up and understand our process.

## Ways to Contribute

- **Bug reports** — open an issue using the bug report template
- **Feature requests** — open an issue using the feature request template
- **Documentation** — fix typos, improve clarity, add examples
- **Code** — fix bugs, implement features, improve performance
- **Pull requests** — see the PR process below

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- pnpm (`npm install -g pnpm`)
- Docker + Docker Compose

### 1. Start infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL (port 5432) and Redis (port 6379).

### 2. Install Python packages

```bash
pip install -e "packages/flowforge-sdk[all]"
pip install -e packages/flowforge-cli
pip install -e server
```

### 3. Install dashboard dependencies

```bash
cd dashboard
pnpm install
```

### 4. Create your first admin user

```bash
flowforge-create-admin -e admin@example.com -p secret123 -n "Admin User"
```

### 5. Run the development server

```bash
cd examples
flowforge dev .
```

The dashboard is available at `http://localhost:3000` (run `pnpm dev` inside `dashboard/`).

## Running Tests

```bash
# All tests
pytest

# Unit tests only (no infrastructure required)
pytest tests/unit

# Integration tests (requires running postgres + redis)
pytest tests/integration

# Specific test
pytest -v -k "test_name"
```

## Linting and Type Checking

```bash
# Lint
ruff check .

# Auto-fix lint issues
ruff format .

# Type check
mypy packages/flowforge-sdk/src packages/flowforge-cli/src server/src
```

All PRs must pass lint and type checks before merging.

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`

Examples:
```
feat(sdk): add step.invoke for cross-function calls
fix(server): handle missing tenant in event dispatch
docs: clarify step.sleep duration format
chore(deps): upgrade pydantic to 2.5
```

## PR Process

1. Fork the repository
2. Create a branch from `main`: `git checkout -b feat/my-feature`
3. Make your changes, commit with Conventional Commits
4. Push to your fork and open a PR against `main`
5. Fill in the PR template — link the related issue
6. A maintainer will review and merge

Keep PRs focused. One logical change per PR makes review faster and history cleaner.

## Release Process

Releases are automated via the `publish-sdks.yml` workflow. Maintainers trigger it via `workflow_dispatch` or by pushing a `v*` tag. Contributors don't need to worry about releases.

## Questions?

Open a [GitHub Discussion](https://github.com/flowforge/flowforge/discussions) rather than an issue for general questions.

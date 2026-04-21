# Changelog

All notable changes to FlowForge are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed
- Runner: durable sleep steps are now marked `COMPLETED` when their
  `scheduled_at` elapses, so the SDK's memoisation sees them on replay and
  doesn't re-emit the same sleep. Previously a paused run would replay its
  sleep endlessly (the step stayed `SLEEPING`, was filtered out of
  `completed_steps`, and the SDK yielded a fresh `StepCompleted` with new
  jitter, re-pausing the run). This surfaced most visibly via the PR #32
  retry-sleep chain on provider 429s, but affected any use of `step.sleep`.
- Runner: commit step/run updates before enqueuing the continuation job, so
  the executor doesn't race and read stale `PAUSED` status. Matches the
  pattern already used by `_resolve_waiting_steps`.

## [0.2.11] — 2026-02-27

### Added
- Kubernetes deployment manifests (`k8s/`)
- `POST /runs/{id}/retry` endpoint for in-place run resumption
- Run management methods on the TypeScript SDK client (`cancel`, `retry`, `get`)

### Fixed
- Mark run as `FAILED` when AI step exhausts all retries
- Retry endpoint now correctly re-enqueues the job to Redis after resetting run status
- Agent wrap-up: add placeholder `tool_results` for unprocessed batch calls
- Agent wrap-up: pass tools with `tool_choice=none` for Anthropic provider

## [0.2.10] — 2026-02

### Added
- Multiple AI providers per type; API endpoints now use provider ID
- OAuth `auth_type` support for AI providers
- Collapsible JSON display for run details in the dashboard

### Changed
- All AI model providers updated to latest verified models
- OAuth token auth: send via `Authorization` header only (not `x-api-key`)
- Simplified OAuth handling: pass credential as `api_key` for all auth types

### Fixed
- Provider test: pass `api_key` directly to LiteLLM instead of env var

## [0.2.0] — 2026-01

### Added
- MIT License
- Contributor Covenant Code of Conduct
- Model pricing management with dedicated UI and backend services
- JWT access and refresh token authentication with automatic client-side token refresh
- Two-Factor Authentication (TOTP)
- AI provider management with usage tracking
- Worker heartbeat mechanism
- Audit logging and data retention
- Dead letter queue (DLQ) for failed runs
- Function versioning
- Telemetry support
- Alembic database migrations
- GitHub Actions workflow to publish SDKs to PyPI and npm

### Changed
- Upgraded Python runtime to 3.12
- Multi-stage Docker builds with virtual environments (smaller images, faster CI)

## [0.1.0] — Initial release

### Added
- FlowForge core: durable workflow execution with step memoization
- `@flowforge.function()` decorator with event, cron, and webhook triggers
- Step primitives: `step.run`, `step.sleep`, `step.ai`, `step.wait_for_event`, `step.invoke`, `step.send_event`
- Flow control: concurrency limiting, rate limiting, throttling, debouncing
- FastAPI orchestration server with fair Redis queue
- PostgreSQL-backed state (Tenant, Function, Run, Step, Event, User, ApiKey models)
- Python SDK (`flowforge-sdk`)
- CLI (`flowforge-cli`): `dev`, `send`, `logs` commands
- TypeScript client (`flowforge-client-ts`)
- Next.js admin dashboard with role-based access (Admin / Member / Viewer)
- Docker Compose setup for local development

[Unreleased]: https://github.com/flowforge/flowforge/compare/v0.2.11...HEAD
[0.2.11]: https://github.com/flowforge/flowforge/compare/v0.2.10...v0.2.11
[0.2.10]: https://github.com/flowforge/flowforge/compare/v0.2.0...v0.2.10
[0.2.0]: https://github.com/flowforge/flowforge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/flowforge/flowforge/releases/tag/v0.1.0

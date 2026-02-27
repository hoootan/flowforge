# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Older releases | No |

We only apply security patches to the latest release. Please upgrade before reporting a vulnerability.

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

### Option 1: GitHub Private Security Advisory (preferred)

Use GitHub's [private vulnerability reporting](https://github.com/flowforge/flowforge/security/advisories/new) feature. This keeps the report confidential until a fix is ready.

### Option 2: Email

Send details to **security@flowforge.io** with:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

Encrypt your email with our PGP key if it contains sensitive details (key available on request).

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | 48 hours |
| Triage and severity assessment | 7 days |
| Patch released | 30 days (critical: 7 days) |
| Public disclosure | After patch is released |

We will keep you informed throughout the process and credit you in the release notes unless you prefer to remain anonymous.

## Scope

The following components are in scope:

- **Server** (`server/`) — FastAPI orchestration server
- **SDK** (`packages/flowforge-sdk/`) — Python SDK
- **CLI** (`packages/flowforge-cli/`) — Command-line tool
- **Dashboard** (`dashboard/`) — Next.js admin UI

### Out of Scope

- `examples/` directory — these are demonstration scripts
- Vulnerabilities in third-party dependencies (report to the upstream project)
- Denial-of-service attacks that require significant resources
- Rate limiting bypass
- Issues only exploitable with physical access to the machine
- Social engineering attacks

## Security Best Practices for Self-Hosted Deployments

- Set a strong `FLOWFORGE_JWT_SECRET` (at least 32 random characters)
- Use environment variables for all secrets — never commit them
- Restrict network access to PostgreSQL and Redis
- Rotate API keys regularly
- Run the server behind a reverse proxy (nginx/Caddy) with TLS

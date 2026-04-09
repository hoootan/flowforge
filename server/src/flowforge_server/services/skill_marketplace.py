"""Skill marketplace service — search skills.sh, fetch SKILL.md from GitHub."""

import re
from datetime import UTC, datetime
from typing import Any

import httpx

# skills.sh search API
SKILLS_SH_API = "https://skills.sh/api/search"

# GitHub raw content base
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Timeout for external requests
TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)

# Max SKILL.md size we'll download (100KB)
MAX_SKILL_SIZE = 100_000


def parse_skill_md(content: str) -> dict[str, Any]:
    """
    Parse a SKILL.md file into frontmatter + body.

    Handles YAML-like frontmatter delimited by --- lines.
    Uses simple regex parsing to avoid pyyaml dependency.

    Returns:
        {"frontmatter": {"name": ..., "description": ...}, "body": "markdown..."}
    """
    frontmatter: dict[str, Any] = {}
    body = content

    # Check for YAML frontmatter (--- delimited)
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if match:
        fm_text = match.group(1)
        body = match.group(2).strip()

        # Simple key: value parsing (handles most SKILL.md frontmatter)
        for line in fm_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower().replace("-", "_")
                value = value.strip().strip('"').strip("'")
                # Handle list values like [a, b, c]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
                frontmatter[key] = value

    return {"frontmatter": frontmatter, "body": body}


async def search_skills_sh(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search skills.sh marketplace.

    Returns normalized results with: external_id, name, description, source, repo, install_count
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(
                SKILLS_SH_API,
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return []

    results = []
    items = data if isinstance(data, list) else data.get("results", data.get("skills", []))

    for item in items[:limit]:
        # Normalize skills.sh response format
        source_repo = item.get("source", item.get("repo", item.get("full_name", "")))
        name = item.get("name", source_repo.split("/")[-1] if source_repo else "Unknown")

        results.append({
            "external_id": str(item.get("id", source_repo)),
            "name": name,
            "description": item.get("description", ""),
            "source": "skills_sh",
            "repo": source_repo,
            "install_count": item.get("installs", item.get("install_count", 0)),
            "preview_url": f"{GITHUB_RAW_BASE}/{source_repo}/main/SKILL.md" if source_repo else None,
        })

    return results


async def fetch_skill_md(
    repo: str,
    path: str = "SKILL.md",
    branch: str = "main",
) -> dict[str, Any] | None:
    """
    Fetch and parse a SKILL.md file from a GitHub repository.

    Args:
        repo: "owner/repo" format
        path: Path to SKILL.md within the repo
        branch: Git branch (default "main")

    Returns:
        Parsed skill data or None if not found.
    """
    url = f"{GITHUB_RAW_BASE}/{repo}/{branch}/{path}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)

            # Try "master" branch if "main" returns 404
            if resp.status_code == 404 and branch == "main":
                url_master = f"{GITHUB_RAW_BASE}/{repo}/master/{path}"
                resp = await client.get(url_master)

            if resp.status_code != 200:
                return None

            content = resp.text
            if len(content) > MAX_SKILL_SIZE:
                content = content[:MAX_SKILL_SIZE]

        except httpx.HTTPError:
            return None

    parsed = parse_skill_md(content)

    return {
        "name": parsed["frontmatter"].get("name", path.replace("SKILL.md", "").strip("/") or repo.split("/")[-1]),
        "description": parsed["frontmatter"].get("description", ""),
        "raw_content": content,
        "frontmatter": parsed["frontmatter"],
        "body": parsed["body"],
        "repo": repo,
        "path": path,
        "fetched_at": datetime.now(UTC).isoformat(),
    }

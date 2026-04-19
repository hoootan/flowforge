"""Unit tests for Tool soft-delete semantics.

These tests exercise the DB-layer query patterns that the tools route and the
function tool-validation path rely on. They avoid importing the FastAPI app
entirely so they run under `pytest --noconftest` without being blocked by the
project's conftest (which pulls in the full API stack).

Run:
    pytest tests/unit/test_tool_soft_delete.py --noconftest -v
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Map Postgres-only types to SQLite equivalents so Base.metadata.create_all works.
SQLiteTypeCompiler.visit_JSONB = lambda self, t, **kw: "JSON"
SQLiteTypeCompiler.visit_UUID = lambda self, t, **kw: "CHAR(36)"

# Imports must come after the SQLite type-compiler patches above, which remap
# JSONB/UUID so Base.metadata.create_all works on sqlite for this test.
from flowforge_server.db.models.base import Base  # noqa: E402
from flowforge_server.db.models.tenant import Tenant  # noqa: E402
from flowforge_server.db.models.tool import Tool  # noqa: E402


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c, tables=[Tenant.__table__, Tool.__table__]
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_id(session: AsyncSession) -> uuid.UUID:
    tid = uuid.uuid4()
    session.add(
        Tenant(
            id=tid,
            name="t1",
            slug="t1",
            api_key_hash="x",
            signing_key_hash="x",
        )
    )
    await session.commit()
    return tid


async def _create_tool(
    session: AsyncSession, tenant_id: uuid.UUID, name: str
) -> Tool:
    tool = Tool(
        tenant_id=tenant_id,
        name=name,
        description="initial",
        parameters={},
        tool_type="custom",
        code="def execute(x): return x",
        is_builtin=False,
        is_active=True,
    )
    session.add(tool)
    await session.commit()
    await session.refresh(tool)
    return tool


class TestToolSoftDelete:
    """Soft-delete of tenant tools preserves history and hides from user queries."""

    async def test_delete_sets_deleted_at_and_inactive(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        tool = await _create_tool(session, tenant_id, "keyword_enrichment")

        # Mirror the DELETE route body.
        tool.deleted_at = datetime.now(UTC)
        tool.is_active = False
        await session.commit()

        assert tool.deleted_at is not None
        assert tool.deleted_at.tzinfo is not None, "deleted_at must be tz-aware"
        assert tool.is_active is False

    async def test_list_query_excludes_soft_deleted(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _create_tool(session, tenant_id, "t_a")
        deleted = await _create_tool(session, tenant_id, "t_b")
        deleted.deleted_at = datetime.now(UTC)
        deleted.is_active = False
        await session.commit()

        # Mirror the filter applied by list_tools in routes/tools.py.
        visible = (
            await session.execute(
                select(Tool).where(
                    Tool.tenant_id == tenant_id,
                    Tool.deleted_at.is_(None),
                )
            )
        ).scalars().all()

        names = {t.name for t in visible}
        assert names == {"t_a"}

    async def test_get_query_excludes_soft_deleted(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        tool = await _create_tool(session, tenant_id, "solo")
        tool.deleted_at = datetime.now(UTC)
        tool.is_active = False
        await session.commit()

        hit = (
            await session.execute(
                select(Tool).where(
                    Tool.tenant_id == tenant_id,
                    Tool.name == "solo",
                    Tool.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        assert hit is None, "get_tool filter must exclude soft-deleted rows"

    async def test_row_still_resolvable_by_id_after_soft_delete(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Execution and history paths look up by primary key without the
        deleted_at filter — the row must still resolve so in-flight runs work.
        """
        tool = await _create_tool(session, tenant_id, "history_check")
        tool_uuid = tool.id
        tool.deleted_at = datetime.now(UTC)
        tool.is_active = False
        await session.commit()

        hit = (
            await session.execute(select(Tool).where(Tool.id == tool_uuid))
        ).scalar_one_or_none()
        assert hit is not None
        assert hit.name == "history_check"

    async def test_recreate_resurrects_same_row(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """POST /tools with the same name after a soft-delete restores the
        original row (same UUID) instead of hitting the unique constraint.
        """
        tool = await _create_tool(session, tenant_id, "reborn")
        original_uuid = tool.id
        tool.deleted_at = datetime.now(UTC)
        tool.is_active = False
        await session.commit()

        # Mirror the resurrect branch in create_tool.
        existing = (
            await session.execute(
                select(Tool).where(
                    Tool.tenant_id == tenant_id,
                    Tool.name == "reborn",
                )
            )
        ).scalar_one()
        assert existing.deleted_at is not None
        existing.deleted_at = None
        existing.description = "rebuilt"
        existing.is_active = True
        await session.commit()

        visible = (
            await session.execute(
                select(Tool).where(
                    Tool.tenant_id == tenant_id,
                    Tool.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        assert len(visible) == 1
        assert visible[0].id == original_uuid, "must resurrect, not create new"
        assert visible[0].description == "rebuilt"
        assert visible[0].is_active is True


class TestFunctionValidationRejectsSoftDeletedTool:
    """The tool existence check in create_inline_function / update_function now
    filters deleted_at — referencing a soft-deleted tool should come back empty.
    """

    async def test_validation_query_returns_none_for_soft_deleted_tool(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        from sqlalchemy import or_

        tool = await _create_tool(session, tenant_id, "soft_deleted_tool")
        tool.deleted_at = datetime.now(UTC)
        tool.is_active = False
        await session.commit()

        # Mirror the query shape used in functions.py tool validation.
        hit = (
            await session.execute(
                select(Tool).where(
                    or_(
                        (Tool.tenant_id == tenant_id)
                        & (Tool.name == "soft_deleted_tool"),
                        (Tool.is_builtin == True)  # noqa: E712
                        & (Tool.name == "soft_deleted_tool"),
                    ),
                    Tool.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        assert hit is None, (
            "functions.py tool validation must treat soft-deleted tools as "
            "nonexistent so they can't be wired into new/updated functions"
        )

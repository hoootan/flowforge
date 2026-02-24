"""Shared pytest fixtures for FlowForge server tests.

This module provides fixtures for:
- Test database setup and teardown
- Test client with authentication
- Mock services for unit tests
- Sample data factories
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from flowforge_server.config import Settings, get_settings
from flowforge_server.db.models.base import Base
from flowforge_server.db.models import Tenant, Function, Tool, Run, RunStatus
from flowforge_server.api.deps import hash_api_key


# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://flowforge:flowforge@localhost:5432/flowforge_test",
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with test database/redis URLs."""
    return Settings(
        env="development",
        database_url=TEST_DATABASE_URL,
        redis_url=TEST_REDIS_URL,
        debug=True,
    )


@pytest_asyncio.fixture(scope="function")
async def test_engine(test_settings: Settings):
    """Create a test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine):
    """Create and drop tables for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine, test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_tenant(test_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    api_key = "test-api-key-12345"
    tenant = Tenant(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Test Tenant",
        slug="test-tenant",
        api_key_hash=hash_api_key(api_key),
        signing_key_hash=hash_api_key("test-signing-key"),
        settings={},
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_function(test_session: AsyncSession, test_tenant: Tenant) -> Function:
    """Create a test inline function."""
    fn = Function(
        tenant_id=test_tenant.id,
        function_id="test-function",
        name="Test Function",
        slug="test-function",
        trigger_type="event",
        trigger_value="test/event",
        is_inline=True,
        system_prompt="You are a helpful assistant.",
        tools_config=["web_search"],
        agent_config={"model": "gpt-5.2", "max_iterations": 5},
        config={},
        is_active=True,
    )
    test_session.add(fn)
    await test_session.commit()
    await test_session.refresh(fn)
    return fn


@pytest_asyncio.fixture
async def test_tool(test_session: AsyncSession, test_tenant: Tenant) -> Tool:
    """Create a test custom tool."""
    tool = Tool(
        tenant_id=test_tenant.id,
        name="test_tool",
        description="A test tool for testing",
        parameters={
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Test input"},
            },
            "required": ["input"],
        },
        code='def execute(input: str) -> dict:\n    return {"result": f"Processed: {input}"}',
        is_builtin=False,
        requires_approval=False,
        is_active=True,
    )
    test_session.add(tool)
    await test_session.commit()
    await test_session.refresh(tool)
    return tool


@pytest_asyncio.fixture
async def test_run(
    test_session: AsyncSession, test_tenant: Tenant, test_function: Function
) -> Run:
    """Create a test run."""
    run = Run(
        tenant_id=test_tenant.id,
        function_id=test_function.id,
        status=RunStatus.PENDING,
        trigger_type="event",
        trigger_data={"event": {"name": "test/event", "data": {"prompt": "Hello"}}},
        attempt=1,
        max_attempts=3,
    )
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)
    return run


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service for unit tests."""
    mock = AsyncMock()
    mock.complete.return_value = MagicMock(
        content="Test response",
        model="gpt-5.2",
        provider="openai",
        usage=MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            latency_ms=500,
        ),
        finish_reason="stop",
        tool_calls=[],
    )
    return mock


@pytest.fixture
def mock_job_queue():
    """Create a mock job queue for unit tests."""
    mock = AsyncMock()
    mock.enqueue.return_value = "job-123"
    mock.dequeue.return_value = None
    return mock


@pytest.fixture
def mock_event_stream():
    """Create a mock event stream for unit tests."""
    mock = AsyncMock()
    mock.publish.return_value = None
    return mock


@pytest.fixture
def mock_pubsub():
    """Create a mock pubsub for unit tests."""
    mock = AsyncMock()
    mock.publish.return_value = None
    mock.subscribe.return_value = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def test_client(
    test_session: AsyncSession,
    test_tenant: Tenant,
    mock_ai_service,
    mock_job_queue,
    mock_event_stream,
    mock_pubsub,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with mocked services."""
    from flowforge_server.api.app import create_app
    from flowforge_server.db import get_session
    from flowforge_server.services.container import ServiceContainer

    app = create_app()

    # Create mock service container
    services = ServiceContainer(
        ai_service=mock_ai_service,
        job_queue=mock_job_queue,
        event_stream=mock_event_stream,
        pubsub=mock_pubsub,
    )
    app.state.services = services

    # Override database session
    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(
    test_client: AsyncClient,
) -> AsyncClient:
    """Create an authenticated test client."""
    test_client.headers["X-FlowForge-API-Key"] = "test-api-key-12345"
    return test_client


# Helper factories
class Factory:
    """Factory for creating test data."""

    @staticmethod
    def event_data(
        name: str = "test/event",
        data: dict | None = None,
        event_id: str | None = None,
    ) -> dict:
        """Create event creation payload."""
        return {
            "name": name,
            "data": data or {"prompt": "Test prompt"},
            "id": event_id,
        }

    @staticmethod
    def function_data(
        function_id: str = "test-fn",
        name: str = "Test Function",
        trigger_event: str = "test/event",
    ) -> dict:
        """Create function creation payload."""
        return {
            "id": function_id,
            "name": name,
            "trigger": {"type": "event", "value": trigger_event},
            "endpoint_url": "http://localhost:8001/functions/test",
            "config": {},
        }

    @staticmethod
    def inline_function_data(
        function_id: str = "test-inline-fn",
        name: str = "Test Inline Function",
        trigger_event: str = "test/inline-event",
        tools: list[str] | None = None,
    ) -> dict:
        """Create inline function creation payload."""
        return {
            "id": function_id,
            "name": name,
            "trigger": {"type": "event", "value": trigger_event},
            "system_prompt": "You are a helpful assistant.",
            "tools": tools or [],
            "agent_config": {"model": "gpt-5.2", "max_iterations": 5},
            "config": {},
        }

    @staticmethod
    def tool_data(
        name: str = "custom_tool",
        description: str = "A custom tool",
        code: str | None = None,
    ) -> dict:
        """Create tool creation payload."""
        return {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
            "code": code or 'def execute(query: str) -> dict:\n    return {"result": query}',
            "requires_approval": False,
        }


@pytest.fixture
def factory() -> Factory:
    """Provide the test data factory."""
    return Factory()

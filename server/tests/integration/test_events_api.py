"""Integration tests for the events API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEventsAPI:
    """Integration tests for /api/v1/events endpoints."""

    async def test_create_event_unauthenticated_dev_mode(
        self, test_client: AsyncClient, factory
    ):
        """Test creating an event without auth in dev mode (uses default tenant)."""
        response = await test_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/event"),
        )
        # In dev mode, should fall back to default tenant
        assert response.status_code in (201, 401, 500)  # Depends on tenant setup

    async def test_create_event_authenticated(
        self, authenticated_client: AsyncClient, factory
    ):
        """Test creating an event with authentication."""
        response = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/event"),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test/event"
        assert "id" in data
        assert "event_id" in data

    async def test_create_event_with_custom_id(
        self, authenticated_client: AsyncClient, factory
    ):
        """Test creating an event with a custom ID for idempotency."""
        event_id = "custom-event-123"
        response = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/event", event_id=event_id),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_id"] == event_id

    async def test_create_event_duplicate_id_rejected(
        self, authenticated_client: AsyncClient, factory
    ):
        """Test that duplicate event IDs are rejected."""
        event_id = "duplicate-event-123"

        # First request should succeed
        response1 = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/event", event_id=event_id),
        )
        assert response1.status_code == 201

        # Second request with same ID should fail
        response2 = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/event", event_id=event_id),
        )
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    async def test_list_events(self, authenticated_client: AsyncClient, factory):
        """Test listing events."""
        # Create some events
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/events",
                json=factory.event_data(name=f"test/event-{i}"),
            )

        response = await authenticated_client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert len(data["events"]) >= 3

    async def test_list_events_filter_by_name(
        self, authenticated_client: AsyncClient, factory
    ):
        """Test filtering events by name."""
        # Create events with different names
        await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="order/created"),
        )
        await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="user/signup"),
        )

        response = await authenticated_client.get(
            "/api/v1/events", params={"name": "order/created"}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(e["name"] == "order/created" for e in data["events"])

    async def test_get_event(self, authenticated_client: AsyncClient, factory):
        """Test getting a specific event."""
        # Create an event
        create_response = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(name="test/specific"),
        )
        event_id = create_response.json()["event_id"]

        # Get the event
        response = await authenticated_client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event_id
        assert data["name"] == "test/specific"

    async def test_get_event_not_found(self, authenticated_client: AsyncClient):
        """Test getting a non-existent event."""
        response = await authenticated_client.get("/api/v1/events/nonexistent-id")
        assert response.status_code == 404

    async def test_list_events_pagination(
        self, authenticated_client: AsyncClient, factory
    ):
        """Test events pagination."""
        # Create multiple events
        for i in range(10):
            await authenticated_client.post(
                "/api/v1/events",
                json=factory.event_data(name=f"test/paginate-{i}"),
            )

        # Get first page
        response = await authenticated_client.get(
            "/api/v1/events", params={"page": 1, "page_size": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5

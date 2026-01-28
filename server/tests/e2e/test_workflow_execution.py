"""End-to-end tests for complete workflow execution."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWorkflowExecution:
    """E2E tests for complete workflow execution flows."""

    async def test_event_to_run_flow(
        self,
        authenticated_client: AsyncClient,
        test_function,
        factory,
    ):
        """Test the complete event -> function -> run flow."""
        # Create an event that matches the test function's trigger
        response = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(
                name="test/event",  # Matches test_function trigger
                data={"prompt": "Hello, world!"},
            ),
        )
        assert response.status_code == 201
        data = response.json()

        # Should have created a run
        assert "run_id" in data
        run_id = data["run_id"]

        # Verify run was created
        if run_id:
            run_response = await authenticated_client.get(f"/api/v1/runs/{run_id}")
            assert run_response.status_code == 200
            run_data = run_response.json()
            assert run_data["status"] in ("pending", "running", "completed")

    async def test_inline_function_creation_and_trigger(
        self,
        authenticated_client: AsyncClient,
        factory,
    ):
        """Test creating an inline function and triggering it."""
        # Create inline function
        fn_response = await authenticated_client.post(
            "/api/v1/functions/inline",
            json=factory.inline_function_data(
                function_id="e2e-inline-fn",
                trigger_event="e2e/test",
            ),
        )
        assert fn_response.status_code == 201

        # Trigger with event
        event_response = await authenticated_client.post(
            "/api/v1/events",
            json=factory.event_data(
                name="e2e/test",
                data={"prompt": "Test prompt"},
            ),
        )
        assert event_response.status_code == 201

    async def test_list_runs_for_function(
        self,
        authenticated_client: AsyncClient,
        test_function,
        factory,
    ):
        """Test listing runs filtered by function."""
        # Create events to generate runs
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/events",
                json=factory.event_data(name="test/event"),
            )

        # List runs for the function
        response = await authenticated_client.get(
            "/api/v1/runs",
            params={"function_id": test_function.function_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data

    async def test_cancel_pending_run(
        self,
        authenticated_client: AsyncClient,
        test_run,
    ):
        """Test cancelling a pending run."""
        run_id = str(test_run.id)

        response = await authenticated_client.post(f"/api/v1/runs/{run_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled" in data["message"].lower()

    async def test_replay_run(
        self,
        authenticated_client: AsyncClient,
        test_run,
    ):
        """Test replaying a run."""
        run_id = str(test_run.id)

        response = await authenticated_client.post(f"/api/v1/runs/{run_id}/replay")
        assert response.status_code == 200
        data = response.json()
        # Should create a new run
        assert data["id"] != run_id
        assert data["status"] == "pending"

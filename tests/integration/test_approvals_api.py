"""Integration tests for tool approvals API endpoints."""

import pytest
import uuid
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from flowforge_server.db.models import ToolApproval, ApprovalStatus, Run, Function, Tenant, Step
from flowforge_server.api.app import app


# Default tenant ID used in the API
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=DEFAULT_TENANT_ID,
        name="Test Tenant",
        api_key="test-api-key",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_function(db_session: AsyncSession, test_tenant: Tenant) -> Function:
    """Create a test function."""
    func = Function(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        function_id="test-function",
        name="Test Function",
        config={},
    )
    db_session.add(func)
    await db_session.commit()
    await db_session.refresh(func)
    return func


@pytest.fixture
async def test_run(db_session: AsyncSession, test_function: Function) -> Run:
    """Create a test run."""
    run = Run(
        id=uuid.uuid4(),
        tenant_id=test_function.tenant_id,
        function_id=test_function.id,
        event_id=uuid.uuid4(),
        status="running",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.fixture
async def test_step(db_session: AsyncSession, test_run: Run) -> Step:
    """Create a test step."""
    step = Step(
        id=uuid.uuid4(),
        run_id=test_run.id,
        step_id="approval-step",
        status="waiting",
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)
    return step


@pytest.fixture
async def pending_approval(
    db_session: AsyncSession,
    test_run: Run,
    test_step: Step,
) -> ToolApproval:
    """Create a pending tool approval."""
    approval = ToolApproval(
        id=uuid.uuid4(),
        run_id=test_run.id,
        step_id=test_step.id,
        tool_name="send_email",
        tool_call_id="call_123",
        tool_arguments={"to": "user@example.com", "subject": "Test"},
        status=ApprovalStatus.PENDING,
        requested_at=datetime.utcnow(),
        timeout_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)
    return approval


@pytest.fixture
async def approved_approval(
    db_session: AsyncSession,
    test_run: Run,
    test_step: Step,
) -> ToolApproval:
    """Create an already approved tool approval."""
    approval = ToolApproval(
        id=uuid.uuid4(),
        run_id=test_run.id,
        step_id=test_step.id,
        tool_name="send_notification",
        tool_call_id="call_456",
        tool_arguments={"message": "Hello"},
        status=ApprovalStatus.APPROVED,
        requested_at=datetime.utcnow() - timedelta(minutes=10),
        timeout_at=datetime.utcnow() + timedelta(minutes=20),
        resolved_at=datetime.utcnow() - timedelta(minutes=5),
        resolved_by="admin@example.com",
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)
    return approval


class TestListApprovals:
    """Test GET /api/v1/approvals endpoint."""

    @pytest.mark.asyncio
    async def test_list_all_approvals(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
        approved_approval: ToolApproval,
    ):
        """Test listing all approvals."""
        response = await client.get("/api/v1/approvals")

        assert response.status_code == 200
        data = response.json()

        assert "approvals" in data
        assert "total" in data
        assert data["total"] >= 2
        assert len(data["approvals"]) >= 2

        # Check that approvals contain required fields
        approval = data["approvals"][0]
        assert "id" in approval
        assert "run_id" in approval
        assert "tool_name" in approval
        assert "status" in approval
        assert "requested_at" in approval

    @pytest.mark.asyncio
    async def test_list_pending_approvals_only(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
        approved_approval: ToolApproval,
    ):
        """Test filtering to show only pending approvals."""
        response = await client.get("/api/v1/approvals?pending_only=true")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1
        # All returned approvals should be pending
        for approval in data["approvals"]:
            assert approval["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_approvals_by_status(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
        approved_approval: ToolApproval,
    ):
        """Test filtering approvals by status."""
        response = await client.get("/api/v1/approvals?status=approved")

        assert response.status_code == 200
        data = response.json()

        # All returned approvals should be approved
        for approval in data["approvals"]:
            assert approval["status"] == "approved"

    @pytest.mark.asyncio
    async def test_list_approvals_by_run_id(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
        test_run: Run,
    ):
        """Test filtering approvals by run ID."""
        response = await client.get(f"/api/v1/approvals?run_id={test_run.id}")

        assert response.status_code == 200
        data = response.json()

        # All returned approvals should be for this run
        for approval in data["approvals"]:
            assert approval["run_id"] == str(test_run.id)

    @pytest.mark.asyncio
    async def test_list_approvals_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_run: Run,
        test_step: Step,
    ):
        """Test pagination of approval list."""
        # Create multiple approvals
        for i in range(15):
            approval = ToolApproval(
                id=uuid.uuid4(),
                run_id=test_run.id,
                step_id=test_step.id,
                tool_name=f"tool_{i}",
                tool_call_id=f"call_{i}",
                tool_arguments={},
                status=ApprovalStatus.PENDING,
                requested_at=datetime.utcnow(),
                timeout_at=datetime.utcnow() + timedelta(minutes=30),
            )
            db_session.add(approval)
        await db_session.commit()

        # Test first page
        response = await client.get("/api/v1/approvals?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["approvals"]) == 10

        # Test second page
        response = await client.get("/api/v1/approvals?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["approvals"]) >= 5

    @pytest.mark.asyncio
    async def test_list_approvals_invalid_run_id(self, client: AsyncClient):
        """Test error handling for invalid run ID format."""
        response = await client.get("/api/v1/approvals?run_id=invalid-uuid")

        assert response.status_code == 400
        assert "Invalid run ID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_approvals_invalid_status(self, client: AsyncClient):
        """Test error handling for invalid status filter."""
        response = await client.get("/api/v1/approvals?status=invalid_status")

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]


class TestGetApproval:
    """Test GET /api/v1/approvals/{approval_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_approval_success(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
    ):
        """Test retrieving a specific approval by ID."""
        response = await client.get(f"/api/v1/approvals/{pending_approval.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(pending_approval.id)
        assert data["run_id"] == str(pending_approval.run_id)
        assert data["tool_name"] == pending_approval.tool_name
        assert data["tool_call_id"] == pending_approval.tool_call_id
        assert data["status"] == "pending"
        assert data["tool_arguments"] == pending_approval.tool_arguments

    @pytest.mark.asyncio
    async def test_get_approval_not_found(self, client: AsyncClient):
        """Test 404 error for non-existent approval."""
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/approvals/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_approval_invalid_id_format(self, client: AsyncClient):
        """Test error handling for invalid approval ID format."""
        response = await client.get("/api/v1/approvals/invalid-uuid")

        assert response.status_code == 400
        assert "Invalid approval ID" in response.json()["detail"]


class TestApproveToolCall:
    """Test POST /api/v1/approvals/{approval_id}/approve endpoint."""

    @pytest.mark.asyncio
    async def test_approve_pending_tool_call(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        pending_approval: ToolApproval,
    ):
        """Test approving a pending tool call."""
        request_data = {"resolved_by": "admin@example.com"}

        response = await client.post(
            f"/api/v1/approvals/{pending_approval.id}/approve",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "approved successfully" in data["message"]
        assert data["approval_id"] == str(pending_approval.id)

        # Verify database was updated
        await db_session.refresh(pending_approval)
        assert pending_approval.status == ApprovalStatus.APPROVED
        assert pending_approval.resolved_by == "admin@example.com"
        assert pending_approval.resolved_at is not None

    @pytest.mark.asyncio
    async def test_approve_without_resolved_by(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
    ):
        """Test approving without specifying who approved."""
        response = await client.post(
            f"/api/v1/approvals/{pending_approval.id}/approve",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_approve_already_approved(
        self,
        client: AsyncClient,
        approved_approval: ToolApproval,
    ):
        """Test error when trying to approve an already approved tool call."""
        response = await client.post(
            f"/api/v1/approvals/{approved_approval.id}/approve",
            json={},
        )

        assert response.status_code == 400
        assert "Cannot approve" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_approve_expired_approval(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_run: Run,
        test_step: Step,
    ):
        """Test error when trying to approve an expired approval."""
        expired_approval = ToolApproval(
            id=uuid.uuid4(),
            run_id=test_run.id,
            step_id=test_step.id,
            tool_name="expired_tool",
            tool_call_id="call_expired",
            tool_arguments={},
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow() - timedelta(hours=2),
            timeout_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        )
        db_session.add(expired_approval)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/approvals/{expired_approval.id}/approve",
            json={},
        )

        assert response.status_code == 400
        assert "timed out" in response.json()["detail"]

        # Verify status was updated to timeout
        await db_session.refresh(expired_approval)
        assert expired_approval.status == ApprovalStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_approve_nonexistent_approval(self, client: AsyncClient):
        """Test error when approving non-existent approval."""
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/approvals/{fake_id}/approve",
            json={},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_approve_invalid_id_format(self, client: AsyncClient):
        """Test error handling for invalid approval ID format."""
        response = await client.post(
            "/api/v1/approvals/invalid-uuid/approve",
            json={},
        )

        assert response.status_code == 400
        assert "Invalid approval ID" in response.json()["detail"]


class TestRejectToolCall:
    """Test POST /api/v1/approvals/{approval_id}/reject endpoint."""

    @pytest.mark.asyncio
    async def test_reject_pending_tool_call(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        pending_approval: ToolApproval,
    ):
        """Test rejecting a pending tool call."""
        request_data = {
            "reason": "Security concerns",
            "resolved_by": "security@example.com",
        }

        response = await client.post(
            f"/api/v1/approvals/{pending_approval.id}/reject",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "rejected successfully" in data["message"]
        assert data["approval_id"] == str(pending_approval.id)

        # Verify database was updated
        await db_session.refresh(pending_approval)
        assert pending_approval.status == ApprovalStatus.REJECTED
        assert pending_approval.resolved_by == "security@example.com"
        assert pending_approval.rejection_reason == "Security concerns"
        assert pending_approval.resolved_at is not None

    @pytest.mark.asyncio
    async def test_reject_without_resolved_by(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        pending_approval: ToolApproval,
    ):
        """Test rejecting without specifying who rejected."""
        request_data = {"reason": "Not needed"}

        response = await client.post(
            f"/api/v1/approvals/{pending_approval.id}/reject",
            json=request_data,
        )

        assert response.status_code == 200

        await db_session.refresh(pending_approval)
        assert pending_approval.status == ApprovalStatus.REJECTED
        assert pending_approval.rejection_reason == "Not needed"

    @pytest.mark.asyncio
    async def test_reject_missing_reason(
        self,
        client: AsyncClient,
        pending_approval: ToolApproval,
    ):
        """Test error when rejecting without providing a reason."""
        response = await client.post(
            f"/api/v1/approvals/{pending_approval.id}/reject",
            json={},  # Missing required 'reason' field
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_reject_already_approved(
        self,
        client: AsyncClient,
        approved_approval: ToolApproval,
    ):
        """Test error when trying to reject an already approved tool call."""
        response = await client.post(
            f"/api/v1/approvals/{approved_approval.id}/reject",
            json={"reason": "Changed my mind"},
        )

        assert response.status_code == 400
        assert "Cannot reject" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_expired_approval(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_run: Run,
        test_step: Step,
    ):
        """Test error when trying to reject an expired approval."""
        expired_approval = ToolApproval(
            id=uuid.uuid4(),
            run_id=test_run.id,
            step_id=test_step.id,
            tool_name="expired_tool",
            tool_call_id="call_expired",
            tool_arguments={},
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow() - timedelta(hours=2),
            timeout_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db_session.add(expired_approval)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/approvals/{expired_approval.id}/reject",
            json={"reason": "Too late"},
        )

        assert response.status_code == 400
        assert "timed out" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_nonexistent_approval(self, client: AsyncClient):
        """Test error when rejecting non-existent approval."""
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/approvals/{fake_id}/reject",
            json={"reason": "Test"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestApprovalWorkflow:
    """Test complete approval workflow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_approval_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_run: Run,
        test_step: Step,
    ):
        """Test a complete workflow: create, list, approve."""
        # Create an approval
        approval = ToolApproval(
            id=uuid.uuid4(),
            run_id=test_run.id,
            step_id=test_step.id,
            tool_name="delete_resource",
            tool_call_id="call_workflow",
            tool_arguments={"resource_id": "res_123"},
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow(),
            timeout_at=datetime.utcnow() + timedelta(hours=1),
        )
        db_session.add(approval)
        await db_session.commit()

        # List pending approvals
        list_response = await client.get("/api/v1/approvals?pending_only=true")
        assert list_response.status_code == 200
        assert any(a["id"] == str(approval.id) for a in list_response.json()["approvals"])

        # Get specific approval
        get_response = await client.get(f"/api/v1/approvals/{approval.id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "pending"

        # Approve it
        approve_response = await client.post(
            f"/api/v1/approvals/{approval.id}/approve",
            json={"resolved_by": "workflow_test"},
        )
        assert approve_response.status_code == 200

        # Verify status changed
        final_response = await client.get(f"/api/v1/approvals/{approval.id}")
        assert final_response.json()["status"] == "approved"
        assert final_response.json()["resolved_by"] == "workflow_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

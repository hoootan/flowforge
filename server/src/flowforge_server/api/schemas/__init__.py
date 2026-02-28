"""Pydantic schemas for API requests and responses."""

from flowforge_server.api.schemas.approvals import (
    ApprovalActionResponse,
    ApprovalsResponse,
    ApproveToolRequest,
    RejectToolRequest,
    ToolApprovalResponse,
    ToolCallResponse,
    ToolCallsResponse,
)
from flowforge_server.api.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeysResponse,
    RevokeApiKeyRequest,
    TokenRequest,
    TokenResponse,
)
from flowforge_server.api.schemas.events import (
    EventCreate,
    EventResponse,
    EventsResponse,
)
from flowforge_server.api.schemas.functions import (
    AgentConfigSchema,
    FunctionCreate,
    FunctionResponse,
    FunctionsResponse,
    FunctionUpdate,
    InlineFunctionCreate,
    TriggerSchema,
)
from flowforge_server.api.schemas.runs import (
    RunResponse,
    RunsResponse,
    StepResponse,
)
from flowforge_server.api.schemas.tools import (
    ToolCreate,
    ToolResponse,
    ToolsResponse,
    ToolUpdate,
)
from flowforge_server.api.schemas.users import (
    UserCreate,
    UserLogin,
    UserLoginResponse,
    UserMeResponse,
    UserPasswordUpdate,
    UserResponse,
    UsersResponse,
    UserUpdate,
)

__all__ = [
    # Events
    "EventCreate",
    "EventResponse",
    "EventsResponse",
    # Functions
    "FunctionCreate",
    "FunctionResponse",
    "FunctionUpdate",
    "FunctionsResponse",
    "InlineFunctionCreate",
    "AgentConfigSchema",
    "TriggerSchema",
    # Runs
    "RunResponse",
    "RunsResponse",
    "StepResponse",
    # Tools
    "ToolCreate",
    "ToolResponse",
    "ToolUpdate",
    "ToolsResponse",
    # Approvals
    "ToolApprovalResponse",
    "ApprovalsResponse",
    "ApproveToolRequest",
    "RejectToolRequest",
    "ApprovalActionResponse",
    "ToolCallResponse",
    "ToolCallsResponse",
    # Auth
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "ApiKeysResponse",
    "TokenRequest",
    "TokenResponse",
    "RevokeApiKeyRequest",
    # Users
    "UserLogin",
    "UserLoginResponse",
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserResponse",
    "UsersResponse",
    "UserMeResponse",
]

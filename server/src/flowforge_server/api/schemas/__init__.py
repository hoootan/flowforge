"""Pydantic schemas for API requests and responses."""

from flowforge_server.api.schemas.events import (
    EventCreate,
    EventResponse,
    EventsResponse,
)
from flowforge_server.api.schemas.functions import (
    FunctionCreate,
    FunctionResponse,
    FunctionUpdate,
    FunctionsResponse,
    InlineFunctionCreate,
    AgentConfigSchema,
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
    ToolUpdate,
    ToolsResponse,
)
from flowforge_server.api.schemas.approvals import (
    ToolApprovalResponse,
    ApprovalsResponse,
    ApproveToolRequest,
    RejectToolRequest,
    ApprovalActionResponse,
    ToolCallResponse,
    ToolCallsResponse,
)
from flowforge_server.api.schemas.auth import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    ApiKeysResponse,
    TokenRequest,
    TokenResponse,
    RevokeApiKeyRequest,
)
from flowforge_server.api.schemas.users import (
    UserLogin,
    UserLoginResponse,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserResponse,
    UsersResponse,
    UserMeResponse,
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

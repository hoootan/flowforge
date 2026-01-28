"""Enhanced streaming module for AI generation.

Provides typed events, composable transformers, and middleware
for processing and enriching streaming AI responses.
"""

from .events import (
    AnyStreamEvent,
    ApprovalRequiredEvent,
    ApprovalResolvedEvent,
    ContentChunkEvent,
    ErrorEvent,
    IterationCompleteEvent,
    PartialObjectEvent,
    ProgressEvent,
    StreamCompleteEvent,
    StreamEvent,
    ThinkingEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from .middleware import (
    ProgressCallback,
    ProgressInfo,
    ProgressTracker,
    StreamMetrics,
    StreamMiddleware,
    create_logging_middleware,
    create_metrics_middleware,
)
from .transformers import (
    BufferTransformer,
    PartialObjectTransformer,
    ProgressEstimatorTransformer,
    StreamTransformer,
    ThrottleTransformer,
    TokenCounterTransformer,
    compose_transformers,
)

__all__ = [
    # Events
    "StreamEvent",
    "ContentChunkEvent",
    "PartialObjectEvent",
    "ToolCallStartEvent",
    "ToolCallEndEvent",
    "ProgressEvent",
    "ThinkingEvent",
    "ApprovalRequiredEvent",
    "ApprovalResolvedEvent",
    "IterationCompleteEvent",
    "StreamCompleteEvent",
    "ErrorEvent",
    "AnyStreamEvent",
    # Transformers
    "StreamTransformer",
    "TokenCounterTransformer",
    "ProgressEstimatorTransformer",
    "PartialObjectTransformer",
    "ThrottleTransformer",
    "BufferTransformer",
    "compose_transformers",
    # Middleware
    "StreamMiddleware",
    "StreamMetrics",
    "ProgressTracker",
    "ProgressInfo",
    "ProgressCallback",
    "create_metrics_middleware",
    "create_logging_middleware",
]

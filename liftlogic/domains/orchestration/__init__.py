"""
Orchestration Domain - Query routing and pipeline coordination.

This domain handles:
- Model selection and routing
- Response caching
- Query pipeline orchestration
- Multi-step reasoning coordination
"""

from .cache import ResponseCacheImpl
from .contracts import PipelineOrchestrator, QueryRouter, ResponseCache
from .models import (
    CachedResponse,
    PipelineResult,
    Query,
    QueryType,
    RoutingDecision,
)
from .pipeline import QueryPipeline
from .router import SmartRouter

__all__ = [
    # Contracts
    "QueryRouter",
    "ResponseCache",
    "PipelineOrchestrator",
    # Models
    "Query",
    "QueryType",
    "RoutingDecision",
    "CachedResponse",
    "PipelineResult",
    # Implementations
    "SmartRouter",
    "ResponseCacheImpl",
    "QueryPipeline",
]

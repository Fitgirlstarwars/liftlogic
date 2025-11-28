"""
Orchestration Domain - Query routing and pipeline coordination.

This domain handles:
- Model selection and routing
- Response caching
- Query pipeline orchestration
- Multi-step reasoning coordination
"""

from .contracts import QueryRouter, ResponseCache, PipelineOrchestrator
from .models import (
    Query,
    QueryType,
    RoutingDecision,
    CachedResponse,
    PipelineResult,
)
from .router import SmartRouter
from .cache import ResponseCacheImpl
from .pipeline import QueryPipeline

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

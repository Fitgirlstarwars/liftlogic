"""
Orchestration Models - Data types for orchestration domain.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Types of queries for routing."""

    FAULT_DIAGNOSIS = "fault_diagnosis"
    GENERAL_SEARCH = "general_search"
    COMPONENT_LOOKUP = "component_lookup"
    SAFETY_ANALYSIS = "safety_analysis"
    MAINTENANCE_QUERY = "maintenance_query"
    DOCUMENT_EXTRACTION = "document_extraction"
    CONVERSATIONAL = "conversational"
    UNKNOWN = "unknown"


class ModelTier(str, Enum):
    """Model capability tiers."""

    FAST = "fast"  # Quick responses, lower cost
    BALANCED = "balanced"  # Standard quality
    PREMIUM = "premium"  # Highest quality, higher cost
    LOCAL = "local"  # Local model (Ollama)


class Query(BaseModel):
    """Incoming query to be processed."""

    id: str = ""
    text: str
    query_type: QueryType = QueryType.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoutingDecision(BaseModel):
    """Decision about how to route a query."""

    query_id: str
    query_type: QueryType
    model_tier: ModelTier = ModelTier.BALANCED
    pipeline: str  # Which pipeline to use
    use_cache: bool = True
    use_rag: bool = True
    use_knowledge_graph: bool = False
    confidence: float = 0.0
    reasoning: str = ""


class CachedResponse(BaseModel):
    """Cached query response."""

    key: str
    response: Any
    query_type: QueryType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    hit_count: int = 0


class PipelineStep(BaseModel):
    """Single step in a pipeline execution."""

    name: str
    status: str  # pending, running, completed, failed
    duration_ms: float = 0.0
    output: Any = None
    error: str | None = None


class PipelineResult(BaseModel):
    """Result of pipeline execution."""

    query_id: str
    success: bool
    response: Any = None
    error: str | None = None
    steps: list[PipelineStep] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    model_used: str = ""
    tokens_used: int = 0
    cache_hit: bool = False
    sources: list[str] = Field(default_factory=list)

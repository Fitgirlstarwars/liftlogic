"""
Smart Router - Intelligent query routing based on classification.

Routes queries to appropriate models and pipelines based on
query type, complexity, and available resources.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING

from .models import Query, QueryType, RoutingDecision, ModelTier

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient

logger = logging.getLogger(__name__)

__all__ = ["SmartRouter"]

# Pattern-based query classification
FAULT_PATTERNS = [
    r"\b[A-Z]{1,3}[-_]?\d{2,4}\b",  # F505, E-42, ERR001
    r"\bfault\s*(code)?\b",
    r"\berror\s*(code)?\b",
    r"\balarm\b",
]

SAFETY_PATTERNS = [
    r"\bsafety\b",
    r"\bhazard\b",
    r"\brisk\b",
    r"\bdanger\b",
    r"\bemergency\b",
    r"\bcritical\b",
    r"\block\s*out\b",
    r"\btag\s*out\b",
]

MAINTENANCE_PATTERNS = [
    r"\bmaintenance\b",
    r"\bschedule\b",
    r"\binspection\b",
    r"\bpreventive\b",
    r"\bservice\b",
    r"\binterval\b",
]

COMPONENT_PATTERNS = [
    r"\bcomponent\b",
    r"\bpart\b",
    r"\brelay\b",
    r"\bcontactor\b",
    r"\bmotor\b",
    r"\bdrive\b",
    r"\bcontroller\b",
    r"\bsensor\b",
]


class SmartRouter:
    """
    Intelligent query router.

    Classifies queries and determines optimal routing based on:
    - Query type (fault, safety, maintenance, etc.)
    - Query complexity
    - Available models and resources
    """

    def __init__(
        self,
        llm_client: GeminiClient | None = None,
        enable_llm_classification: bool = True,
    ) -> None:
        """
        Initialize router.

        Args:
            llm_client: Optional LLM for complex classification
            enable_llm_classification: Use LLM for ambiguous queries
        """
        self._llm = llm_client
        self._enable_llm = enable_llm_classification

    async def route(self, query: Query) -> RoutingDecision:
        """Determine how to route a query."""
        query_id = query.id or str(uuid.uuid4())
        query_type = await self.classify_query(query)

        # Determine model tier based on query type
        model_tier = self._select_model_tier(query_type, query)

        # Select pipeline
        pipeline = self._select_pipeline(query_type)

        # Determine feature flags
        use_rag = query_type in (
            QueryType.GENERAL_SEARCH,
            QueryType.FAULT_DIAGNOSIS,
            QueryType.COMPONENT_LOOKUP,
        )
        use_knowledge_graph = query_type in (
            QueryType.FAULT_DIAGNOSIS,
            QueryType.COMPONENT_LOOKUP,
        )

        decision = RoutingDecision(
            query_id=query_id,
            query_type=query_type,
            model_tier=model_tier,
            pipeline=pipeline,
            use_cache=True,
            use_rag=use_rag,
            use_knowledge_graph=use_knowledge_graph,
            confidence=0.8,
            reasoning=f"Classified as {query_type.value}, using {pipeline} pipeline",
        )

        logger.info(
            "Routed query %s: type=%s, pipeline=%s, model=%s",
            query_id[:8],
            query_type.value,
            pipeline,
            model_tier.value,
        )

        return decision

    async def classify_query(self, query: Query) -> QueryType:
        """Classify query type."""
        text = query.text.lower()

        # Try pattern-based classification first (fast)
        pattern_result = self._pattern_classify(text)
        if pattern_result != QueryType.UNKNOWN:
            return pattern_result

        # Use LLM for ambiguous queries if enabled
        if self._enable_llm and self._llm:
            return await self._llm_classify(query)

        return QueryType.GENERAL_SEARCH

    def _pattern_classify(self, text: str) -> QueryType:
        """Pattern-based query classification."""
        text_lower = text.lower()

        # Check fault patterns
        for pattern in FAULT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return QueryType.FAULT_DIAGNOSIS

        # Check safety patterns
        for pattern in SAFETY_PATTERNS:
            if re.search(pattern, text_lower):
                return QueryType.SAFETY_ANALYSIS

        # Check maintenance patterns
        for pattern in MAINTENANCE_PATTERNS:
            if re.search(pattern, text_lower):
                return QueryType.MAINTENANCE_QUERY

        # Check component patterns
        for pattern in COMPONENT_PATTERNS:
            if re.search(pattern, text_lower):
                return QueryType.COMPONENT_LOOKUP

        # Check for extraction requests
        if any(word in text_lower for word in ["extract", "parse", "pdf", "document"]):
            return QueryType.DOCUMENT_EXTRACTION

        # Check for conversational markers
        if any(
            text_lower.startswith(word)
            for word in ["hi", "hello", "hey", "thanks", "thank you"]
        ):
            return QueryType.CONVERSATIONAL

        return QueryType.UNKNOWN

    async def _llm_classify(self, query: Query) -> QueryType:
        """Use LLM to classify ambiguous queries."""
        if not self._llm:
            return QueryType.GENERAL_SEARCH

        prompt = f"""Classify this elevator-related query into one category:

Query: "{query.text}"

Categories:
- fault_diagnosis: Questions about fault codes, errors, troubleshooting
- general_search: General information lookup
- component_lookup: Questions about specific components
- safety_analysis: Safety-related questions
- maintenance_query: Maintenance schedules, procedures
- document_extraction: Requests to extract/parse documents
- conversational: Greetings, thanks, small talk

Respond with just the category name."""

        try:
            response = await self._llm.generate(prompt)
            category = response.text.strip().lower()

            type_map = {
                "fault_diagnosis": QueryType.FAULT_DIAGNOSIS,
                "general_search": QueryType.GENERAL_SEARCH,
                "component_lookup": QueryType.COMPONENT_LOOKUP,
                "safety_analysis": QueryType.SAFETY_ANALYSIS,
                "maintenance_query": QueryType.MAINTENANCE_QUERY,
                "document_extraction": QueryType.DOCUMENT_EXTRACTION,
                "conversational": QueryType.CONVERSATIONAL,
            }

            return type_map.get(category, QueryType.GENERAL_SEARCH)
        except Exception as e:
            logger.warning("LLM classification failed: %s", e)
            return QueryType.GENERAL_SEARCH

    def _select_model_tier(self, query_type: QueryType, query: Query) -> ModelTier:
        """Select appropriate model tier."""
        # Premium for safety-critical queries
        if query_type == QueryType.SAFETY_ANALYSIS:
            return ModelTier.PREMIUM

        # Premium for complex fault diagnosis
        if query_type == QueryType.FAULT_DIAGNOSIS:
            # Check query complexity
            if len(query.text) > 200 or "multiple" in query.text.lower():
                return ModelTier.PREMIUM
            return ModelTier.BALANCED

        # Fast for simple queries
        if query_type in (QueryType.CONVERSATIONAL, QueryType.COMPONENT_LOOKUP):
            return ModelTier.FAST

        return ModelTier.BALANCED

    def _select_pipeline(self, query_type: QueryType) -> str:
        """Select processing pipeline for query type."""
        pipeline_map = {
            QueryType.FAULT_DIAGNOSIS: "diagnosis",
            QueryType.GENERAL_SEARCH: "rag_search",
            QueryType.COMPONENT_LOOKUP: "component_search",
            QueryType.SAFETY_ANALYSIS: "safety",
            QueryType.MAINTENANCE_QUERY: "maintenance",
            QueryType.DOCUMENT_EXTRACTION: "extraction",
            QueryType.CONVERSATIONAL: "simple",
            QueryType.UNKNOWN: "rag_search",
        }
        return pipeline_map.get(query_type, "rag_search")

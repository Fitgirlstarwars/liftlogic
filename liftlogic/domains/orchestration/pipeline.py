"""
Query Pipeline - Orchestrates query processing through domains.

Coordinates search, diagnosis, and knowledge graph operations
to produce comprehensive responses.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from .models import (
    Query,
    QueryType,
    PipelineResult,
    PipelineStep,
)
from .router import SmartRouter
from .cache import ResponseCacheImpl

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient
    from liftlogic.domains.search import HybridSearchEngine
    from liftlogic.domains.knowledge import KnowledgeGraphStore, GraphReasoner
    from liftlogic.domains.diagnosis import FaultDiagnosisAgent

logger = logging.getLogger(__name__)

__all__ = ["QueryPipeline"]


class QueryPipeline:
    """
    Main query orchestration pipeline.

    Coordinates:
    - Query routing and classification
    - Response caching
    - RAG retrieval
    - Knowledge graph reasoning
    - Expert agent diagnosis
    - Response generation
    """

    def __init__(
        self,
        llm_client: GeminiClient,
        search_engine: HybridSearchEngine | None = None,
        graph_store: KnowledgeGraphStore | None = None,
        reasoner: GraphReasoner | None = None,
        diagnosis_agent: FaultDiagnosisAgent | None = None,
        cache: ResponseCacheImpl | None = None,
    ) -> None:
        """
        Initialize pipeline.

        Args:
            llm_client: Gemini client for generation
            search_engine: Hybrid search engine for RAG
            graph_store: Knowledge graph store
            reasoner: Graph reasoner for causal analysis
            diagnosis_agent: Fault diagnosis agent
            cache: Response cache
        """
        self._llm = llm_client
        self._search = search_engine
        self._graph = graph_store
        self._reasoner = reasoner
        self._diagnosis = diagnosis_agent
        self._cache = cache or ResponseCacheImpl()
        self._router = SmartRouter(llm_client)

    async def execute(self, query: Query) -> PipelineResult:
        """Execute query through pipeline."""
        return await self.execute_with_context(query, {})

    async def execute_with_context(
        self,
        query: Query,
        context: dict,
    ) -> PipelineResult:
        """Execute query with additional context."""
        start_time = time.time()
        query_id = query.id or str(uuid.uuid4())
        steps: list[PipelineStep] = []

        try:
            # Step 1: Check cache
            cache_key = ResponseCacheImpl.generate_key(query.text, context)
            cached = await self._cache.get(cache_key)
            if cached:
                return PipelineResult(
                    query_id=query_id,
                    success=True,
                    response=cached.response,
                    cache_hit=True,
                    total_duration_ms=(time.time() - start_time) * 1000,
                )

            # Step 2: Route query
            step_start = time.time()
            routing = await self._router.route(query)
            steps.append(
                PipelineStep(
                    name="routing",
                    status="completed",
                    duration_ms=(time.time() - step_start) * 1000,
                    output={"type": routing.query_type.value, "pipeline": routing.pipeline},
                )
            )

            # Step 3: Execute appropriate pipeline
            response: Any = None
            sources: list[str] = []

            if routing.pipeline == "diagnosis":
                response, sources = await self._execute_diagnosis(query, context, steps)
            elif routing.pipeline == "rag_search":
                response, sources = await self._execute_rag(query, context, steps)
            elif routing.pipeline == "safety":
                response, sources = await self._execute_safety(query, context, steps)
            elif routing.pipeline == "simple":
                response, sources = await self._execute_simple(query, context, steps)
            else:
                response, sources = await self._execute_rag(query, context, steps)

            # Cache successful response
            await self._cache.set(
                cache_key,
                response,
                query_type=routing.query_type,
            )

            total_duration = (time.time() - start_time) * 1000
            return PipelineResult(
                query_id=query_id,
                success=True,
                response=response,
                steps=steps,
                total_duration_ms=total_duration,
                model_used=self._llm.model if self._llm else "",
                sources=sources,
            )

        except Exception as e:
            logger.error("Pipeline execution failed: %s", e)
            return PipelineResult(
                query_id=query_id,
                success=False,
                error=str(e),
                steps=steps,
                total_duration_ms=(time.time() - start_time) * 1000,
            )

    async def _execute_diagnosis(
        self,
        query: Query,
        context: dict,
        steps: list[PipelineStep],
    ) -> tuple[Any, list[str]]:
        """Execute fault diagnosis pipeline."""
        sources: list[str] = []

        # Extract fault code from query
        import re
        fault_match = re.search(r"\b[A-Z]{1,3}[-_]?\d{2,4}\b", query.text)
        fault_code = fault_match.group() if fault_match else query.text

        # Get knowledge graph context
        graph_context = ""
        if self._reasoner:
            step_start = time.time()
            try:
                chain = await self._reasoner.find_causes(fault_code)
                if chain.explanation:
                    graph_context = chain.explanation
                    sources.extend(chain.root_causes)
            except Exception as e:
                logger.warning("Graph reasoning failed: %s", e)

            steps.append(
                PipelineStep(
                    name="knowledge_graph",
                    status="completed",
                    duration_ms=(time.time() - step_start) * 1000,
                )
            )

        # Use diagnosis agent if available
        if self._diagnosis:
            step_start = time.time()
            diagnosis = await self._diagnosis.diagnose(
                fault_code=fault_code,
                symptoms=query.metadata.get("symptoms", []),
                context=context,
            )
            steps.append(
                PipelineStep(
                    name="diagnosis",
                    status="completed",
                    duration_ms=(time.time() - step_start) * 1000,
                    output=diagnosis.model_dump(),
                )
            )
            return diagnosis.model_dump(), sources

        # Fallback to direct LLM
        return await self._generate_response(
            query.text,
            context=graph_context,
            system_prompt="You are an expert elevator technician. Diagnose faults accurately.",
        ), sources

    async def _execute_rag(
        self,
        query: Query,
        context: dict,
        steps: list[PipelineStep],
    ) -> tuple[Any, list[str]]:
        """Execute RAG search pipeline."""
        sources: list[str] = []
        retrieved_context = ""

        # Perform hybrid search
        if self._search:
            step_start = time.time()
            try:
                from liftlogic.domains.search import SearchQuery
                search_query = SearchQuery(query=query.text)
                results = await self._search.search(search_query)

                # Build context from results
                context_parts = []
                for result in results[:5]:  # Top 5 results
                    context_parts.append(f"[Source: {result.source}]\n{result.content}")
                    sources.append(result.source)

                retrieved_context = "\n\n---\n\n".join(context_parts)

            except Exception as e:
                logger.warning("Search failed: %s", e)

            steps.append(
                PipelineStep(
                    name="retrieval",
                    status="completed",
                    duration_ms=(time.time() - step_start) * 1000,
                    output={"results_count": len(sources)},
                )
            )

        # Generate response with context
        step_start = time.time()
        response = await self._generate_response(
            query.text,
            context=retrieved_context,
            system_prompt=(
                "You are an expert elevator technician assistant. "
                "Use the provided context to answer accurately. "
                "Cite sources when possible."
            ),
        )

        steps.append(
            PipelineStep(
                name="generation",
                status="completed",
                duration_ms=(time.time() - step_start) * 1000,
            )
        )

        return response, sources

    async def _execute_safety(
        self,
        query: Query,
        context: dict,
        steps: list[PipelineStep],
    ) -> tuple[Any, list[str]]:
        """Execute safety analysis pipeline."""
        # First get relevant safety documentation via RAG
        response, sources = await self._execute_rag(query, context, steps)

        # Enhance with safety-specific prompt
        step_start = time.time()
        safety_response = await self._generate_response(
            query.text,
            context=str(response),
            system_prompt=(
                "You are a safety expert for elevator systems. "
                "Prioritize safety above all else. "
                "Always mention relevant safety standards (EN81, ASME A17.1). "
                "Highlight any critical warnings clearly."
            ),
        )

        steps.append(
            PipelineStep(
                name="safety_enhancement",
                status="completed",
                duration_ms=(time.time() - step_start) * 1000,
            )
        )

        return safety_response, sources

    async def _execute_simple(
        self,
        query: Query,
        context: dict,
        steps: list[PipelineStep],
    ) -> tuple[Any, list[str]]:
        """Execute simple conversational pipeline."""
        step_start = time.time()
        response = await self._generate_response(
            query.text,
            system_prompt=(
                "You are a helpful elevator technician assistant. "
                "Be friendly and concise."
            ),
        )

        steps.append(
            PipelineStep(
                name="generation",
                status="completed",
                duration_ms=(time.time() - step_start) * 1000,
            )
        )

        return response, []

    async def _generate_response(
        self,
        query: str,
        context: str = "",
        system_prompt: str = "",
    ) -> str:
        """Generate LLM response."""
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)

        if context:
            prompt_parts.append(f"\nContext:\n{context}")

        prompt_parts.append(f"\nQuestion: {query}")
        prompt_parts.append("\nAnswer:")

        full_prompt = "\n".join(prompt_parts)

        try:
            response = await self._llm.generate(full_prompt)
            return response.text
        except Exception as e:
            logger.error("Generation failed: %s", e)
            return f"I encountered an error processing your request: {e}"

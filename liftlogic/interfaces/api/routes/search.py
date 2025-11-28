"""
Search Routes - Document search and RAG endpoints.

Authentication:
- Authenticated users: Gemini (user's quota, zero cost)
- Unauthenticated users: Ollama fallback (your server)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from liftlogic.interfaces.api.auth import get_current_user_optional, UserContext
from liftlogic.interfaces.api.deps import get_sqlite_repository, get_knowledge_graph
from liftlogic.adapters import get_llm_for_user, SQLiteRepository
from liftlogic.domains.knowledge import KnowledgeGraphStore

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request body."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=20, ge=1, le=100)
    manufacturer: str | None = None
    use_rag: bool = Field(default=False, description="Generate AI answer")


class SearchResultItem(BaseModel):
    """Single search result."""

    doc_id: int
    filename: str
    content: str
    manufacturer: str | None
    score: float


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    results: list[SearchResultItem]
    total: int
    answer: str | None = None
    llm_provider: str | None = None  # "gemini" or "ollama"


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    user: UserContext | None = Depends(get_current_user_optional),
    repo: SQLiteRepository = Depends(get_sqlite_repository),
):
    """
    Search documents with optional AI-powered answers.

    - **query**: Search query text
    - **limit**: Maximum results (1-100)
    - **manufacturer**: Filter by manufacturer
    - **use_rag**: Generate AI-powered answer from results

    Auth:
    - With Google login: Uses Gemini (your quota, zero cost)
    - Without login: Uses Ollama (server-side)
    """
    # Perform FTS5 search
    search_results = await repo.search_fts(
        query=request.query,
        limit=request.limit,
        manufacturer=request.manufacturer,
    )

    # Convert to response format
    results = [
        SearchResultItem(
            doc_id=row["id"],
            filename=row["filename"],
            content=(row.get("content") or "")[:500],  # Truncate for response
            manufacturer=row.get("manufacturer"),
            score=abs(row.get("score", 0)),  # BM25 scores are negative
        )
        for row in search_results
    ]

    answer = None
    llm_provider = None

    if request.use_rag and results:
        # Get LLM based on user auth
        llm = await get_llm_for_user(user)
        llm_provider = llm.provider

        # Build context from search results
        context = "\n\n".join([
            f"[{r.filename}]: {r.content}"
            for r in results[:5]  # Use top 5 results as context
        ])

        response = await llm.generate(
            f"Based on the following elevator documentation, answer this query: {request.query}\n\nDocumentation:\n{context}",
            system_instruction="You are an elevator technician assistant. Provide practical, accurate answers based on the documentation provided. If the documentation doesn't contain the answer, say so.",
        )
        answer = response.text

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        answer=answer,
        llm_provider=llm_provider,
    )


@router.get("/fault/{code}")
async def get_fault_code(
    code: str,
    manufacturer: str | None = None,
    user: UserContext | None = Depends(get_current_user_optional),
    repo: SQLiteRepository = Depends(get_sqlite_repository),
    graph: KnowledgeGraphStore = Depends(get_knowledge_graph),
):
    """
    Look up a specific fault code with AI explanation.

    - **code**: Fault code (e.g., "505", "E-01")
    - **manufacturer**: Optional manufacturer filter

    Auth:
    - With Google login: Uses Gemini (your quota, zero cost)
    - Without login: Uses Ollama (server-side)
    """
    # Look up in SQLite fault codes table
    fault_results = await repo.get_fault_code(code, manufacturer)

    # Look up in knowledge graph
    fault_node = await graph.find_fault_by_code(code)
    resolution_procedures = []
    test_procedures = []

    if fault_node:
        resolution_procedures = await graph.get_fault_resolution(fault_node.id)
        test_procedures = await graph.get_fault_tests(fault_node.id)

    # Build context from database and graph
    context_parts = []

    if fault_results:
        for fr in fault_results:
            context_parts.append(
                f"Fault {fr.get('code')}: {fr.get('description', 'No description')}"
            )

    if fault_node:
        props = fault_node.properties
        context_parts.append(
            f"Name: {props.get('name', fault_node.name)}\n"
            f"Description: {props.get('description', 'N/A')}\n"
            f"Reason: {props.get('reason', 'N/A')}\n"
            f"Operation: {props.get('operation', 'N/A')}"
        )

    if resolution_procedures:
        context_parts.append(
            "Recovery procedures:\n" +
            "\n".join(f"- {p.properties.get('text', p.name)}" for p in resolution_procedures)
        )

    if test_procedures:
        context_parts.append(
            "Testing procedures:\n" +
            "\n".join(f"- {p.properties.get('text', p.name)}" for p in test_procedures)
        )

    # Get LLM for AI explanation
    llm = await get_llm_for_user(user)

    # Generate explanation with context
    context = "\n\n".join(context_parts) if context_parts else "No specific documentation found."

    response = await llm.generate(
        f"Based on this documentation, explain elevator fault code {code}" +
        (f" for {manufacturer}" if manufacturer else "") +
        f":\n\n{context}",
        system_instruction="You are an elevator technician assistant. Provide a practical explanation of the fault code, its causes, and recommended actions. Be concise.",
    )

    return {
        "code": code,
        "manufacturer": manufacturer,
        "explanation": response.text,
        "llm_provider": llm.provider,
        "db_results": fault_results,
        "graph_data": {
            "name": fault_node.properties.get("name") if fault_node else None,
            "description": fault_node.properties.get("description") if fault_node else None,
            "resolution_procedures": [
                p.properties.get("text", p.name) for p in resolution_procedures
            ],
            "test_procedures": [
                p.properties.get("text", p.name) for p in test_procedures
            ],
        } if fault_node else None,
    }

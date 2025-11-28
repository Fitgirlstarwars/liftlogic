"""
Diagnosis Routes - Fault diagnosis and expert analysis endpoints.

Authentication:
- Authenticated users: Gemini (user's quota, zero cost)
- Unauthenticated users: Ollama fallback (your server)
"""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from liftlogic.adapters import SQLiteRepository, get_llm_for_user
from liftlogic.domains.knowledge import KnowledgeGraphStore
from liftlogic.interfaces.api.auth import UserContext, get_current_user_optional
from liftlogic.interfaces.api.deps import get_knowledge_graph, get_sqlite_repository

router = APIRouter()


class DiagnosisMode(str, Enum):
    """Diagnosis analysis mode."""

    QUICK = "quick"
    DETAILED = "detailed"
    SAFETY = "safety"
    MAINTENANCE = "maintenance"
    STRATEGIC = "strategic"


class DiagnosisRequest(BaseModel):
    """Diagnosis request body."""

    fault_code: str = Field(..., description="Fault code to diagnose")
    manufacturer: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    mode: DiagnosisMode = DiagnosisMode.DETAILED


class DiagnosisResponse(BaseModel):
    """Diagnosis response."""

    fault_code: str
    description: str
    severity: str
    causes: list[str]
    remedies: list[str]
    related_components: list[str]
    confidence: float


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose_fault(
    request: DiagnosisRequest,
    user: UserContext | None = Depends(get_current_user_optional),
    repo: SQLiteRepository = Depends(get_sqlite_repository),
    graph: KnowledgeGraphStore = Depends(get_knowledge_graph),
):
    """
    Diagnose a fault code.

    Provides:
    - Fault description
    - Possible causes
    - Recommended remedies
    - Related components

    Auth:
    - With Google login: Uses Gemini (your quota, zero cost)
    - Without login: Uses Ollama (server-side)
    """
    # Look up fault in knowledge graph
    fault_node = await graph.find_fault_by_code(request.fault_code)

    # Get related data from graph
    resolution_procedures = []
    test_procedures = []
    related_nodes = []

    if fault_node:
        resolution_procedures = await graph.get_fault_resolution(fault_node.id)
        test_procedures = await graph.get_fault_tests(fault_node.id)
        # Get all neighbors (related components/procedures)
        related_nodes = await graph.get_neighbors(fault_node.id)

    # Look up in SQLite
    await repo.get_fault_code(
        request.fault_code,
        request.manufacturer,
    )

    # Build context for LLM
    context_parts = []

    if fault_node:
        props = fault_node.properties
        context_parts.append(
            f"Fault Code: {props.get('code', fault_node.name)}\n"
            f"Name: {props.get('name', '')}\n"
            f"Description: {props.get('description', '')}\n"
            f"Reason: {props.get('reason', '')}\n"
            f"Detection: {props.get('detection', '')}\n"
            f"Operation: {props.get('operation', '')}"
        )

    if resolution_procedures:
        context_parts.append(
            "Recovery Procedures:\n"
            + "\n".join(f"- {p.properties.get('text', p.name)}" for p in resolution_procedures)
        )

    if test_procedures:
        context_parts.append(
            "Testing Procedures:\n"
            + "\n".join(f"- {p.properties.get('text', p.name)}" for p in test_procedures)
        )

    if request.symptoms:
        context_parts.append("Reported Symptoms:\n" + "\n".join(f"- {s}" for s in request.symptoms))

    # Get LLM for diagnosis
    llm = await get_llm_for_user(user)

    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No documentation found for this fault code."
    )

    # Generate diagnosis based on mode
    if request.mode == DiagnosisMode.QUICK:
        prompt = f"Briefly explain fault code {request.fault_code}. Context:\n{context}"
        system_instruction = (
            "You are an elevator technician. Provide a brief explanation in 2-3 sentences."
        )
    elif request.mode == DiagnosisMode.SAFETY:
        prompt = f"Analyze the safety implications of fault code {request.fault_code}. Context:\n{context}"
        system_instruction = "You are an elevator safety expert. Focus on safety risks, hazards, and critical precautions."
    else:  # DETAILED
        prompt = f"""Diagnose elevator fault code {request.fault_code}.
Context:
{context}

Provide:
1. Description of the fault
2. Likely causes (list)
3. Recommended remedies (list)
4. Related components that may be affected
5. Severity assessment (critical/high/medium/low)"""
        system_instruction = "You are an expert elevator technician. Provide a comprehensive diagnosis based on the documentation."

    response = await llm.generate(prompt, system_instruction)

    # Extract structured data from fault node if available
    description = (
        fault_node.properties.get("description", response.text[:200])
        if fault_node
        else response.text[:200]
    )
    causes = (
        [fault_node.properties.get("reason", "")]
        if fault_node and fault_node.properties.get("reason")
        else []
    )
    remedies = (
        [p.properties.get("text", p.name) for p in resolution_procedures]
        if resolution_procedures
        else []
    )
    related_components = [n.name for n in related_nodes if n.type.value != "procedure"][:5]

    # Determine severity from operation field
    severity = "medium"
    if fault_node:
        operation = fault_node.properties.get("operation", "").lower()
        if "immediately" in operation or "lock" in operation:
            severity = "critical"
        elif "prevent" in operation or "inhibit" in operation:
            severity = "high"
        elif "warning" in operation or "alarm" in operation:
            severity = "low"

    return DiagnosisResponse(
        fault_code=request.fault_code,
        description=description,
        severity=severity,
        causes=causes if causes else ["See AI analysis for detailed causes"],
        remedies=remedies if remedies else ["See AI analysis for recommended actions"],
        related_components=related_components,
        confidence=0.9 if fault_node else 0.5,
    )


@router.post("/analyze/safety")
async def safety_analysis(
    document_id: int,
    user: UserContext | None = Depends(get_current_user_optional),
    repo: SQLiteRepository = Depends(get_sqlite_repository),
):
    """
    Perform safety audit on a document.

    Returns critical safety risks and recommendations.

    Auth:
    - With Google login: Uses Gemini (your quota, zero cost)
    - Without login: Uses Ollama (server-side)
    """
    # Get document from database
    doc = await repo.get_document(document_id)

    if not doc:
        return {
            "document_id": document_id,
            "error": "Document not found",
            "critical_risks": [],
            "recommendations": [],
        }

    # Get LLM for analysis
    llm = await get_llm_for_user(user)

    # Analyze document for safety concerns
    content = (doc.get("content") or "")[:10000]  # Limit context size

    response = await llm.generate(
        f"""Analyze this elevator documentation for safety concerns:

Document: {doc.get("filename", "Unknown")}
Manufacturer: {doc.get("manufacturer", "Unknown")}

Content:
{content}

Identify:
1. Critical safety risks (list with severity)
2. Safety recommendations
3. Compliance concerns""",
        system_instruction="You are an elevator safety auditor. Focus on OSHA compliance, EN 81 standards, and critical safety hazards. Be thorough but concise.",
    )

    return {
        "document_id": document_id,
        "filename": doc.get("filename"),
        "manufacturer": doc.get("manufacturer"),
        "analysis": response.text,
        "llm_provider": llm.provider,
        "critical_risks": [],  # Would be parsed from LLM response in production
        "recommendations": [],
    }


@router.post("/analyze/maintenance")
async def maintenance_analysis(
    document_id: int,
    user: UserContext | None = Depends(get_current_user_optional),
    repo: SQLiteRepository = Depends(get_sqlite_repository),
):
    """
    Generate maintenance schedule from a document.

    Returns recommended maintenance intervals and tasks.

    Auth:
    - With Google login: Uses Gemini (your quota, zero cost)
    - Without login: Uses Ollama (server-side)
    """
    # Get document from database
    doc = await repo.get_document(document_id)

    if not doc:
        return {
            "document_id": document_id,
            "error": "Document not found",
            "schedule": {"monthly": [], "quarterly": [], "annually": []},
        }

    # Get LLM for analysis
    llm = await get_llm_for_user(user)

    # Analyze document for maintenance requirements
    content = (doc.get("content") or "")[:10000]

    response = await llm.generate(
        f"""Extract maintenance schedule from this elevator documentation:

Document: {doc.get("filename", "Unknown")}
Manufacturer: {doc.get("manufacturer", "Unknown")}

Content:
{content}

Provide:
1. Monthly maintenance tasks
2. Quarterly maintenance tasks
3. Annual maintenance tasks
4. Critical inspections required""",
        system_instruction="You are an elevator maintenance planner. Extract specific maintenance tasks with their intervals. Be practical and actionable.",
    )

    return {
        "document_id": document_id,
        "filename": doc.get("filename"),
        "manufacturer": doc.get("manufacturer"),
        "analysis": response.text,
        "llm_provider": llm.provider,
        "schedule": {
            "monthly": [],  # Would be parsed from LLM response in production
            "quarterly": [],
            "annually": [],
        },
    }

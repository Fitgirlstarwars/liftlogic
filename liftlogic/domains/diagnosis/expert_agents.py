"""
Expert Agents - Specialized LLM agents for diagnosis tasks.

Implements fault diagnosis, safety analysis, and maintenance planning
using structured prompts and knowledge graph context.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from .models import (
    FaultDiagnosis,
    SafetyRisk,
    MaintenanceTask,
    DiagnosisMode,
    Severity,
    ExpertOpinion,
    ConsensusResult,
)

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient
    from liftlogic.domains.knowledge import KnowledgeGraphStore, GraphReasoner

logger = logging.getLogger(__name__)

__all__ = [
    "FaultDiagnosisAgent",
    "SafetyAnalysisAgent",
    "MaintenanceAgent",
    "ExpertConsensus",
]


class FaultDiagnosisAgent:
    """
    Expert agent for fault code diagnosis.

    Uses LLM with knowledge graph context to diagnose faults
    and recommend remedies.
    """

    def __init__(
        self,
        llm_client: GeminiClient,
        graph_store: KnowledgeGraphStore | None = None,
        reasoner: GraphReasoner | None = None,
    ) -> None:
        self._llm = llm_client
        self._graph = graph_store
        self._reasoner = reasoner

    async def diagnose(
        self,
        fault_code: str,
        symptoms: list[str] | None = None,
        context: dict | None = None,
        mode: DiagnosisMode = DiagnosisMode.DETAILED,
    ) -> FaultDiagnosis:
        """Diagnose a fault code with context."""
        context = context or {}
        symptoms = symptoms or []

        # Gather knowledge graph context if available
        graph_context = ""
        if self._reasoner:
            try:
                chain = await self._reasoner.find_causes(fault_code, max_depth=3)
                if chain.paths:
                    graph_context = f"\nKnowledge Graph Analysis:\n{chain.explanation}"
            except Exception as e:
                logger.warning("Failed to get graph context: %s", e)

        # Build prompt based on mode
        prompt = self._build_diagnosis_prompt(
            fault_code=fault_code,
            symptoms=symptoms,
            context=context,
            mode=mode,
            graph_context=graph_context,
        )

        # Get diagnosis from LLM
        try:
            response = await self._llm.generate_json(
                prompt=prompt,
                response_schema=self._get_diagnosis_schema(),
            )
            return self._parse_diagnosis_response(fault_code, response)
        except Exception as e:
            logger.error("Diagnosis failed: %s", e)
            return FaultDiagnosis(
                fault_code=fault_code,
                description=f"Diagnosis failed: {e}",
                severity=Severity.INFO,
                confidence=0.0,
            )

    def _build_diagnosis_prompt(
        self,
        fault_code: str,
        symptoms: list[str],
        context: dict,
        mode: DiagnosisMode,
        graph_context: str,
    ) -> str:
        """Build diagnosis prompt based on mode."""
        manufacturer = context.get("manufacturer", "Unknown")
        model = context.get("model", "Unknown")

        base_prompt = f"""You are an expert elevator technician diagnosing fault code: {fault_code}

Manufacturer: {manufacturer}
Model: {model}
Reported Symptoms: {', '.join(symptoms) if symptoms else 'None specified'}
{graph_context}

Analyze this fault and provide:
1. Clear description of what this fault means
2. Severity assessment (critical/high/medium/low/info)
3. Most likely causes (ranked by probability)
4. Recommended remedies (step-by-step)
5. Related components to inspect
6. Parts that may need replacement
7. Estimated repair time"""

        if mode == DiagnosisMode.SAFETY:
            base_prompt += """

SAFETY FOCUS: Pay special attention to:
- Immediate safety risks
- Required safety precautions
- Lockout/tagout requirements
- Potential for injury or equipment damage"""

        elif mode == DiagnosisMode.QUICK:
            base_prompt += """

QUICK MODE: Provide concise, actionable diagnosis.
Focus on most likely cause and primary remedy."""

        return base_prompt

    def _get_diagnosis_schema(self) -> dict:
        """Get JSON schema for diagnosis response."""
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "info"],
                },
                "causes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "root_cause": {"type": "string"},
                "remedies": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "related_components": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "safety_implications": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "parts_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "estimated_time": {"type": "string"},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["description", "severity", "causes", "remedies"],
        }

    def _parse_diagnosis_response(
        self,
        fault_code: str,
        response: dict,
    ) -> FaultDiagnosis:
        """Parse LLM response into FaultDiagnosis."""
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }

        return FaultDiagnosis(
            fault_code=fault_code,
            description=response.get("description", ""),
            severity=severity_map.get(
                response.get("severity", "medium"), Severity.MEDIUM
            ),
            causes=response.get("causes", []),
            root_cause=response.get("root_cause"),
            remedies=response.get("remedies", []),
            related_components=response.get("related_components", []),
            safety_implications=response.get("safety_implications", []),
            parts_needed=response.get("parts_needed", []),
            estimated_time=response.get("estimated_time"),
            confidence=response.get("confidence", 0.7),
            reasoning_chain=response.get("reasoning"),
        )


class SafetyAnalysisAgent:
    """Expert agent for safety risk analysis."""

    def __init__(self, llm_client: GeminiClient) -> None:
        self._llm = llm_client

    async def analyze_risks(
        self,
        document_content: str,
        focus_areas: list[str] | None = None,
    ) -> list[SafetyRisk]:
        """Analyze document for safety risks."""
        focus_areas = focus_areas or []

        prompt = f"""Analyze this elevator technical document for safety risks:

{document_content[:8000]}  # Truncate for context window

Focus areas: {', '.join(focus_areas) if focus_areas else 'All safety aspects'}

Identify:
1. Critical safety risks requiring immediate attention
2. Potential hazards during maintenance
3. Electrical safety concerns
4. Mechanical safety concerns
5. Fire/smoke risks
6. Compliance gaps with safety standards

For each risk provide:
- Clear title and description
- Severity (critical/high/medium/low)
- Affected components
- Recommended mitigation
- Relevant safety standards"""

        try:
            response = await self._llm.generate_json(
                prompt=prompt,
                response_schema={
                    "type": "object",
                    "properties": {
                        "risks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "severity": {"type": "string"},
                                    "category": {"type": "string"},
                                    "affected_components": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "mitigation": {"type": "string"},
                                    "standards": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "immediate_action": {"type": "boolean"},
                                },
                            },
                        }
                    },
                },
            )

            return [
                SafetyRisk(
                    id=f"SR-{uuid.uuid4().hex[:8]}",
                    title=r.get("title", ""),
                    description=r.get("description", ""),
                    severity=Severity(r.get("severity", "medium")),
                    category=r.get("category", ""),
                    affected_components=r.get("affected_components", []),
                    mitigation=r.get("mitigation", ""),
                    standards_reference=r.get("standards", []),
                    immediate_action_required=r.get("immediate_action", False),
                )
                for r in response.get("risks", [])
            ]
        except Exception as e:
            logger.error("Safety analysis failed: %s", e)
            return []

    async def audit_compliance(
        self,
        document_content: str,
        standards: list[str] | None = None,
    ) -> dict:
        """Audit document for standards compliance."""
        standards = standards or ["EN81", "ASME A17.1", "ISO 8100"]

        prompt = f"""Audit this elevator document for compliance with safety standards:

{document_content[:8000]}

Standards to check: {', '.join(standards)}

Evaluate:
1. Documented safety procedures
2. Required maintenance intervals
3. Emergency procedures
4. Warning labels and signage
5. Component specifications

Provide compliance status for each standard."""

        try:
            response = await self._llm.generate_json(
                prompt=prompt,
                response_schema={
                    "type": "object",
                    "properties": {
                        "overall_compliance": {"type": "string"},
                        "standards_checked": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "standard": {"type": "string"},
                                    "compliant": {"type": "boolean"},
                                    "gaps": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "recommendations": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            )
            return response
        except Exception as e:
            logger.error("Compliance audit failed: %s", e)
            return {"error": str(e)}


class MaintenanceAgent:
    """Expert agent for maintenance planning."""

    def __init__(self, llm_client: GeminiClient) -> None:
        self._llm = llm_client

    async def generate_schedule(
        self,
        components: list[dict],
        usage_data: dict | None = None,
    ) -> list[MaintenanceTask]:
        """Generate maintenance schedule for components."""
        usage_data = usage_data or {}

        component_list = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('type', 'Unknown')}"
            for c in components[:50]  # Limit components
        )

        prompt = f"""Generate maintenance schedule for these elevator components:

{component_list}

Usage Data: {usage_data if usage_data else 'Standard usage assumed'}

For each component, recommend:
1. Maintenance interval (daily/weekly/monthly/quarterly/annually)
2. Specific maintenance tasks
3. Required tools and parts
4. Safety precautions
5. Priority (1-10, 1=highest)
6. Estimated duration"""

        try:
            response = await self._llm.generate_json(
                prompt=prompt,
                response_schema={
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "component": {"type": "string"},
                                    "interval": {"type": "string"},
                                    "priority": {"type": "integer"},
                                    "duration": {"type": "string"},
                                    "parts": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "tools": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "safety": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                        }
                    },
                },
            )

            return [
                MaintenanceTask(
                    id=f"MT-{uuid.uuid4().hex[:8]}",
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    component=t.get("component", ""),
                    interval=t.get("interval", "monthly"),
                    priority=t.get("priority", 5),
                    estimated_duration=t.get("duration"),
                    parts_needed=t.get("parts", []),
                    tools_needed=t.get("tools", []),
                    safety_precautions=t.get("safety", []),
                )
                for t in response.get("tasks", [])
            ]
        except Exception as e:
            logger.error("Schedule generation failed: %s", e)
            return []

    async def prioritize_tasks(
        self,
        tasks: list[MaintenanceTask],
        constraints: dict | None = None,
    ) -> list[MaintenanceTask]:
        """Prioritize maintenance tasks based on constraints."""
        constraints = constraints or {}

        # Sort by priority and interval urgency
        interval_weight = {
            "daily": 1,
            "weekly": 2,
            "monthly": 3,
            "quarterly": 4,
            "annually": 5,
        }

        def task_score(task: MaintenanceTask) -> float:
            priority_score = task.priority
            interval_score = interval_weight.get(task.interval, 3)
            return priority_score + interval_score * 0.5

        return sorted(tasks, key=task_score)


class ExpertConsensus:
    """
    Multi-expert consensus system.

    Runs multiple expert agents and synthesizes their opinions
    into a unified diagnosis with confidence scoring.
    """

    def __init__(
        self,
        agents: list[FaultDiagnosisAgent],
        llm_client: GeminiClient | None = None,
    ) -> None:
        self._agents = agents
        self._llm = llm_client

    async def get_consensus(
        self,
        fault_code: str,
        symptoms: list[str] | None = None,
        context: dict | None = None,
    ) -> ConsensusResult:
        """Get consensus diagnosis from multiple experts."""
        opinions: list[ExpertOpinion] = []

        # Gather opinions from all agents
        for i, agent in enumerate(self._agents):
            try:
                diagnosis = await agent.diagnose(
                    fault_code=fault_code,
                    symptoms=symptoms,
                    context=context,
                )
                opinions.append(
                    ExpertOpinion(
                        agent_name=f"Expert_{i+1}",
                        diagnosis=diagnosis,
                        confidence=diagnosis.confidence,
                        reasoning=diagnosis.reasoning_chain or "",
                    )
                )
            except Exception as e:
                logger.warning("Expert %d failed: %s", i, e)

        if not opinions:
            return ConsensusResult(
                final_diagnosis=FaultDiagnosis(
                    fault_code=fault_code,
                    description="No expert opinions available",
                    severity=Severity.INFO,
                    confidence=0.0,
                ),
                consensus_level=0.0,
            )

        # Synthesize consensus
        final_diagnosis = self._synthesize_diagnoses(opinions)
        consensus_level = self._calculate_consensus(opinions)
        disagreements = self._find_disagreements(opinions)

        return ConsensusResult(
            final_diagnosis=final_diagnosis,
            expert_opinions=opinions,
            consensus_level=consensus_level,
            disagreements=disagreements,
            combined_confidence=sum(o.confidence for o in opinions) / len(opinions),
        )

    def _synthesize_diagnoses(
        self,
        opinions: list[ExpertOpinion],
    ) -> FaultDiagnosis:
        """Synthesize multiple diagnoses into one."""
        if not opinions:
            return FaultDiagnosis(
                fault_code="",
                description="",
                severity=Severity.INFO,
            )

        # Use highest confidence diagnosis as base
        best_opinion = max(opinions, key=lambda o: o.confidence)
        if not best_opinion.diagnosis:
            return FaultDiagnosis(
                fault_code="",
                description="",
                severity=Severity.INFO,
            )

        # Merge causes and remedies from all opinions
        all_causes: list[str] = []
        all_remedies: list[str] = []
        all_components: list[str] = []

        for opinion in opinions:
            if opinion.diagnosis:
                all_causes.extend(opinion.diagnosis.causes)
                all_remedies.extend(opinion.diagnosis.remedies)
                all_components.extend(opinion.diagnosis.related_components)

        # Deduplicate while preserving order
        unique_causes = list(dict.fromkeys(all_causes))
        unique_remedies = list(dict.fromkeys(all_remedies))
        unique_components = list(dict.fromkeys(all_components))

        return FaultDiagnosis(
            fault_code=best_opinion.diagnosis.fault_code,
            description=best_opinion.diagnosis.description,
            severity=best_opinion.diagnosis.severity,
            causes=unique_causes[:10],
            root_cause=best_opinion.diagnosis.root_cause,
            remedies=unique_remedies[:10],
            related_components=unique_components[:10],
            safety_implications=best_opinion.diagnosis.safety_implications,
            parts_needed=best_opinion.diagnosis.parts_needed,
            estimated_time=best_opinion.diagnosis.estimated_time,
            confidence=sum(o.confidence for o in opinions) / len(opinions),
        )

    def _calculate_consensus(self, opinions: list[ExpertOpinion]) -> float:
        """Calculate agreement level between experts."""
        if len(opinions) < 2:
            return 1.0

        # Compare severity ratings
        severities = [
            o.diagnosis.severity for o in opinions if o.diagnosis
        ]
        if not severities:
            return 0.0

        severity_agreement = len(set(severities)) == 1

        # Compare root causes
        root_causes = [
            o.diagnosis.root_cause for o in opinions if o.diagnosis and o.diagnosis.root_cause
        ]
        root_cause_agreement = len(set(root_causes)) <= 1 if root_causes else True

        # Weighted consensus score
        score = 0.0
        if severity_agreement:
            score += 0.5
        if root_cause_agreement:
            score += 0.5

        return score

    def _find_disagreements(self, opinions: list[ExpertOpinion]) -> list[str]:
        """Find points of disagreement between experts."""
        disagreements: list[str] = []

        if len(opinions) < 2:
            return disagreements

        # Check severity disagreements
        severities = set(
            o.diagnosis.severity.value for o in opinions if o.diagnosis
        )
        if len(severities) > 1:
            disagreements.append(
                f"Severity assessment varies: {', '.join(severities)}"
            )

        # Check root cause disagreements
        root_causes = set(
            o.diagnosis.root_cause
            for o in opinions
            if o.diagnosis and o.diagnosis.root_cause
        )
        if len(root_causes) > 1:
            disagreements.append(
                f"Root cause differs: {', '.join(str(rc) for rc in root_causes)}"
            )

        return disagreements

"""
Diagnosis Models - Data types for diagnosis domain.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DiagnosisMode(str, Enum):
    """Diagnosis analysis mode."""

    QUICK = "quick"  # Fast, basic diagnosis
    DETAILED = "detailed"  # Comprehensive analysis
    SAFETY = "safety"  # Safety-focused analysis
    MAINTENANCE = "maintenance"  # Maintenance-focused
    STRATEGIC = "strategic"  # Long-term planning


class Severity(str, Enum):
    """Severity level for issues."""

    CRITICAL = "critical"  # Immediate safety risk
    HIGH = "high"  # Service affecting
    MEDIUM = "medium"  # Should be addressed soon
    LOW = "low"  # Minor issue
    INFO = "info"  # Informational only


class FaultDiagnosis(BaseModel):
    """Complete fault diagnosis result."""

    fault_code: str
    description: str
    severity: Severity
    causes: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    remedies: list[str] = Field(default_factory=list)
    related_components: list[str] = Field(default_factory=list)
    safety_implications: list[str] = Field(default_factory=list)
    parts_needed: list[str] = Field(default_factory=list)
    estimated_time: str | None = None
    confidence: float = 0.0
    sources: list[str] = Field(default_factory=list)
    reasoning_chain: str | None = None


class SafetyRisk(BaseModel):
    """Identified safety risk."""

    id: str = ""
    title: str
    description: str
    severity: Severity
    category: str = ""  # electrical, mechanical, fire, etc.
    affected_components: list[str] = Field(default_factory=list)
    mitigation: str = ""
    standards_reference: list[str] = Field(default_factory=list)
    immediate_action_required: bool = False


class MaintenanceTask(BaseModel):
    """Scheduled maintenance task."""

    id: str = ""
    title: str
    description: str
    component: str
    interval: str  # daily, weekly, monthly, quarterly, annually
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest
    estimated_duration: str | None = None
    parts_needed: list[str] = Field(default_factory=list)
    tools_needed: list[str] = Field(default_factory=list)
    safety_precautions: list[str] = Field(default_factory=list)
    last_performed: datetime | None = None
    next_due: datetime | None = None


class ExpertOpinion(BaseModel):
    """Single expert agent's opinion."""

    agent_name: str
    diagnosis: FaultDiagnosis | None = None
    confidence: float = 0.0
    reasoning: str = ""
    dissenting_points: list[str] = Field(default_factory=list)


class ConsensusResult(BaseModel):
    """Multi-expert consensus result."""

    final_diagnosis: FaultDiagnosis
    expert_opinions: list[ExpertOpinion] = Field(default_factory=list)
    consensus_level: float = 0.0  # 0-1 agreement level
    disagreements: list[str] = Field(default_factory=list)
    combined_confidence: float = 0.0

"""
Knowledge Models - Data types for knowledge domain.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    COMPONENT = "component"
    FAULT_CODE = "fault_code"
    SYMPTOM = "symptom"
    ACTION = "action"
    TOOL = "tool"
    PART = "part"
    DOCUMENT = "document"
    MANUFACTURER = "manufacturer"
    # Additional types from imported graph data
    ENTITY = "entity"  # Generic fault/code entity
    PROCEDURE = "procedure"  # Recovery/testing procedures


class EdgeType(str, Enum):
    """Types of edges in the knowledge graph."""

    CAUSED_BY = "CAUSED_BY"
    INDICATES = "INDICATES"
    REQUIRES = "REQUIRES"
    PART_OF = "PART_OF"
    CONNECTED_TO = "CONNECTED_TO"
    DOCUMENTED_IN = "DOCUMENTED_IN"
    MANUFACTURED_BY = "MANUFACTURED_BY"
    RESOLVES = "RESOLVES"
    # Additional types from imported graph data
    CONTAINS = "CONTAINS"  # Document contains fault
    HAS_SUBCODE = "HAS_SUBCODE"  # Fault category has subcode
    RESOLVED_BY = "RESOLVED_BY"  # Fault resolved by procedure
    TESTED_BY = "TESTED_BY"  # Fault tested by procedure


class KnowledgeNode(BaseModel):
    """Node in the knowledge graph."""

    id: str
    type: NodeType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_document: str | None = None
    confidence: float = 1.0

    def __hash__(self) -> int:
        return hash(self.id)


class KnowledgeEdge(BaseModel):
    """Edge in the knowledge graph."""

    source_id: str
    target_id: str
    type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0


class ReasoningPath(BaseModel):
    """A path through the knowledge graph."""

    nodes: list[KnowledgeNode]
    edges: list[KnowledgeEdge]
    total_weight: float = 0.0

    @property
    def length(self) -> int:
        """Path length (number of edges)."""
        return len(self.edges)

    def to_string(self) -> str:
        """Human-readable path representation."""
        if not self.nodes:
            return "Empty path"

        parts = []
        for i, node in enumerate(self.nodes):
            parts.append(f"[{node.name}]")
            if i < len(self.edges):
                edge = self.edges[i]
                parts.append(f" --{edge.type.value}--> ")

        return "".join(parts)


class CausalChain(BaseModel):
    """Causal chain from symptom to root cause."""

    symptom: str
    root_causes: list[str]
    paths: list[ReasoningPath]
    confidence: float = 0.0
    explanation: str = ""


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""

    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_type: dict[str, int] = Field(default_factory=dict)
    edges_by_type: dict[str, int] = Field(default_factory=dict)

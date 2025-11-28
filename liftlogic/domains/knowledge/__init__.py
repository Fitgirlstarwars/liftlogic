"""
Knowledge Domain - Graph-based knowledge management and reasoning.

This domain handles:
- Knowledge graph construction
- Multi-hop reasoning
- Causal chain analysis
- Component relationship mapping
"""

from .contracts import GraphStore, Reasoner
from .models import (
    KnowledgeNode,
    KnowledgeEdge,
    ReasoningPath,
    CausalChain,
)
from .graph_store import KnowledgeGraphStore
from .reasoner import GraphReasoner

__all__ = [
    # Contracts
    "GraphStore",
    "Reasoner",
    # Models
    "KnowledgeNode",
    "KnowledgeEdge",
    "ReasoningPath",
    "CausalChain",
    # Implementations
    "KnowledgeGraphStore",
    "GraphReasoner",
]

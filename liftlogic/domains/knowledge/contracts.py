"""
Knowledge Contracts - Interfaces for knowledge domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import CausalChain, KnowledgeEdge, KnowledgeNode, ReasoningPath


@runtime_checkable
class GraphStore(Protocol):
    """Contract for knowledge graph storage."""

    async def add_node(self, node: KnowledgeNode) -> str:
        """Add a node to the graph."""
        ...

    async def add_edge(self, edge: KnowledgeEdge) -> str:
        """Add an edge to the graph."""
        ...

    async def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID."""
        ...

    async def get_neighbors(
        self,
        node_id: str,
        edge_type: str | None = None,
        direction: str = "both",
    ) -> list[KnowledgeNode]:
        """Get neighboring nodes."""
        ...

    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
    ) -> ReasoningPath | None:
        """Find shortest path between nodes."""
        ...


@runtime_checkable
class Reasoner(Protocol):
    """Contract for graph-based reasoning."""

    async def find_causes(
        self,
        symptom_or_fault: str,
        max_depth: int = 3,
    ) -> CausalChain:
        """Find root causes for a symptom or fault."""
        ...

    async def find_effects(
        self,
        component_or_action: str,
        max_depth: int = 3,
    ) -> list[str]:
        """Find effects of a component failure or action."""
        ...

    async def explain_connection(
        self,
        start: str,
        end: str,
    ) -> str:
        """Generate natural language explanation of connection."""
        ...

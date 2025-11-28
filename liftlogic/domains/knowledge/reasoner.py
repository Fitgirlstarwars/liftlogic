"""
Graph Reasoner - Multi-hop reasoning over knowledge graphs.

Provides causal chain analysis and natural language explanations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import (
    KnowledgeNode,
    KnowledgeEdge,
    ReasoningPath,
    CausalChain,
    NodeType,
    EdgeType,
)

if TYPE_CHECKING:
    from .graph_store import KnowledgeGraphStore
    from liftlogic.adapters.gemini import GeminiClient

logger = logging.getLogger(__name__)

__all__ = ["GraphReasoner"]


class GraphReasoner:
    """
    Graph-based reasoner for causal analysis.

    Uses multi-hop traversal to find root causes and effects,
    with optional LLM-powered explanations.

    Example:
        >>> reasoner = GraphReasoner(graph_store, gemini_client)
        >>> chain = await reasoner.find_causes("F505", max_depth=3)
        >>> print(chain.explanation)
    """

    def __init__(
        self,
        graph_store: KnowledgeGraphStore,
        llm_client: GeminiClient | None = None,
    ) -> None:
        """
        Initialize reasoner.

        Args:
            graph_store: Knowledge graph store
            llm_client: Optional Gemini client for explanations
        """
        self._graph = graph_store
        self._llm = llm_client

    async def find_causes(
        self,
        symptom_or_fault: str,
        max_depth: int = 3,
    ) -> CausalChain:
        """
        Find root causes for a symptom or fault code.

        Traverses CAUSED_BY and INDICATES edges backwards to find
        the originating components or conditions.

        Args:
            symptom_or_fault: Symptom description or fault code ID
            max_depth: Maximum traversal depth

        Returns:
            CausalChain with paths to root causes
        """
        # Find starting node
        start_node = await self._graph.get_node(symptom_or_fault)
        if not start_node:
            # Try to find by name match
            start_node = await self._find_node_by_name(symptom_or_fault)

        if not start_node:
            return CausalChain(
                symptom=symptom_or_fault,
                root_causes=[],
                paths=[],
                confidence=0.0,
                explanation=f"No matching node found for: {symptom_or_fault}",
            )

        # Traverse backwards through causal edges
        root_causes: list[str] = []
        paths: list[ReasoningPath] = []
        visited: set[str] = set()

        await self._traverse_causes(
            node_id=start_node.id,
            current_path=[start_node],
            current_edges=[],
            depth=0,
            max_depth=max_depth,
            visited=visited,
            root_causes=root_causes,
            paths=paths,
        )

        # Calculate confidence based on path quality
        confidence = self._calculate_confidence(paths)

        # Generate explanation if LLM available
        explanation = ""
        if self._llm and paths:
            explanation = await self._generate_explanation(
                symptom_or_fault, root_causes, paths
            )

        return CausalChain(
            symptom=symptom_or_fault,
            root_causes=root_causes,
            paths=paths,
            confidence=confidence,
            explanation=explanation,
        )

    async def _traverse_causes(
        self,
        node_id: str,
        current_path: list[KnowledgeNode],
        current_edges: list[KnowledgeEdge],
        depth: int,
        max_depth: int,
        visited: set[str],
        root_causes: list[str],
        paths: list[ReasoningPath],
    ) -> None:
        """Recursively traverse causal edges."""
        if depth >= max_depth or node_id in visited:
            return

        visited.add(node_id)

        # Get incoming causal edges
        neighbors = await self._graph.get_neighbors(
            node_id,
            direction="in",
        )

        # Filter for causal relationships
        causal_neighbors = []
        for neighbor in neighbors:
            # Check if edge is causal
            edge_data = self._graph._graph.get_edge_data(neighbor.id, node_id)
            if edge_data:
                edge_type = edge_data.get("type", "")
                if edge_type in (EdgeType.CAUSED_BY.value, EdgeType.INDICATES.value):
                    causal_neighbors.append((neighbor, edge_type))

        if not causal_neighbors:
            # This is a root cause (no incoming causal edges)
            node = await self._graph.get_node(node_id)
            if node and node.type == NodeType.COMPONENT:
                root_causes.append(node.name)
                if len(current_path) > 1:
                    paths.append(
                        ReasoningPath(
                            nodes=list(current_path),
                            edges=list(current_edges),
                            total_weight=sum(e.weight for e in current_edges),
                        )
                    )
            return

        # Continue traversal
        for neighbor, edge_type in causal_neighbors:
            edge = KnowledgeEdge(
                source_id=neighbor.id,
                target_id=node_id,
                type=EdgeType(edge_type),
            )
            await self._traverse_causes(
                node_id=neighbor.id,
                current_path=current_path + [neighbor],
                current_edges=current_edges + [edge],
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited.copy(),  # Allow revisiting in different paths
                root_causes=root_causes,
                paths=paths,
            )

    async def find_effects(
        self,
        component_or_action: str,
        max_depth: int = 3,
    ) -> list[str]:
        """
        Find effects of a component failure or action.

        Traverses CAUSED_BY edges forward to find resulting
        symptoms, faults, or cascading failures.

        Args:
            component_or_action: Component ID or action name
            max_depth: Maximum traversal depth

        Returns:
            List of effect descriptions
        """
        start_node = await self._graph.get_node(component_or_action)
        if not start_node:
            start_node = await self._find_node_by_name(component_or_action)

        if not start_node:
            return []

        effects: list[str] = []
        visited: set[str] = set()

        await self._traverse_effects(
            node_id=start_node.id,
            depth=0,
            max_depth=max_depth,
            visited=visited,
            effects=effects,
        )

        return effects

    async def _traverse_effects(
        self,
        node_id: str,
        depth: int,
        max_depth: int,
        visited: set[str],
        effects: list[str],
    ) -> None:
        """Recursively traverse effect edges."""
        if depth >= max_depth or node_id in visited:
            return

        visited.add(node_id)

        # Get outgoing edges (effects)
        neighbors = await self._graph.get_neighbors(
            node_id,
            direction="out",
        )

        for neighbor in neighbors:
            # Check edge type
            edge_data = self._graph._graph.get_edge_data(node_id, neighbor.id)
            if edge_data:
                edge_type = edge_data.get("type", "")
                if edge_type in (EdgeType.CAUSED_BY.value, EdgeType.INDICATES.value):
                    # This neighbor is an effect
                    if neighbor.type in (NodeType.FAULT_CODE, NodeType.SYMPTOM):
                        effects.append(neighbor.name)

                    # Continue traversal
                    await self._traverse_effects(
                        node_id=neighbor.id,
                        depth=depth + 1,
                        max_depth=max_depth,
                        visited=visited,
                        effects=effects,
                    )

    async def explain_connection(
        self,
        start: str,
        end: str,
    ) -> str:
        """
        Generate natural language explanation of connection.

        Args:
            start: Start node ID or name
            end: End node ID or name

        Returns:
            Human-readable explanation of the connection
        """
        # Find nodes
        start_node = await self._graph.get_node(start)
        if not start_node:
            start_node = await self._find_node_by_name(start)

        end_node = await self._graph.get_node(end)
        if not end_node:
            end_node = await self._find_node_by_name(end)

        if not start_node or not end_node:
            return f"Could not find connection between '{start}' and '{end}'"

        # Find path
        path = await self._graph.find_path(start_node.id, end_node.id)
        if not path:
            # Try reverse direction
            path = await self._graph.find_path(end_node.id, start_node.id)

        if not path:
            return f"No connection found between '{start_node.name}' and '{end_node.name}'"

        # Generate explanation
        if self._llm:
            return await self._generate_path_explanation(path)

        # Fallback to template-based explanation
        return self._template_explanation(path)

    async def _find_node_by_name(self, name: str) -> KnowledgeNode | None:
        """Find node by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for node in self._graph._nodes.values():
            if name_lower in node.name.lower():
                return node
        return None

    def _calculate_confidence(self, paths: list[ReasoningPath]) -> float:
        """Calculate confidence score based on path quality."""
        if not paths:
            return 0.0

        # Factors: number of paths, path lengths, edge weights
        num_paths = len(paths)
        avg_length = sum(p.length for p in paths) / num_paths
        avg_weight = sum(p.total_weight for p in paths) / num_paths if paths else 0

        # Shorter paths and more paths = higher confidence
        length_factor = 1.0 / (1.0 + avg_length * 0.2)
        path_factor = min(1.0, num_paths * 0.3)

        confidence = (length_factor + path_factor) / 2
        return min(1.0, max(0.0, confidence))

    async def _generate_explanation(
        self,
        symptom: str,
        root_causes: list[str],
        paths: list[ReasoningPath],
    ) -> str:
        """Generate LLM explanation for causal chain."""
        if not self._llm:
            return ""

        # Build path descriptions
        path_descriptions = []
        for i, path in enumerate(paths[:3], 1):  # Limit to 3 paths
            path_descriptions.append(f"{i}. {path.to_string()}")

        prompt = f"""Explain the causal relationship in this elevator fault diagnosis:

Symptom/Fault: {symptom}
Root Causes Found: {', '.join(root_causes) if root_causes else 'None identified'}

Reasoning Paths:
{chr(10).join(path_descriptions) if path_descriptions else 'No paths found'}

Provide a clear, technician-friendly explanation of:
1. Why these components might cause this symptom
2. The most likely root cause
3. What to check first

Keep it concise (2-3 paragraphs)."""

        try:
            response = await self._llm.generate(prompt)
            return response.text
        except Exception as e:
            logger.warning("Failed to generate LLM explanation: %s", e)
            return self._template_causal_explanation(symptom, root_causes)

    async def _generate_path_explanation(self, path: ReasoningPath) -> str:
        """Generate LLM explanation for a specific path."""
        if not self._llm:
            return self._template_explanation(path)

        prompt = f"""Explain this connection path in an elevator system:

Path: {path.to_string()}

Provide a brief, technician-friendly explanation of how these components
are related and what this connection means for troubleshooting."""

        try:
            response = await self._llm.generate(prompt)
            return response.text
        except Exception as e:
            logger.warning("Failed to generate path explanation: %s", e)
            return self._template_explanation(path)

    def _template_explanation(self, path: ReasoningPath) -> str:
        """Generate template-based explanation for a path."""
        if not path.nodes:
            return "Empty path"

        parts = [f"Starting from {path.nodes[0].name}"]

        for i, edge in enumerate(path.edges):
            target = path.nodes[i + 1] if i + 1 < len(path.nodes) else None
            if target:
                relation = edge.type.value.lower().replace("_", " ")
                parts.append(f"which is {relation} {target.name}")

        return ", ".join(parts) + "."

    def _template_causal_explanation(
        self,
        symptom: str,
        root_causes: list[str],
    ) -> str:
        """Generate template-based causal explanation."""
        if not root_causes:
            return f"No root causes identified for {symptom}."

        if len(root_causes) == 1:
            return f"The symptom '{symptom}' is likely caused by {root_causes[0]}."

        causes_text = ", ".join(root_causes[:-1]) + f" or {root_causes[-1]}"
        return f"The symptom '{symptom}' may be caused by {causes_text}."

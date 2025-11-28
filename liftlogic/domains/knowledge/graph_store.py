"""
Knowledge Graph Store - Graph storage with NetworkX and Neo4j backends.

Supports both in-memory (NetworkX) and persistent (Neo4j) storage.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import networkx as nx

from .models import (
    EdgeType,
    GraphStats,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
    ReasoningPath,
)

if TYPE_CHECKING:
    from liftlogic.adapters.neo4j import Neo4jClient

logger = logging.getLogger(__name__)

__all__ = ["KnowledgeGraphStore"]


class KnowledgeGraphStore:
    """
    Knowledge graph store with dual backend support.

    Uses NetworkX for in-memory operations and optionally syncs to Neo4j.

    Example:
        >>> store = KnowledgeGraphStore()
        >>> await store.add_node(KnowledgeNode(id="K1", type=NodeType.COMPONENT, name="Relay K1"))
        >>> await store.add_edge(KnowledgeEdge(source_id="K1", target_id="F505", type=EdgeType.CAUSED_BY))
    """

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """
        Initialize graph store.

        Args:
            neo4j_client: Optional Neo4j client for persistence
        """
        self._graph = nx.DiGraph()
        self._neo4j = neo4j_client
        self._nodes: dict[str, KnowledgeNode] = {}

    async def add_node(self, node: KnowledgeNode) -> str:
        """Add a node to the graph."""
        # Filter out conflicting properties (name is already set)
        props = {k: v for k, v in node.properties.items() if k not in ("name", "type")}
        self._graph.add_node(
            node.id,
            node_type=node.type.value,
            node_name=node.name,
            **props,
        )
        self._nodes[node.id] = node

        # Sync to Neo4j if available
        if self._neo4j:
            await self._neo4j.create_node(
                label=node.type.value.capitalize(),
                properties={
                    "id": node.id,
                    "name": node.name,
                    **node.properties,
                },
            )

        logger.debug("Added node: %s (%s)", node.id, node.type.value)
        return node.id

    async def add_edge(self, edge: KnowledgeEdge) -> str:
        """Add an edge to the graph."""
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            type=edge.type.value,
            weight=edge.weight,
            **edge.properties,
        )

        # Sync to Neo4j if available
        if self._neo4j:
            # Get node types for Neo4j labels
            source_node = self._nodes.get(edge.source_id)
            target_node = self._nodes.get(edge.target_id)

            if source_node and target_node:
                await self._neo4j.create_relationship(
                    from_id=edge.source_id,
                    from_label=source_node.type.value.capitalize(),
                    to_id=edge.target_id,
                    to_label=target_node.type.value.capitalize(),
                    relationship_type=edge.type.value,
                    properties=edge.properties,
                )

        logger.debug(
            "Added edge: %s -[%s]-> %s",
            edge.source_id,
            edge.type.value,
            edge.target_id,
        )
        return f"{edge.source_id}->{edge.target_id}"

    async def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    async def get_neighbors(
        self,
        node_id: str,
        edge_type: str | None = None,
        direction: str = "both",
    ) -> list[KnowledgeNode]:
        """
        Get neighboring nodes.

        Args:
            node_id: Source node ID
            edge_type: Filter by edge type
            direction: "in", "out", or "both"

        Returns:
            List of neighboring nodes
        """
        neighbors = []

        if direction in ("out", "both"):
            for _, target, data in self._graph.out_edges(node_id, data=True):
                if edge_type is None or data.get("type") == edge_type:
                    node = self._nodes.get(target)
                    if node:
                        neighbors.append(node)

        if direction in ("in", "both"):
            for source, _, data in self._graph.in_edges(node_id, data=True):
                if edge_type is None or data.get("type") == edge_type:
                    node = self._nodes.get(source)
                    if node:
                        neighbors.append(node)

        return neighbors

    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
    ) -> ReasoningPath | None:
        """Find shortest path between two nodes."""
        try:
            path_ids = nx.shortest_path(
                self._graph,
                source=start_id,
                target=end_id,
            )

            if len(path_ids) > max_depth + 1:
                return None

            # Build path with nodes and edges
            nodes = []
            edges = []

            for i, node_id in enumerate(path_ids):
                node = self._nodes.get(node_id)
                if node:
                    nodes.append(node)

                if i < len(path_ids) - 1:
                    edge_data = self._graph.get_edge_data(node_id, path_ids[i + 1])
                    if edge_data:
                        edges.append(
                            KnowledgeEdge(
                                source_id=node_id,
                                target_id=path_ids[i + 1],
                                type=EdgeType(edge_data.get("type", "CONNECTED_TO")),
                                weight=edge_data.get("weight", 1.0),
                            )
                        )

            return ReasoningPath(
                nodes=nodes,
                edges=edges,
                total_weight=sum(e.weight for e in edges),
            )

        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    async def find_all_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
    ) -> list[ReasoningPath]:
        """Find all paths between two nodes up to max depth."""
        paths = []

        try:
            for path_ids in nx.all_simple_paths(
                self._graph,
                source=start_id,
                target=end_id,
                cutoff=max_depth,
            ):
                nodes = [self._nodes[nid] for nid in path_ids if nid in self._nodes]
                edges = []

                for i in range(len(path_ids) - 1):
                    edge_data = self._graph.get_edge_data(path_ids[i], path_ids[i + 1])
                    if edge_data:
                        edges.append(
                            KnowledgeEdge(
                                source_id=path_ids[i],
                                target_id=path_ids[i + 1],
                                type=EdgeType(edge_data.get("type", "CONNECTED_TO")),
                            )
                        )

                if nodes:
                    paths.append(ReasoningPath(nodes=nodes, edges=edges))

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return paths

    async def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        nodes_by_type: dict[str, int] = {}
        edges_by_type: dict[str, int] = {}

        for node in self._nodes.values():
            type_name = node.type.value
            nodes_by_type[type_name] = nodes_by_type.get(type_name, 0) + 1

        for _, _, data in self._graph.edges(data=True):
            type_name = data.get("type", "unknown")
            edges_by_type[type_name] = edges_by_type.get(type_name, 0) + 1

        return GraphStats(
            total_nodes=len(self._nodes),
            total_edges=self._graph.number_of_edges(),
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
        )

    async def build_from_extraction(
        self,
        components: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        fault_codes: list[dict[str, Any]],
        document_id: str,
    ) -> None:
        """
        Build graph from extraction results.

        Args:
            components: List of extracted components
            connections: List of extracted connections
            fault_codes: List of extracted fault codes
            document_id: Source document ID
        """
        # Add document node
        await self.add_node(
            KnowledgeNode(
                id=document_id,
                type=NodeType.DOCUMENT,
                name=document_id,
            )
        )

        # Add components
        for comp in components:
            node = KnowledgeNode(
                id=comp.get("id", ""),
                type=NodeType.COMPONENT,
                name=comp.get("name", ""),
                properties=comp.get("specs", {}),
                source_document=document_id,
            )
            await self.add_node(node)

            # Link to document
            await self.add_edge(
                KnowledgeEdge(
                    source_id=node.id,
                    target_id=document_id,
                    type=EdgeType.DOCUMENTED_IN,
                )
            )

        # Add connections
        for conn in connections:
            await self.add_edge(
                KnowledgeEdge(
                    source_id=conn.get("source_id", ""),
                    target_id=conn.get("target_id", ""),
                    type=EdgeType.CONNECTED_TO,
                    properties={"label": conn.get("label")},
                )
            )

        # Add fault codes
        for fault in fault_codes:
            fault_id = f"FAULT_{fault.get('code', '')}"
            await self.add_node(
                KnowledgeNode(
                    id=fault_id,
                    type=NodeType.FAULT_CODE,
                    name=fault.get("code", ""),
                    properties={
                        "description": fault.get("description", ""),
                        "severity": fault.get("severity"),
                    },
                    source_document=document_id,
                )
            )

            # Link fault to related components
            for comp_id in fault.get("related_components", []):
                await self.add_edge(
                    KnowledgeEdge(
                        source_id=fault_id,
                        target_id=comp_id,
                        type=EdgeType.CAUSED_BY,
                    )
                )

        logger.info(
            "Built graph from extraction: %d components, %d connections, %d faults",
            len(components),
            len(connections),
            len(fault_codes),
        )

    async def load_from_json(self, graph_dir: str | Path) -> tuple[int, int]:
        """
        Load graph data from JSON files.

        Args:
            graph_dir: Directory containing nodes.json and edges.json

        Returns:
            Tuple of (node_count, edge_count)
        """
        graph_dir = Path(graph_dir)
        nodes_file = graph_dir / "nodes.json"
        edges_file = graph_dir / "edges.json"

        node_count = 0
        edge_count = 0

        # Load nodes
        if nodes_file.exists():
            with open(nodes_file) as f:
                nodes_data = json.load(f)

            for node_data in nodes_data:
                # Map type from graph data to NodeType
                node_type_str = node_data.get("type", "entity")
                try:
                    node_type = NodeType(node_type_str)
                except ValueError:
                    node_type = NodeType.ENTITY  # Default fallback

                properties = node_data.get("properties", {})
                name = (
                    properties.get("name")
                    or properties.get("code")
                    or properties.get("title")
                    or node_data.get("label", "")
                )

                node = KnowledgeNode(
                    id=node_data["id"],
                    type=node_type,
                    name=name,
                    properties=properties,
                )
                await self.add_node(node)
                node_count += 1

        # Load edges
        if edges_file.exists():
            with open(edges_file) as f:
                edges_data = json.load(f)

            for edge_data in edges_data:
                edge_type_str = edge_data.get("type", "CONNECTED_TO")
                try:
                    edge_type = EdgeType(edge_type_str)
                except ValueError:
                    edge_type = EdgeType.CONNECTED_TO  # Default fallback

                edge = KnowledgeEdge(
                    source_id=edge_data["source"],
                    target_id=edge_data["target"],
                    type=edge_type,
                    weight=edge_data.get("weight", 1.0),
                    properties=edge_data.get("properties", {}),
                )
                await self.add_edge(edge)
                edge_count += 1

        logger.info("Loaded graph from JSON: %d nodes, %d edges", node_count, edge_count)
        return node_count, edge_count

    async def find_fault_by_code(self, code: str) -> KnowledgeNode | None:
        """
        Find a fault node by its code.

        Args:
            code: Fault code to search for

        Returns:
            KnowledgeNode if found, None otherwise
        """
        for node in self._nodes.values():
            if node.type in (NodeType.FAULT_CODE, NodeType.ENTITY):
                node_code = node.properties.get("code") or node.name
                if node_code == code:
                    return node
        return None

    async def get_fault_resolution(self, fault_node_id: str) -> list[KnowledgeNode]:
        """
        Get resolution procedures for a fault.

        Args:
            fault_node_id: ID of the fault node

        Returns:
            List of procedure nodes that resolve the fault
        """
        return await self.get_neighbors(
            fault_node_id,
            edge_type=EdgeType.RESOLVED_BY.value,
            direction="out",
        )

    async def get_fault_tests(self, fault_node_id: str) -> list[KnowledgeNode]:
        """
        Get test procedures for a fault.

        Args:
            fault_node_id: ID of the fault node

        Returns:
            List of procedure nodes for testing the fault
        """
        return await self.get_neighbors(
            fault_node_id,
            edge_type=EdgeType.TESTED_BY.value,
            direction="out",
        )

"""Tests for Knowledge Graph Store."""

import json
from pathlib import Path

import pytest

from .graph_store import KnowledgeGraphStore
from .models import EdgeType, KnowledgeEdge, KnowledgeNode, NodeType


@pytest.fixture
def graph():
    """Create a fresh knowledge graph store."""
    return KnowledgeGraphStore()


async def test_add_and_get_node(graph: KnowledgeGraphStore):
    """Test adding and retrieving a node."""
    node = KnowledgeNode(
        id="comp_1",
        type=NodeType.COMPONENT,
        name="Door Controller",
        properties={"voltage": "24V", "manufacturer": "KONE"},
    )

    node_id = await graph.add_node(node)
    assert node_id == "comp_1"

    retrieved = await graph.get_node("comp_1")
    assert retrieved is not None
    assert retrieved.name == "Door Controller"
    assert retrieved.properties["voltage"] == "24V"


async def test_add_edge(graph: KnowledgeGraphStore):
    """Test adding an edge between nodes."""
    # Add nodes first
    await graph.add_node(
        KnowledgeNode(
            id="fault_505",
            type=NodeType.FAULT_CODE,
            name="F505",
        )
    )
    await graph.add_node(
        KnowledgeNode(
            id="comp_sensor",
            type=NodeType.COMPONENT,
            name="Door Sensor",
        )
    )

    # Add edge
    edge = KnowledgeEdge(
        source_id="fault_505",
        target_id="comp_sensor",
        type=EdgeType.CAUSED_BY,
        weight=0.9,
    )
    edge_id = await graph.add_edge(edge)

    assert edge_id == "fault_505->comp_sensor"


async def test_get_neighbors(graph: KnowledgeGraphStore):
    """Test getting neighboring nodes."""
    # Create a small graph: fault -> component -> document
    await graph.add_node(KnowledgeNode(id="fault", type=NodeType.FAULT_CODE, name="F505"))
    await graph.add_node(KnowledgeNode(id="comp", type=NodeType.COMPONENT, name="Sensor"))
    await graph.add_node(KnowledgeNode(id="doc", type=NodeType.DOCUMENT, name="Manual"))

    await graph.add_edge(
        KnowledgeEdge(source_id="fault", target_id="comp", type=EdgeType.CAUSED_BY)
    )
    await graph.add_edge(
        KnowledgeEdge(source_id="comp", target_id="doc", type=EdgeType.DOCUMENTED_IN)
    )

    # Get outgoing neighbors
    neighbors = await graph.get_neighbors("fault", direction="out")
    assert len(neighbors) == 1
    assert neighbors[0].id == "comp"

    # Get neighbors with edge type filter
    neighbors = await graph.get_neighbors("fault", edge_type="CAUSED_BY", direction="out")
    assert len(neighbors) == 1


async def test_find_path(graph: KnowledgeGraphStore):
    """Test finding path between nodes."""
    # Create chain: A -> B -> C
    await graph.add_node(KnowledgeNode(id="a", type=NodeType.COMPONENT, name="A"))
    await graph.add_node(KnowledgeNode(id="b", type=NodeType.COMPONENT, name="B"))
    await graph.add_node(KnowledgeNode(id="c", type=NodeType.COMPONENT, name="C"))

    await graph.add_edge(KnowledgeEdge(source_id="a", target_id="b", type=EdgeType.CONNECTED_TO))
    await graph.add_edge(KnowledgeEdge(source_id="b", target_id="c", type=EdgeType.CONNECTED_TO))

    path = await graph.find_path("a", "c")
    assert path is not None
    assert len(path.nodes) == 3
    assert path.nodes[0].id == "a"
    assert path.nodes[2].id == "c"


async def test_find_path_no_path(graph: KnowledgeGraphStore):
    """Test finding path when none exists."""
    await graph.add_node(KnowledgeNode(id="isolated", type=NodeType.COMPONENT, name="Isolated"))
    await graph.add_node(KnowledgeNode(id="other", type=NodeType.COMPONENT, name="Other"))

    path = await graph.find_path("isolated", "other")
    assert path is None


async def test_get_stats(graph: KnowledgeGraphStore):
    """Test getting graph statistics."""
    await graph.add_node(KnowledgeNode(id="c1", type=NodeType.COMPONENT, name="C1"))
    await graph.add_node(KnowledgeNode(id="c2", type=NodeType.COMPONENT, name="C2"))
    await graph.add_node(KnowledgeNode(id="f1", type=NodeType.FAULT_CODE, name="F1"))

    await graph.add_edge(KnowledgeEdge(source_id="f1", target_id="c1", type=EdgeType.CAUSED_BY))

    stats = await graph.get_stats()
    assert stats.total_nodes == 3
    assert stats.total_edges == 1
    assert stats.nodes_by_type["component"] == 2
    assert stats.nodes_by_type["fault_code"] == 1


async def test_find_fault_by_code(graph: KnowledgeGraphStore):
    """Test finding fault node by code."""
    await graph.add_node(
        KnowledgeNode(
            id="fault_2001",
            type=NodeType.ENTITY,
            name="Peak value over limit",
            properties={"code": "2001", "description": "Overcurrent"},
        )
    )

    fault = await graph.find_fault_by_code("2001")
    assert fault is not None
    assert fault.name == "Peak value over limit"
    assert fault.properties["description"] == "Overcurrent"


async def test_load_from_json(graph: KnowledgeGraphStore, tmp_path: Path):
    """Test loading graph from JSON files."""
    # Create test JSON files
    nodes = [
        {
            "entity": "node",
            "id": "n1",
            "type": "entity",
            "label": "Fault",
            "properties": {"code": "100", "name": "Test Fault"},
        },
        {
            "entity": "node",
            "id": "n2",
            "type": "procedure",
            "label": "Procedure",
            "properties": {"text": "Reset the system"},
        },
    ]
    edges = [
        {
            "entity": "edge",
            "source": "n1",
            "target": "n2",
            "type": "RESOLVED_BY",
            "weight": 1.0,
            "properties": {},
        },
    ]

    nodes_file = tmp_path / "nodes.json"
    edges_file = tmp_path / "edges.json"

    with open(nodes_file, "w") as f:
        json.dump(nodes, f)
    with open(edges_file, "w") as f:
        json.dump(edges, f)

    # Load and verify
    node_count, edge_count = await graph.load_from_json(tmp_path)

    assert node_count == 2
    assert edge_count == 1

    # Verify nodes loaded correctly
    node = await graph.get_node("n1")
    assert node is not None
    assert node.properties["code"] == "100"


async def test_get_fault_resolution(graph: KnowledgeGraphStore):
    """Test getting resolution procedures for a fault."""
    # Create fault and procedure nodes
    await graph.add_node(
        KnowledgeNode(
            id="fault",
            type=NodeType.ENTITY,
            name="F100",
            properties={"code": "100"},
        )
    )
    await graph.add_node(
        KnowledgeNode(
            id="proc1",
            type=NodeType.PROCEDURE,
            name="Reset",
            properties={"text": "Power cycle the system"},
        )
    )

    # Add resolution edge
    await graph.add_edge(
        KnowledgeEdge(
            source_id="fault",
            target_id="proc1",
            type=EdgeType.RESOLVED_BY,
        )
    )

    # Get resolutions
    resolutions = await graph.get_fault_resolution("fault")
    assert len(resolutions) == 1
    assert resolutions[0].properties["text"] == "Power cycle the system"

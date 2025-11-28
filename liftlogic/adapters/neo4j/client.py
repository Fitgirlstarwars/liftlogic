"""
Neo4j Client - Graph database operations.

Features:
- Async-compatible operations
- Connection pooling
- Cypher query execution
- Graph traversal helpers
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)

__all__ = ["Neo4jClient"]


class Neo4jClient:
    """
    Neo4j graph database client.

    Example:
        >>> client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        >>> await client.connect()
        >>> result = await client.run_query("MATCH (n) RETURN n LIMIT 10")
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
    ) -> None:
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
            database: Database name
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        self._driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )
        # Verify connectivity
        await self._driver.verify_connectivity()
        logger.info("Connected to Neo4j: %s", self.uri)

    async def close(self) -> None:
        """Close connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def run_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dicts
        """
        if not self._driver:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def create_node(
        self,
        label: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a node.

        Args:
            label: Node label (e.g., "Component", "FaultCode")
            properties: Node properties

        Returns:
            Created node data
        """
        query = f"""
            CREATE (n:{label} $props)
            RETURN n
        """
        result = await self.run_query(query, {"props": properties})
        return result[0]["n"] if result else {}

    async def create_relationship(
        self,
        from_id: str,
        from_label: str,
        to_id: str,
        to_label: str,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a relationship between nodes.

        Args:
            from_id: Source node ID property
            from_label: Source node label
            to_id: Target node ID property
            to_label: Target node label
            relationship_type: Relationship type (e.g., "CAUSED_BY")
            properties: Relationship properties

        Returns:
            Created relationship data
        """
        query = f"""
            MATCH (a:{from_label} {{id: $from_id}})
            MATCH (b:{to_label} {{id: $to_id}})
            CREATE (a)-[r:{relationship_type} $props]->(b)
            RETURN r
        """
        result = await self.run_query(
            query,
            {
                "from_id": from_id,
                "to_id": to_id,
                "props": properties or {},
            },
        )
        return result[0]["r"] if result else {}

    async def find_path(
        self,
        start_id: str,
        start_label: str,
        end_id: str,
        end_label: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find shortest path between nodes.

        Args:
            start_id: Start node ID
            start_label: Start node label
            end_id: End node ID
            end_label: End node label
            max_depth: Maximum path depth

        Returns:
            List of nodes in path
        """
        query = f"""
            MATCH path = shortestPath(
                (start:{start_label} {{id: $start_id}})-[*..{max_depth}]-
                (end:{end_label} {{id: $end_id}})
            )
            RETURN nodes(path) as nodes, relationships(path) as rels
        """
        result = await self.run_query(
            query,
            {
                "start_id": start_id,
                "end_id": end_id,
            },
        )
        return result

    async def get_related_nodes(
        self,
        node_id: str,
        node_label: str,
        relationship_type: str | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get nodes related to a given node.

        Args:
            node_id: Source node ID
            node_label: Source node label
            relationship_type: Filter by relationship type
            direction: "in", "out", or "both"
            limit: Maximum results

        Returns:
            List of related nodes
        """
        rel_pattern = f":{relationship_type}" if relationship_type else ""

        if direction == "out":
            pattern = f"-[r{rel_pattern}]->"
        elif direction == "in":
            pattern = f"<-[r{rel_pattern}]-"
        else:
            pattern = f"-[r{rel_pattern}]-"

        query = f"""
            MATCH (n:{node_label} {{id: $node_id}}){pattern}(related)
            RETURN related, type(r) as rel_type
            LIMIT $limit
        """
        return await self.run_query(query, {"node_id": node_id, "limit": limit})

    async def initialize_schema(self) -> None:
        """Create indexes and constraints for the knowledge graph."""
        queries = [
            # Constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:FaultCode) REQUIRE f.code IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            # Indexes
            "CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (f:FaultCode) ON (f.manufacturer)",
            "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.manufacturer)",
        ]

        for query in queries:
            try:
                await self.run_query(query)
            except Exception as e:
                logger.warning("Schema query failed (may already exist): %s", e)

        logger.info("Neo4j schema initialized")

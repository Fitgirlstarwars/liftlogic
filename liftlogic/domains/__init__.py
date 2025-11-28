"""
Domains - Business logic layer.

Each domain is self-contained with:
- contracts.py: Interfaces (Protocol classes)
- models.py: Pydantic data models
- Implementation files
- tests/ directory
"""

__all__ = [
    "extraction",
    "search",
    "knowledge",
    "diagnosis",
    "orchestration",
]

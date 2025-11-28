"""
CLI Interface - Command-line tools for LiftLogic.

Provides commands for:
- Document extraction
- Search queries
- Fault diagnosis
- System management
"""

from .main import app, main

__all__ = ["app", "main"]

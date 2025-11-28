"""
API Interface - FastAPI REST API.

This is the unified API that replaces:
- tech-portal Flask API
- liftlogic-portal FastAPI
- liftcode-decoder Express API
"""

from .main import app, create_app

__all__ = ["app", "create_app"]

"""
Health Routes - System health and status endpoints.
"""

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "liftlogic"}


@router.get("/api")
async def api_info() -> dict[str, Any]:
    """API info endpoint."""
    return {
        "name": "LiftLogic API",
        "version": "2.0.0",
        "description": "AI-native elevator/lift documentation intelligence",
        "docs": "/docs",
    }

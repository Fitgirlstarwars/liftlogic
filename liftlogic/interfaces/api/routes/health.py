"""
Health Routes - System health and status endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "liftlogic"}


@router.get("/api")
async def api_info():
    """API info endpoint."""
    return {
        "name": "LiftLogic API",
        "version": "2.0.0",
        "description": "AI-native elevator/lift documentation intelligence",
        "docs": "/docs",
    }

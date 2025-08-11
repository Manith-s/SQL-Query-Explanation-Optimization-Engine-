"""
Health check router.

Provides basic health and status endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Simple status response
    """
    return {"status": "ok"}

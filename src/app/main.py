"""
FastAPI application entry point.

Mounts routers and provides minimal health route.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, lint, explain, optimize

app = FastAPI(
    title="SQL Query Explanation & Optimization Engine",
    description="A local, offline-capable tool for SQL analysis, explanation, and optimization",
    version="0.1.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health.router, tags=["health"])
app.include_router(lint.router, prefix="/api/v1", tags=["lint"])
app.include_router(explain.router, prefix="/api/v1", tags=["explain"])
app.include_router(optimize.router, prefix="/api/v1", tags=["optimize"])


@app.get("/")
async def root():
    """Root endpoint with basic project info."""
    return {
        "name": "SQL Query Explanation & Optimization Engine",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


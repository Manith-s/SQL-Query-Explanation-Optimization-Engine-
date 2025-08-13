"""
FastAPI application entry point.

Mounts routers and provides minimal health route.
"""

from fastapi import FastAPI, Request, Response
import time
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, lint, explain, optimize, schema
from app.core.metrics import init_metrics, observe_request, metrics_exposition

app = FastAPI(
    title="SQL Query Explanation & Optimization Engine",
    description="A local, offline-capable tool for SQL analysis, explanation, and optimization",
    version="0.7.0",
)

# CORS middleware for development
from app.core.config import settings

allow_origins = (settings.__dict__.get("CORS_ALLOW_ORIGINS") or "*").split(",") if hasattr(settings, "CORS_ALLOW_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    rid = request.headers.get("x-request-id", str(int(start * 1000000)))
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        try:
            route_tmpl = request.scope.get("route").path  # type: ignore[attr-defined]
        except Exception:
            route_tmpl = request.url.path
        try:
            observe_request(route_tmpl, request.method, response.status_code, duration_ms / 1000.0)
        except Exception:
            pass
        print(
            {
                "lvl": "info",
                "rid": rid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "dur_ms": duration_ms,
            }
        )
        return response
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        print(
            {
                "lvl": "error",
                "rid": rid,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "dur_ms": duration_ms,
            }
        )
        raise

# Initialize metrics once on startup
init_metrics()


@app.get("/metrics")
async def metrics():
    if not settings.METRICS_ENABLED:
        return Response(status_code=404)
    data, content_type = metrics_exposition()
    return Response(content=data, media_type=content_type)

# Mount routers
app.include_router(health.router, tags=["health"])
app.include_router(lint.router, prefix="/api/v1", tags=["lint"])
app.include_router(explain.router, prefix="/api/v1", tags=["explain"])
app.include_router(optimize.router, prefix="/api/v1", tags=["optimize"])
app.include_router(schema.router, prefix="/api/v1", tags=["schema"])


@app.get("/")
async def root():
    """Root endpoint with basic project info."""
    return {
        "name": "SQL Query Explanation & Optimization Engine",
        "version": "0.7.0",
        "status": "running",
        "docs": "/docs"
    }


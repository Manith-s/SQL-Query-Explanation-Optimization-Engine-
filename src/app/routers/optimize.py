"""
SQL optimization router.

Provides deterministic rewrite and index suggestions for a given SQL query.
"""

from typing import List, Optional, Literal, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint

from app.core import db, sql_analyzer, plan_heuristics
from app.core.config import settings
from app.core.optimizer import analyze as optimizer_analyze
from app.core import whatif


router = APIRouter()


class OptimizeRequest(BaseModel):
    sql: str = Field(..., description="SQL to analyze")
    analyze: bool = Field(False, description="Use EXPLAIN ANALYZE if true")
    timeout_ms: conint(ge=1, le=600000) = Field(10000, description="Statement timeout (ms)")
    advisors: List[Literal["rewrite", "index"]] = Field(
        default_factory=lambda: ["rewrite", "index"], description="Which advisors to run"
    )
    top_k: conint(ge=1, le=50) = Field(10, description="Max suggestions to return")


class OptimizeResponse(BaseModel):
    ok: bool = True
    message: str = "ok"
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    ranking: Literal["cost_based", "heuristic"] = "heuristic"
    whatIf: Dict[str, Any] = Field(default_factory=dict)
    plan_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    plan_metrics: Dict[str, Any] = Field(default_factory=dict)
    advisorsRan: List[str] = Field(default_factory=list)
    dataSources: Dict[str, Any] = Field(default_factory=dict)
    actualTopK: int = 0


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Deterministic optimization suggestions (rewrites + index advisor)",
    description="Runs static analysis, optional EXPLAIN/ANALYZE, schema+stats fetch, plan heuristics, and returns deterministic suggestions.",
    responses={
        200: {
            "description": "Optimization suggestions",
            "content": {
                "application/json": {
                    "example": {
                        "ok": True,
                        "message": "ok",
                        "suggestions": [
                            {
                                "kind": "rewrite",
                                "title": "Align ORDER BY with index to support Top-N",
                                "rationale": "Matching order-by with an index enables early termination.",
                                "impact": "medium",
                                "confidence": 0.800,
                                "statements": [],
                                "alt_sql": "-- Ensure leading index columns match ORDER BY direction",
                                "safety_notes": None
                            }
                        ],
                        "summary": {"summary": "Top suggestion: Align ORDER BY with index to support Top-N", "score": 0.800},
                        "plan_warnings": [],
                        "plan_metrics": {"planning_time_ms": 0.0, "execution_time_ms": 0.0, "node_count": 1},
                        "advisorsRan": ["rewrite", "index"],
                        "dataSources": {"plan": "explain", "stats": True},
                        "actualTopK": 1
                    }
                }
            }
        }
    }
)
async def optimize_sql(request: OptimizeRequest) -> OptimizeResponse:
    try:
        # Apply defaults
        if request.timeout_ms is None:
            request.timeout_ms = settings.OPT_TIMEOUT_MS_DEFAULT

        # Parse SQL statically
        ast_info = sql_analyzer.parse_sql(request.sql)
        if ast_info.get("type") != "SELECT":
            return OptimizeResponse(
                ok=False,
                message="Only SELECT statements are supported for optimization",
            )

        # Identify tables involved
        tables = [t.get("name") for t in (ast_info.get("tables") or []) if t.get("name")]

        # Optionally run EXPLAIN
        plan = None
        plan_warnings: List[Dict[str, Any]] = []
        plan_metrics: Dict[str, Any] = {}
        plan_source = "none"
        try:
            plan = db.run_explain(request.sql, analyze=request.analyze, timeout_ms=request.timeout_ms)
            plan_warnings, plan_metrics = plan_heuristics.analyze(plan)
            plan_source = "explain_analyze" if request.analyze else "explain"
        except Exception:
            # Soft-fail: still continue with rewrites
            plan = None
            plan_source = "none"

        # Fetch schema and lightweight stats
        schema_info = db.fetch_schema()
        stats = {}
        stats_used = False
        try:
            stats = db.fetch_table_stats(tables)
            stats_used = True
        except Exception:
            stats = {}
            stats_used = False

        # Optimizer options (could be extended from config)
        options = {
            "min_index_rows": settings.OPT_MIN_ROWS_FOR_INDEX,
            "max_index_cols": settings.OPT_MAX_INDEX_COLS,
        }

        result = optimizer_analyze(
            sql=request.sql,
            ast_info=ast_info,
            plan=plan,
            schema=schema_info,
            stats=stats,
            options=options,
        )

        server_top_k = min(int(request.top_k or settings.OPT_TOP_K), settings.OPT_TOP_K)
        suggestions = result.get("suggestions", [])[: server_top_k]
        summary = result.get("summary", {})

        # Optional what-if (HypoPG) ranking/evaluation
        ranking = "heuristic"
        whatif_info: Dict[str, Any] = {"enabled": False, "available": False, "trials": 0, "filteredByPct": 0}
        if settings.WHATIF_ENABLED:
            try:
                wi = whatif.evaluate(request.sql, suggestions, timeout_ms=request.timeout_ms)
                ranking = wi.get("ranking", ranking)
                whatif_info = wi.get("whatIf", whatif_info)
                suggestions = wi.get("suggestions", suggestions)
            except Exception:
                # Graceful fallback
                ranking = "heuristic"
                whatif_info = {"enabled": True, "available": False, "trials": 0, "filteredByPct": 0}

        return OptimizeResponse(
            ok=True,
            message="stub: optimize ok",
            suggestions=suggestions,
            summary=summary,
            ranking=ranking,
            whatIf=whatif_info,
            plan_warnings=plan_warnings,
            plan_metrics=plan_metrics,
            advisorsRan=["rewrite", "index"],
            dataSources={"plan": plan_source, "stats": stats_used},
            actualTopK=len(suggestions),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

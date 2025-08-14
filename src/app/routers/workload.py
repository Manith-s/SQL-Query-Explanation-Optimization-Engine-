from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field, conint

from app.core.workload import analyze_workload


router = APIRouter()


class WorkloadRequest(BaseModel):
    sqls: List[str] = Field(..., description="List of SQL statements")
    top_k: conint(ge=1, le=50) = 10
    what_if: bool = False


class WorkloadResponse(BaseModel):
    ok: bool = True
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    perQuery: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/workload", response_model=WorkloadResponse)
async def workload(req: WorkloadRequest) -> WorkloadResponse:
    res = analyze_workload(req.sqls, top_k=int(req.top_k), what_if=bool(req.what_if))
    return WorkloadResponse(ok=True, suggestions=res.get("suggestions", []), perQuery=res.get("perQuery", []))



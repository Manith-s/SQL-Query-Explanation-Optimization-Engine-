from typing import List, Dict, Any
from app.core import sql_analyzer, db, plan_heuristics
from app.core.optimizer import analyze as analyze_one
from app.core.config import settings


def _merge_candidates(all_suggs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for s in all_suggs:
        if s.get("kind") != "index":
            continue
        key = s.get("title") or ""
        cur = seen.get(key)
        if not cur:
            cur = {**s, "frequency": 0}
            seen[key] = cur
        cur["frequency"] += 1
        # accumulate score if present
        cur["score"] = float(f"{(float(cur.get('score') or 0.0) + float(s.get('score') or 0.0)):.3f}")
    out = list(seen.values())
    out.sort(key=lambda x: (-float(x.get("score") or 0.0), -int(x.get("frequency") or 0), x.get("title") or ""))
    return out[: top_k]


def analyze_workload(sqls: List[str], top_k: int = 10, what_if: bool = False) -> Dict[str, Any]:
    all_suggs: List[Dict[str, Any]] = []
    per_query: List[Dict[str, Any]] = []
    for sql in sqls:
        info = sql_analyzer.parse_sql(sql)
        if info.get("type") != "SELECT":
            per_query.append({"sql": sql, "skipped": True})
            continue
        plan = None
        warnings: List[Dict[str, Any]] = []
        metrics: Dict[str, Any] = {}
        try:
            plan = db.run_explain(sql, analyze=False, timeout_ms=settings.OPT_TIMEOUT_MS_DEFAULT)
            warnings, metrics = plan_heuristics.analyze(plan)
        except Exception:
            plan = None
        schema_info = db.fetch_schema()
        try:
            tables = [t.get("name") for t in (info.get("tables") or []) if t.get("name")]
            stats = db.fetch_table_stats(tables, timeout_ms=settings.OPT_TIMEOUT_MS_DEFAULT)
        except Exception:
            stats = {}
        options = {
            "min_index_rows": settings.OPT_MIN_ROWS_FOR_INDEX,
            "max_index_cols": settings.OPT_MAX_INDEX_COLS,
        }
        res = analyze_one(sql, info, plan, schema_info, stats, options)
        suggs = res.get("suggestions", [])
        all_suggs.extend(suggs)
        per_query.append({"sql": sql, "suggestions": suggs})
    merged = _merge_candidates(all_suggs, top_k)
    return {"suggestions": merged, "perQuery": per_query}



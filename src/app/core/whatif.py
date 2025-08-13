"""Cost-based what-if evaluator using HypoPG (optional, read-only).

This module never executes DDL for real. It creates hypothetical indexes via HypoPG
only to measure planner cost deltas, and resets state after trials.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import time
import re

from app.core.config import settings
from app.core import db
from app.core.metrics import observe_whatif_trial, count_whatif_filtered


def _parse_index_stmt(stmt: str) -> Tuple[str, List[str]]:
    """Extract table and columns from a CREATE INDEX suggestion statement.

    Expected format created by optimizer: CREATE INDEX ... ON table (col1, col2)
    """
    m = re.search(r"\bON\s+([A-Za-z0-9_\.]+)\s*\(([^\)]+)\)", stmt, re.IGNORECASE)
    if not m:
        return "", []
    table = m.group(1)
    cols = [c.strip().strip('"') for c in m.group(2).split(",")]
    return table, cols


def _plan_total_cost(plan: Dict[str, Any]) -> float:
    try:
        return float(plan.get("Plan", {}).get("Total Cost", 0.0))
    except Exception:
        return 0.0


def _hypopg_available() -> bool:
    try:
        rows = db.run_sql("SELECT extname FROM pg_extension WHERE extname='hypopg'")
        return any(r and r[0] == 'hypopg' for r in rows)
    except Exception:
        return False


def evaluate(sql: str, suggestions: List[Dict[str, Any]], timeout_ms: int) -> Dict[str, Any]:
    """Evaluate top-N index suggestions via HypoPG and return cost deltas.

    Returns dict with:
      - ranking: "cost_based"|"heuristic"
      - whatIf: { enabled, available, trials, filteredByPct }
      - enriched suggestions (may include estCostBefore/After/Delta)
    """
    enabled = bool(settings.WHATIF_ENABLED)
    if not enabled:
        return {
            "ranking": "heuristic",
            "whatIf": {"enabled": False, "available": False, "trials": 0, "filteredByPct": 0},
            "suggestions": suggestions,
        }

    available = _hypopg_available()
    if not available:
        return {
            "ranking": "heuristic",
            "whatIf": {"enabled": True, "available": False, "trials": 0, "filteredByPct": 0},
            "suggestions": suggestions,
        }

    # Baseline cost
    baseline = db.run_explain_costs(sql, timeout_ms=timeout_ms)
    base_cost = _plan_total_cost(baseline)

    # Select top-N index suggestions to trial
    max_trials = int(settings.WHATIF_MAX_TRIALS)
    min_pct = float(settings.WHATIF_MIN_COST_REDUCTION_PCT)
    candidates = [s for s in suggestions if s.get("kind") == "index"][: max_trials]

    enriched: List[Dict[str, Any]] = []
    filtered = 0

    for s in suggestions:
        enriched.append(dict(s))

    if not candidates:
        return {
            "ranking": "heuristic",
            "whatIf": {"enabled": True, "available": True, "trials": 0, "filteredByPct": 0},
            "suggestions": enriched,
        }

    # Run each candidate in isolation; reset hypopg between trials
    trials = 0
    for cand in candidates:
        stmt_list = cand.get("statements") or []
        table, cols = ("", [])
        if stmt_list:
            table, cols = _parse_index_stmt(stmt_list[0])
        if not table or not cols:
            continue

        try:
            with db.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                    cur.execute("SELECT hypopg_reset()")
                    # create hypothetical index
                    cols_sql = ", ".join(cols)
                    cur.execute("SELECT * FROM hypopg_create_index(%s)", (f"CREATE INDEX ON {table} ({cols_sql})",))
                    start = time.time()
                    # run costed explain
                    plan = db.run_explain_costs(sql, timeout_ms=timeout_ms)
                    observe_whatif_trial(time.time() - start)
                    cur.execute("SELECT hypopg_reset()")
                    trials += 1
                    cost_after = _plan_total_cost(plan)
                    delta = base_cost - cost_after
        except Exception:
            # Ignore trial errors; leave suggestion untouched
            continue

        # Attach deltas to the matching enriched suggestion
        for e in enriched:
            if e.get("title") == cand.get("title") and e.get("kind") == "index":
                e["estCostBefore"] = float(f"{base_cost:.3f}")
                e["estCostAfter"] = float(f"{cost_after:.3f}")
                e["estCostDelta"] = float(f"{delta:.3f}")
                break

    # Filter by min reduction pct
    out: List[Dict[str, Any]] = []
    for e in enriched:
        d = float(e.get("estCostDelta") or 0.0)
        if d > 0 and base_cost > 0:
            pct = (d / base_cost) * 100.0
            if pct + 1e-9 < min_pct:
                filtered += 1
                continue
        out.append(e)

    count_whatif_filtered(filtered)

    # Ranking: sort primarily by cost delta desc, then keep prior deterministic tie-breakers
    def _rank_key(x: Dict[str, Any]):
        impact_rank = {"high": 3, "medium": 2, "low": 1}
        return (
            -float(x.get("estCostDelta") or 0.0),
            -impact_rank.get(x.get("impact"), 0),
            -float(x.get("confidence") or 0.0),
            str(x.get("title") or ""),
        )

    out.sort(key=_rank_key)

    return {
        "ranking": "cost_based",
        "whatIf": {"enabled": True, "available": True, "trials": trials, "filteredByPct": filtered},
        "suggestions": out,
    }




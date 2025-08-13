"""Command-line interface for Query Explain & Optimize.

Supports lint, explain, and optimize without running the API server.
Deterministic outputs; no DDL execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from app.core import sql_analyzer, plan_heuristics, db
from app.core import whatif


def _print(data: Dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    else:
        # Minimal text formatting
        for k, v in data.items():
            print(f"{k}: {v}")


def cmd_lint(args: argparse.Namespace) -> int:
    sql = _read_sql(args)
    info = sql_analyzer.parse_sql(sql)
    out = sql_analyzer.lint_rules(info)
    _print(out, args.format)
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    sql = _read_sql(args)
    try:
        plan = db.run_explain(sql, analyze=args.analyze, timeout_ms=args.timeout_ms)
        warnings, metrics = plan_heuristics.analyze(plan)
        out = {"plan": plan, "warnings": warnings, "metrics": metrics}
        _print(out, args.format)
        return 0
    except Exception as e:
        _print({"error": str(e)}, args.format)
        return 3


def cmd_optimize(args: argparse.Namespace) -> int:
    from app.core.optimizer import analyze as opt_analyze

    sql = _read_sql(args)
    info = sql_analyzer.parse_sql(sql)
    if info.get("type") != "SELECT":
        _print({"ok": False, "message": "Only SELECT supported"}, args.format)
        return 2

    plan = None
    warnings: list = []
    metrics: dict = {}
    try:
        plan = db.run_explain(sql, analyze=args.analyze, timeout_ms=args.timeout_ms)
        warnings, metrics = plan_heuristics.analyze(plan)
    except Exception:
        plan = None

    schema = db.fetch_schema()
    try:
        tables = [t.get("name") for t in (info.get("tables") or []) if t.get("name")]
        stats = db.fetch_table_stats(tables, timeout_ms=args.timeout_ms)
    except Exception:
        stats = {}

    options = {
        "min_index_rows": args.min_rows_for_index,
        "max_index_cols": args.max_index_cols,
    }
    result = opt_analyze(sql, info, plan, schema, stats, options)
    suggestions = result.get("suggestions", [])[: args.top_k]

    ranking = "heuristic"
    whatif_info = {"enabled": False, "available": False, "trials": 0, "filteredByPct": 0}
    if args.what_if:
        try:
            wi = whatif.evaluate(sql, suggestions, timeout_ms=args.timeout_ms)
            ranking = wi.get("ranking", ranking)
            whatif_info = wi.get("whatIf", whatif_info)
            suggestions = wi.get("suggestions", suggestions)
        except Exception:
            ranking = "heuristic"
            whatif_info = {"enabled": True, "available": False, "trials": 0, "filteredByPct": 0}

    out = {
        "ok": True,
        "message": "ok",
        "suggestions": suggestions,
        "summary": result.get("summary", {}),
        "plan_warnings": warnings,
        "plan_metrics": metrics,
        "ranking": ranking,
        "whatIf": whatif_info,
    }
    _print(out, args.format)
    return 0


def _read_sql(args: argparse.Namespace) -> str:
    if args.sql:
        return args.sql
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    data = sys.stdin.read()
    if not data.strip():
        raise SystemExit(2)
    return data


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qeo", description="Query Explain & Optimize CLI")
    p.add_argument("--format", choices=["json", "text"], default="json")
    p.add_argument("--timeout-ms", type=int, default=10000)

    sp = p.add_subparsers(dest="cmd", required=True)

    lint = sp.add_parser("lint", help="Lint SQL")
    lint.add_argument("--sql")
    lint.add_argument("--file")
    lint.set_defaults(func=cmd_lint)

    ex = sp.add_parser("explain", help="Explain SQL plan")
    ex.add_argument("--sql")
    ex.add_argument("--file")
    ex.add_argument("--analyze", action="store_true")
    ex.set_defaults(func=cmd_explain)

    opt = sp.add_parser("optimize", help="Optimize SQL")
    opt.add_argument("--sql")
    opt.add_argument("--file")
    opt.add_argument("--analyze", action="store_true")
    opt.add_argument("--top-k", type=int, default=10)
    opt.add_argument("--min-rows-for-index", type=int, default=10000)
    opt.add_argument("--max-index-cols", type=int, default=3)
    opt.add_argument("--what-if", dest="what_if", action="store_true", help="Enable HypoPG cost-based what-if evaluation")
    opt.add_argument("--no-what-if", dest="what_if", action="store_false")
    opt.set_defaults(what_if=False)
    opt.set_defaults(func=cmd_optimize)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
        sys.exit(code)
    except SystemExit as e:
        raise e
    except Exception as e:
        _print({"error": str(e)}, getattr(args, "format", "json"))
        sys.exit(3)



"""
Database utilities for PostgreSQL connection management and EXPLAIN analysis.

This module provides safe connection handling, EXPLAIN helpers, and schema inspection
utilities for the Query Explain & Optimize engine.
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import psycopg2
from psycopg2.extensions import connection as pg_connection
from psycopg2.extras import RealDictCursor

from app.core.config import settings

@contextmanager
def get_conn() -> pg_connection:
    """
    Get a PostgreSQL connection with proper error handling and automatic closing.
    Uses connection parameters from settings.DB_URL.
    """
    conn = None
    try:
        conn = psycopg2.connect(settings.db_url_psycopg)
        yield conn
    finally:
        if conn is not None:
        conn.close()

def run_sql(sql: str, params: Optional[Tuple] = None, timeout_ms: int = 10000) -> List[Tuple]:
    """
    Execute SQL with proper connection handling and timeout.
    
    Args:
        sql: SQL query to execute
        params: Query parameters (optional)
        timeout_ms: Statement timeout in milliseconds
    
    Returns:
        List of result tuples
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            cur.execute(sql, params)
            return cur.fetchall()

def run_explain(sql: str, analyze: bool = False, timeout_ms: int = 10000) -> Dict:
    """
    Run EXPLAIN on a query and return the execution plan.
    
    Args:
        sql: SQL query to explain
        analyze: If True, use EXPLAIN ANALYZE
        timeout_ms: Statement timeout in milliseconds
    
    Returns:
        Normalized plan dictionary
    """
    explain_options = ["FORMAT JSON"]
    if analyze:
        explain_options.extend(["ANALYZE", "BUFFERS", "TIMING"])
    
    explain_sql = f"EXPLAIN ({', '.join(explain_options)}) {sql}"
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                # Set statement timeout
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                
                # Run EXPLAIN
                cur.execute(explain_sql)
                result = cur.fetchone()
                
                # Handle both text and native JSON formats
                if isinstance(result[0], str):
                    plan_json = json.loads(result[0])
                else:
                    plan_json = result[0]
                
                # Normalize plan shape: EXPLAIN returns a list with one item
                plan_obj = plan_json[0] if isinstance(plan_json, list) and plan_json else plan_json
                # Ensure plan_obj is a dict with top-level Plan
                if isinstance(plan_obj, dict) and "Plan" in plan_obj:
                    return plan_obj
                if isinstance(plan_obj, dict):
                    return {"Plan": plan_obj}
                # Fallback
                return {"Plan": {}}
            
            except Exception as e:
                raise Exception(f"EXPLAIN failed: {str(e)}")

def run_explain_costs(sql: str, timeout_ms: int = 10000) -> Dict:
    """
    Run EXPLAIN with costs enabled (no analyze, no timing) and return plan JSON.
    """
    explain_sql = f"EXPLAIN (FORMAT JSON, COSTS ON, TIMING OFF) {sql}"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            cur.execute(explain_sql)
            result = cur.fetchone()
            if isinstance(result[0], str):
                plan_json = json.loads(result[0])
            else:
                plan_json = result[0]
            plan_obj = plan_json[0] if isinstance(plan_json, list) and plan_json else plan_json
            if isinstance(plan_obj, dict) and "Plan" in plan_obj:
                return plan_obj
            if isinstance(plan_obj, dict):
                return {"Plan": plan_obj}
            return {"Plan": {}}

def fetch_schema(schema: str = "public", table: Optional[str] = None) -> Dict:
    """
    Fetch database schema information using information_schema views.
    
    Args:
        schema: Schema name to inspect
        table: Optional table name to filter results
    
    Returns:
        Dictionary containing tables, columns, indexes, and constraints
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Base table query
            table_where = f"AND table_name = %s" if table else ""
            table_params = (schema, table) if table else (schema,)
            
            # Get tables
            cur.execute(f"""
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_schema = %s
                {table_where}
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, table_params)
            tables = cur.fetchall()
            
            result = {
                "schema": schema,
                "tables": []
            }
            
            for tbl in tables:
                table_name = tbl['table_name']
                table_info = {"name": table_name, "columns": [], "indexes": [], 
                            "primary_key": [], "foreign_keys": []}
                
                # Get columns
                cur.execute("""
                    SELECT column_name, data_type, 
                           is_nullable::bool as nullable,
                           column_default as "default"
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, table_name))
                table_info["columns"] = cur.fetchall()
                
                # Get primary key
                cur.execute("""
                    SELECT a.attname as column_name
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass
                    AND i.indisprimary
                """, (f"{schema}.{table_name}",))
                pk_columns = cur.fetchall()
                table_info["primary_key"] = [col['column_name'] for col in pk_columns]
                
                # Get indexes
                cur.execute("""
                    SELECT
                        i.relname as name,
                        ix.indisunique as unique,
                        array_agg(a.attname ORDER BY k.i) as columns
                    FROM
                        pg_class t,
                        pg_class i,
                        pg_index ix,
                        pg_attribute a,
                        generate_subscripts(ix.indkey, 1) k(i)
                    WHERE
                        t.oid = %s::regclass
                        AND ix.indrelid = t.oid
                        AND i.oid = ix.indexrelid
                        AND a.attrelid = t.oid
                        AND a.attnum = ix.indkey[k.i]
                        AND NOT ix.indisprimary
                    GROUP BY
                        i.relname,
                        ix.indisunique
                    ORDER BY
                        i.relname;
                """, (f"{schema}.{table_name}",))
                table_info["indexes"] = cur.fetchall()
                
                # Get foreign keys
                cur.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_schema AS foreign_schema,
                        ccu.table_name AS foreign_table,
                        ccu.column_name AS foreign_column
                    FROM
                        information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                          AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = %s
                        AND tc.table_name = %s
                """, (schema, table_name))
                table_info["foreign_keys"] = cur.fetchall()
                
                result["tables"].append(table_info)
            
            return result


def fetch_table_stats(tables: List[str], schema: str = "public", timeout_ms: int = 5000) -> Dict[str, Any]:
    """
    Fetch per-table stats for given tables: approximate row counts and existing indexes.

    This function keeps catalog access minimal and bounded by statement_timeout.
    Returns a mapping: { table_name: { rows: float, indexes: [ { name, unique, columns[] } ] } }
    """
    if not tables:
        return {}

    # Normalize and schema-qualify
    norm_tables = sorted({t for t in tables if t and not t.startswith("(")})

    out: Dict[str, Any] = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Respect timeout
            cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")

            # Row estimates from pg_class.reltuples (approx row count)
            cur.execute(
                """
                SELECT c.relname as table_name, c.reltuples::bigint AS rows
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relkind = 'r'
                  AND c.relname = ANY(%s)
                ORDER BY c.relname
                """,
                (schema, norm_tables),
            )
            for r in cur.fetchall():
                out[r["table_name"]] = {"rows": float(r.get("rows") or 0), "indexes": []}

            # Existing indexes (non-PK)
            cur.execute(
                """
                SELECT
                    t.relname AS table_name,
                    i.relname AS name,
                    ix.indisunique AS unique,
                    array_agg(a.attname ORDER BY k.i) AS columns
                FROM pg_class t
                JOIN pg_namespace ns ON ns.oid = t.relnamespace
                JOIN pg_index ix ON ix.indrelid = t.oid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid
                JOIN generate_subscripts(ix.indkey, 1) k(i) ON TRUE
                WHERE ns.nspname = %s
                  AND t.relname = ANY(%s)
                  AND NOT ix.indisprimary
                GROUP BY t.relname, i.relname, ix.indisunique
                ORDER BY t.relname, i.relname
                """,
                (schema, norm_tables),
            )
            for r in cur.fetchall():
                tbl = r["table_name"]
                if tbl not in out:
                    out[tbl] = {"rows": 0.0, "indexes": []}
                out[tbl].setdefault("indexes", []).append(
                    {
                        "name": r.get("name"),
                        "unique": bool(r.get("unique")),
                        "columns": r.get("columns") or [],
                    }
                )

    return out
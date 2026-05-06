# To use with Claude Code, add to your MCP settings:
# {
#   "mcpServers": {
#     "bastion": {
#       "command": "python",
#       "args": ["-m", "bastion"]
#     }
#   }
# }

import json
import sys

import bastion
from bastion.db import get_db
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bastion")


# --- Error tools ---

@mcp.tool()
def get_recent_errors(limit: int = 10) -> list:
    """Return the most recently seen errors, newest first.

    Each record includes id, type, message, function, file, line, fingerprint,
    occurrence_count, first_seen, and last_seen. Use get_error_detail() for
    full records including locals and hint.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT id, type, message, function, file, line, fingerprint, "
            "occurrence_count, first_seen, last_seen FROM errors "
            "ORDER BY last_seen DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_error_detail(error_id: str) -> dict:
    """Return the full error record for a given error id.

    Includes all fields: locals (JSON string of captured variables) and hint
    (optional developer note). Returns {"error": "not found"} if no match.
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM errors WHERE id = ?", (error_id,)
        ).fetchone()
        return dict(row) if row else {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_errors_by_fingerprint(fingerprint: str) -> dict:
    """Return the error record matching a given fingerprint.

    Fingerprints are SHA256 digests of (exception type, file, line). Multiple
    occurrences of the same error share one record with an incrementing
    occurrence_count. Returns {"error": "not found"} if no match.
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM errors WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        return dict(row) if row else {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


# --- Checkpoint tools ---

@mcp.tool()
def get_checkpoints(flow: str = None, run_id: str = None, limit: int = 50) -> list:
    """Return checkpoint records ordered oldest-first so you see the execution sequence.

    Filter by flow name and/or run_id to narrow to a specific execution trace.
    Omit both to retrieve all checkpoints across all flows.
    """
    try:
        conn = get_db()
        query = "SELECT * FROM checkpoints"
        params = []
        conditions = []
        if flow is not None:
            conditions.append("flow = ?")
            params.append(flow)
        if run_id is not None:
            conditions.append("run_id = ?")
            params.append(run_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_flows() -> list:
    """Return a sorted list of all distinct flow names recorded in checkpoints.

    Use this to discover what named flows exist before calling get_checkpoints()
    with a specific flow filter.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT DISTINCT flow FROM checkpoints ORDER BY flow ASC"
        ).fetchall()
        return [r["flow"] for r in rows]
    except Exception as e:
        return {"error": str(e)}


# --- Expectation tools ---

@mcp.tool()
def get_failed_expectations(limit: int = 10) -> list:
    """Return the most recently failed expectations, newest first.

    Each record includes the message, context, file, line, and timestamp.
    Use this to quickly identify what invariants broke during a run.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM expectations WHERE passed = 0 "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_expectations(limit: int = 20) -> list:
    """Return recent expectations (both passed and failed), newest first.

    Use this to see the full assertion history for a run. Filter for failures
    with get_failed_expectations() when you only care about broken invariants.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM expectations ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


# --- Breadcrumb tools ---

# TODO: v2 — tags filtering currently filters Python-side after fetch.
# Migrate to SQL JSON_EACH() for performance when breadcrumb volume is high
@mcp.tool()
def get_breadcrumbs(severity: str = None, tags: str = None, limit: int = 50) -> list:
    """Return breadcrumb event markers ordered oldest-first for chronological tracing.

    Filter by severity (debug, info, warning, error, critical) and/or by tags
    (comma-separated string, e.g. "payment,stripe" — matches any tag in the list).
    """
    try:
        conn = get_db()
        query = "SELECT * FROM breadcrumbs"
        params = []
        if severity is not None:
            query += " WHERE severity = ?"
            params.append(severity)
        query += " ORDER BY timestamp ASC"
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        if tags is not None:
            tag_set = {t.strip() for t in tags.split(",")}

            def has_tag(row: dict) -> bool:
                stored = json.loads(row.get("tags") or "[]")
                return bool(tag_set & set(stored))

            rows = [r for r in rows if has_tag(r)]
        return rows[:limit]
    except Exception as e:
        return {"error": str(e)}


# --- Utility tools ---

@mcp.tool()
def get_summary() -> dict:
    """Return a high-level snapshot of everything Bastion has recorded.

    Fields: error_count, most_frequent_error, last_checkpoint, last_breadcrumb,
    failed_expectation_count. Any field is null if its table is empty.
    Start here to orient yourself before drilling into specific tables.
    """
    try:
        conn = get_db()
        error_count = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
        mfe_row = conn.execute(
            "SELECT type, message, file, line, occurrence_count FROM errors "
            "ORDER BY occurrence_count DESC LIMIT 1"
        ).fetchone()
        cp_row = conn.execute(
            "SELECT flow, step, timestamp FROM checkpoints "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        bc_row = conn.execute(
            "SELECT message, severity, timestamp FROM breadcrumbs "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        failed_count = conn.execute(
            "SELECT COUNT(*) FROM expectations WHERE passed = 0"
        ).fetchone()[0]
        return {
            "error_count": error_count,
            "most_frequent_error": dict(mfe_row) if mfe_row else None,
            "last_checkpoint": dict(cp_row) if cp_row else None,
            "last_breadcrumb": dict(bc_row) if bc_row else None,
            "failed_expectation_count": failed_count,
        }
    except Exception as e:
        return {"error": str(e)}


# TODO: v2 — add per-table clear tools: clear_errors(), clear_checkpoints(),
# clear_expectations(), clear_breadcrumbs() for surgical clearing
@mcp.tool()
def clear_all() -> dict:
    """Delete all records from every Bastion table (errors, checkpoints, expectations, breadcrumbs).

    Use this to reset state between test runs or debugging sessions.
    This operation is irreversible.
    """
    try:
        conn = get_db()
        conn.execute("DELETE FROM errors")
        conn.execute("DELETE FROM checkpoints")
        conn.execute("DELETE FROM expectations")
        conn.execute("DELETE FROM breadcrumbs")
        conn.commit()
        return {"status": "cleared", "message": "all tables cleared"}
    except Exception as e:
        return {"error": str(e)}


def run() -> None:
    """Start the Bastion MCP server over stdio transport."""
    # Redirect stdout to stderr during init — stdio transport requires a clean stdout.
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        bastion.init()
    finally:
        sys.stdout = old_stdout
    mcp.run(transport="stdio")

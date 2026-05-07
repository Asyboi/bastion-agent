# Bastion

**Runtime context for coding agents — structured error observability built for the agent era**

[![PyPI version](https://img.shields.io/pypi/v/bastion-agent)](https://pypi.org/project/bastion-agent/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/bastion-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem

When a coding agent writes code that breaks, the default feedback loop looks like this: agent runs the code, something raises, the agent reads a wall of unstructured stdout or a raw traceback, guesses at the cause, asks you to add more logging, you re-run and paste output back. That loop is slow and lossy because each iteration discards context. Traditional error handling was designed for a human sitting at a terminal — one reader, interactive, patient. A coding agent is none of those things. It needs structured, queryable runtime context, not formatted text.

## What Bastion Does

Bastion gives your coding agent structured access to what is actually happening at runtime. Four instrumentation primitives — `guard()`, `checkpoint()`, `expect()`, and `breadcrumb()` — replace traditional error handling with agent-readable structured records persisted to a local SQLite store. An MCP server exposes that store as ten queryable tools the agent calls on demand. No stdout parsing, no copy-pasting, no re-running with extra logs added.

## Who It Is For

Bastion earns its place in:

- Complex multi-step workflows with many moving parts where you need to reconstruct what happened between steps
- Multi-agent orchestration layers with API calls, retries, and rate limits — anywhere the execution path is non-trivial
- Long-running processes and background jobs that fail silently and leave no trail
- Existing codebases where an agent needs runtime history to debug effectively, not just static analysis

It is not the right fit for:

- Simple one-off scripts where reading the single traceback is sufficient
- Greenfield code that works on the first run and has no meaningful failure modes yet

---

## Installation

```bash
pip install bastion-agent

# httpx is used in the Quick Start example below — not a Bastion dependency
pip install httpx
```

---

## Quick Start

```python
import bastion
import httpx

bastion.init()


@bastion.guard(context=["agent_id", "endpoint", "retry_count"])
def call_api(agent_id: str, endpoint: str, retry_count: int = 0) -> dict:
    bastion.breadcrumb(
        f"agent {agent_id} calling {endpoint}",
        severity="info",
        tags=["api", agent_id],
    )

    response = httpx.get(endpoint, timeout=10)

    bastion.expect(
        response.status_code != 429,
        "Rate limit hit",
        context={"agent_id": agent_id, "endpoint": endpoint, "retry_count": retry_count},
    )

    bastion.checkpoint("api_flow", "call_succeeded", {
        "agent_id": agent_id,
        "endpoint": endpoint,
        "status_code": response.status_code,
        "retry_count": retry_count,
    })

    return response.json()
```

There are two distinct failure paths here. If `httpx.get()` raises a network exception, execution leaves `call_api()` immediately — `guard()` catches it, records the exception type, message, source location, and the three named locals (`agent_id`, `endpoint`, `retry_count`), then re-raises. `expect()` and `checkpoint()` are never reached in that path. If the request succeeds but returns a 429, execution reaches `expect()`, which persists the failed assertion before raising `AssertionError` — and `guard()` then catches that too, so you get both records. Every `breadcrumb()` call fires regardless of which path is taken. Your agent queries all of it without re-running anything.

---

## MCP Server Setup

### Starting the server

```bash
# via module
python -m bastion

# or via the console script installed with pip
bastion-mcp
```

### Claude Code configuration

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "bastion": {
      "command": "python",
      "args": ["-m", "bastion"]
    }
  }
}
```

### Cursor configuration

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "bastion": {
      "command": "bastion-mcp",
      "args": []
    }
  }
}
```

### Available MCP tools

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `get_summary` | High-level snapshot: error count, most frequent error, last checkpoint, last breadcrumb, failed expectation count | — |
| `get_recent_errors` | Most recently seen errors, newest first (summary fields only) | `limit` (default 10) |
| `get_error_detail` | Full error record including captured locals and hint | `error_id` |
| `get_errors_by_fingerprint` | Error record for a given SHA256 fingerprint | `fingerprint` |
| `get_checkpoints` | Checkpoint records ordered oldest-first for execution tracing | `flow`, `run_id`, `limit` |
| `get_flows` | All distinct flow names recorded in checkpoints | — |
| `get_failed_expectations` | Failed expectations only, newest first | `limit` (default 10) |
| `get_expectations` | All expectations (passed and failed), newest first | `limit` (default 20) |
| `get_breadcrumbs` | Event markers ordered oldest-first for chronological tracing | `severity`, `tags` (comma-separated), `limit` |
| `clear_all` | Delete all records from every table — use between test runs | — |

Start a debugging session with `get_summary` to orient, then drill into the relevant table.

---

## The Four Primitives

### `guard()`

Wraps a function in structured exception capture. When the wrapped function raises, `guard()` records the exception type, message, source location, and named locals (or all locals if `context` is omitted), then re-raises so your control flow is unaffected.

```python
@bastion.guard(context=["user_id", "payload"])
def process_submission(user_id: str, payload: dict) -> dict:
    if not payload.get("items"):
        raise ValueError("submission has no items")
    return submit(payload)
```

**Replaces:** a bare `try/except` that either swallows the error or prints an unstructured traceback.

---

### `checkpoint()`

Records a named step within a named logical flow. Use it to mark the boundary between stages in a multi-step process so an agent can reconstruct what completed before a failure.

```python
bastion.checkpoint("document_pipeline", "chunking_complete", {
    "doc_id": doc.id,
    "chunk_count": len(chunks),
    "run_id": run_id,
})
```

**Replaces:** `print("step 3 done")` statements that vanish from context and can't be queried.

---

### `expect()`

Asserts a condition and persists the result regardless of outcome. Failed expectations raise `AssertionError` after writing the record, so agents can query "what invariants broke during this run" without grepping logs.

```python
bastion.expect(
    len(search_results) > 0,
    "search must return at least one result",
    context={"query": query, "index": index_name},
)
```

**Replaces:** bare `assert` statements that raise but leave no queryable record behind.

---

### `breadcrumb()`

Records an ambient event marker with no frame capture or condition checking. Use it for high-frequency events where you want chronological tracing without the overhead of exception handling.

```python
bastion.breadcrumb(
    f"rate limiter sleeping {backoff:.1f}s",
    severity="warning",
    tags=["rate_limit", agent_id],
)
```

**Replaces:** `logger.info()` calls that produce unstructured output an agent has to parse.

---

## How It Works

The library captures structured records at the point of instrumentation and persists them to a local SQLite database at `~/.bastion/bastion.db`. The MCP server reads from that same database and exposes the records as typed tool responses. When an agent needs to understand a failure, it calls the appropriate MCP tool — `get_recent_errors`, `get_checkpoints`, or `get_failed_expectations` — and receives a structured list it can reason about directly. There is no daemon process, no network call, and no background sync. Everything runs locally and the database is a single file you can inspect with any SQLite browser.

---

## Roadmap

| Version | Milestone | Status |
|---------|-----------|--------|
| v0.1.0 | Package skeleton — typed stubs, correct public API, importable | ✓ |
| v0.2.0 | SQLite persistence, `guard()`, `checkpoint()`, `expect()`, `breadcrumb()` | ✓ |
| v0.3.0 | MCP server with 10 query tools, `bastion-mcp` entry point | ✓ |
| v1.0.0 | Node.js port, full documentation site, MCP registry listing | planned |
| v2.0.0 | Team mode with Turso DB, per-table clear tools, opt-out variable capture | planned |

---

## Contributing

Bastion is early-stage and the API is not frozen. If you hit a rough edge or have a strong opinion about how the instrumentation primitives should behave, opening an issue is the most useful thing you can do. Pull requests are welcome for bug fixes, documentation improvements, and new MCP tools. Feedback on the API design — naming, signatures, what gets persisted — is especially valuable right now, before v1.0.0 locks things in.

---

## License

MIT

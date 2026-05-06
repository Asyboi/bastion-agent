# Bastion — CLAUDE.md

## Project Overview

Bastion is error observability infrastructure for the agent era. The core thesis: traditional debugging tools are designed for humans reading terminal output or log dashboards. Bastion is designed with the assumption that a coding agent is the primary consumer of error data — every record should be compact, structured, and queryable without human curation.

The project has two main components:

1. **Python library** (`bastion/`) — decorators and functions that instrument application code and emit structured records.
2. **MCP server** (coming in v0.3.0) — a local server that exposes Bastion's SQLite store to any MCP-compatible agent via query tools (`list_errors`, `get_error`, `list_checkpoints`, etc.).

## Architecture

### `core.py`
The entry point. `init()` configures the runtime (db path, project name) and will own the SQLite connection lifecycle. All other modules depend on the connection opened here.

### `guard.py`
The workhorse. `guard()` is a decorator factory. When a wrapped function raises, it captures the exception into a structured dict — type, message, source location — and (eventually) local variables. Re-raises so normal control flow is not disrupted. Agents query the errors table to understand what went wrong and where.

### `checkpoint.py`
Lightweight progress markers. `checkpoint(flow, step, data)` records named steps within a named logical flow. Useful for agents reconstructing what a long-running task was doing when it failed. Maps to a `checkpoints` SQLite table.

### `expect.py`
Structured assertions. `expect(condition, message, context)` is `assert` with an agent-readable paper trail. Failed expectations are persisted so agents can query "what invariants broke during this run" without grepping logs.

### `breadcrumb.py`
Lightweight event markers. `breadcrumb(message, severity, tags)` records ambient ordered events with no frame capture or condition checking. Useful for agents tracing execution flow between errors and checkpoints. Maps to a `breadcrumbs` SQLite table.

### Relationships
- All modules import nothing from each other; only `core.py`'s module-level `_db` connection (v0.2+) will be shared.
- The public API surface is entirely flat: `import bastion` then `bastion.<function>()`.
- SQLite is the only persistence layer — no network, no daemon, one file per project.

## Design Principles

**Token efficiency** — error records must be compact by default. An agent reading 50 errors should not exhaust its context window. Detailed payloads (local variable dumps, full tracebacks) should be available on demand, not emitted by default.

**Agent-first** — every design decision should be evaluated against: "is this useful to a coding agent trying to diagnose a failure?" Field names, record shapes, and query tools are all optimized for programmatic consumption.

**Local-first** — no cloud, no accounts, no telemetry. Everything lives in a single `.bastion.db` SQLite file in the project root. The developer owns their data.

**Human-readable too** — the framework should not be hostile to humans. Printed output is a clean Python dict. The SQLite schema is simple enough to query with any SQLite browser.

## Roadmap

| Version | Milestone |
|---------|-----------|
| v0.1.0  | Package skeleton — typed stubs, correct public API, importable |
| v0.2.0  | SQLite persistence, local variable capture via `inspect`, error fingerprinting |
| v0.3.0  | MCP server with core query tools (`list_errors`, `get_checkpoint`, `query_expectations`) |
| v1.0.0  | Node.js port, full documentation site, MCP registry listing |

## Working With This Codebase

- **Keep stubs typed.** Every function must have complete type annotations even before the body is implemented. Agents reading the source need to understand signatures without running the code.
- **TODO comments are the roadmap.** Each `# TODO:` in a stub describes the exact implementation needed. Do not remove or generalise them — they are the specification for the next session.
- **Verify importability** after any change to the package structure:
  ```bash
  python -c "import bastion; bastion.init()"
  ```
- **No external dependencies** until v0.2.0. The standard library (`inspect`, `traceback`, `datetime`, `sqlite3`) covers everything needed.
- **One public API, flat.** Do not expose submodule internals. Everything the user needs should be reachable via `import bastion`.

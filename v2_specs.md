# v2 Features

# FEAT — guard() v2 variable capture design

v2 replaces the explicit `context=` allowlist with an opt-out model. By default, `guard()` captures all local variables in scope at the point of failure. Developers exclude known sensitive variables explicitly:

```python
@guard(exclude=["password", "token"])
def process_payment(user_id, amount, password):
    ...
```

This reduces instrumentation friction significantly — the common case (capture everything except obvious secrets) requires minimal configuration, while the developer retains full control over exclusions.

## Automatic scrubbing

Operates as a secondary safety net beneath the opt-out layer. Any variable whose name matches a pattern in a predefined sensitive key list is automatically redacted regardless of whether it appears in `exclude`. This catches cases where a developer forgets to exclude a sensitive variable or a new sensitive variable is introduced to a function without updating the decorator. Scrubbing replaces the value with `"[redacted]"` and does not raise an error.

Default pattern list:
- `password`, `passwd`
- `secret`
- `token`
- `api_key`, `apikey`
- `auth`, `credential`
- `ssn`
- `card`, `cvv`, `pin`

The pattern list is user-configurable via `bastion.init(sensitive_keys=[...])`.

## Type-aware truncation

Prevents large objects from bloating stored error records. Truncation rules apply per type before the record is written to SQLite:

| Type | Behavior |
|---|---|
| `str` | Truncated at 200 chars, `"...[truncated]"` appended |
| `list` / `tuple` | Length recorded, first 5 items captured |
| `dict` | Keys always captured, values truncated to 100 chars each |
| `DataFrame` | Shape only, e.g. `"DataFrame(1000x12)"` |
| All other types | `repr()` truncated at 300 chars |

Truncation limits are user-configurable via `bastion.init(truncation_limits={...})`.

## Capture order of operations

1. Exclude list applied
2. Automatic scrubbing applied
3. Type-aware truncation appliedpplied first → automatic scrubbing applied second → type-aware truncation applied last.

# FEAT: guard() — hint parameter

## Overview

The `hint` parameter is a developer-authored note attached to the `@guard()`
decorator that is stored alongside the error record and surfaced to the coding
agent when it queries the error via MCP. It gives the agent a direct signal
from the developer about what is likely wrong, rather than requiring the agent
to reason entirely from the structured error data alone.

## Motivation

Structured error data — type, message, location, local variables — tells the
agent *what* broke and *where*. It does not always tell the agent *why*. Some
failure modes are non-obvious from the error alone: an upstream service
returning an unexpected response, a race condition, a known edge case in a
third-party library. The developer often knows the likely cause but has no
way to communicate it to the agent short of a comment in the code the agent
may or may not read.

`hint` solves this by putting the developer's knowledge directly in the error
record where the agent will always see it.

## Usage

```python
@bastion.guard(hint="Check whether the upstream auth service returned a valid session before this runs")
def process_payment(user_id, amount):
    ...
```

## Behavior

- If `hint` is provided, it is stored in the `hint` column of the errors table
  alongside the structured error record
- If `hint` is not provided, the column is NULL — no behavior change
- `hint` is a plain string — no formatting or structure is enforced
- `hint` is static — it is set at decoration time, not at exception time

## Agent experience

When the agent calls `get_error_detail(error_id)` via MCP, the hint is
included in the response:

```json
{
  "type": "KeyError",
  "message": "'user_id' not found",
  "location": "auth/middleware.py:47",
  "hint": "Check whether the upstream auth service returned a valid session before this runs",
  "locals": {"request": "..."},
  "occurrence_count": 12
}
```

The agent reads the hint before forming a hypothesis, giving it a head start
on the likely fix.

## Implementation notes

- Add `hint: Optional[str] = None` as a kwarg to `guard()`
- Include `"hint": hint` in `error_record` before calling `upsert_error()`
- The `hint` column already exists in the errors table schema — no migration
  required

# FEAT — Team Mode & Turso DB Migration

## Overview

v2 introduces team mode, enabling multiple developers sharing a codebase to
share a single Bastion error store. This requires moving beyond a local SQLite
file to a database layer that supports concurrent writes and cloud sync. Turso
is the natural upgrade path — it is a drop-in SQLite replacement with no API
changes required, meaning the migration is a one-file change to the database
abstraction layer.

## Team Mode

In v1, Bastion is strictly local — one developer, one machine, one SQLite file.
In v2, team mode allows a shared error store across multiple developers working
on the same codebase. When team mode is enabled, errors captured by any
developer's `guard()`, `checkpoint()`, `expect()`, or `breadcrumb()` calls are
written to a shared store visible to the whole team.

This changes the MCP query experience significantly — instead of an agent seeing
only errors from the current developer's session, it can query across the team's
full error history. Recurring errors that multiple developers have hit independently
become immediately visible, and deduplication via fingerprinting becomes more
valuable as the error volume grows.

Team mode is opt-in and configured via `bastion.init()`:

```python
bastion.init(
    mode="team",
    db_url="libsql://your-team.turso.io",
    db_token="your-turso-token",
)
```

Local mode remains the default. No cloud dependency is introduced unless the
developer explicitly opts into team mode.

## Turso as the Database Layer

v1 uses Python's stdlib `sqlite3` with a clean database abstraction layer
designed for exactly this migration. v2 swaps that layer for Turso, using the
`libsql-python` client. The SQL schema, query logic, and MCP tools remain
unchanged — only the connection layer is swapped.

Turso's built-in MCP server is also worth evaluating in v2 as a potential
replacement for Bastion's custom MCP server, since it exposes any Turso
database directly to coding agents via MCP with no additional code required.

Key Turso features that unlock in v2:
- Concurrent writes via MVCC — multiple developers writing simultaneously
  without locking conflicts
- Cloud sync — errors written on one machine are immediately visible to
  teammates
- Branching — snapshot the error store at any point, useful for debugging
  a specific release or reproducing a reported issue
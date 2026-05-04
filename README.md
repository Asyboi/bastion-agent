# bastion

Error observability for the agent era.

## What is Bastion?

Traditional error handling is designed for humans: stack traces printed to a terminal, logs scrolled through in a browser, exceptions caught and swallowed silently. Bastion is built on a different assumption — that the primary debugger is a coding agent, not a human. Every error record, checkpoint, and failed assertion is structured for easy ingestion by an agent's context window, not a human's eyes.

Bastion sits at the boundary between your code and the agent working on it. It captures the information an agent needs to diagnose a failure — exception type, location, local variables — and makes it retrievable without manual log trawling. The goal is to shrink the feedback loop between a bug occurring and an agent understanding it.

## Installation

```bash
pip install bastion
```

## Quick start

```python
import bastion

# Initialize at the entry point of your application or agent session.
bastion.init()

# Wrap any function — errors are captured and structured automatically.
@bastion.guard(context=["user_id", "payload"])
def process(user_id: str, payload: dict) -> dict:
    if not payload:
        raise ValueError("empty payload")
    return {"ok": True}

# Mark progress through a multi-step flow.
bastion.checkpoint("ingest", "parse-complete", data={"rows": 42})

# Assert invariants in a way an agent can query later.
bastion.expect(len(results) > 0, "search must return results", context={"query": query})
```

## Coming soon

- **SQLite persistence** — every error, checkpoint, and expectation stored locally and queryable
- **MCP server** — expose Bastion data to any MCP-compatible agent via structured tools
- **Local variable capture** — `context=` on `guard()` will snapshot named variables at the point of failure
- **Error fingerprinting** — stable IDs for recurring errors so agents can track frequency over time

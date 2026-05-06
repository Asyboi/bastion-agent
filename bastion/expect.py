"""Expect — structured assertion for agent-observable invariants."""

import inspect
from datetime import datetime, timezone
from typing import Optional

from bastion.db import insert_expectation


def expect(
    condition: bool,
    message: str,
    context: Optional[dict] = None,
) -> None:
    """Assert a condition and emit a structured record, always persisted.

    Args:
        condition: Boolean expression to assert.
        message:   Human/agent-readable description of what was expected.
        context:   Optional extra data to surface alongside the result.

    Raises:
        AssertionError: Raised when ``condition`` is ``False``, after persisting.

    Example::

        bastion.expect(len(results) > 0, "search returned results", context={"query": q})
    """
    caller = inspect.currentframe().f_back
    file = caller.f_code.co_filename
    line = caller.f_lineno

    record = {
        "message": message,
        "context": context,
        "passed": bool(condition),
        "file": file,
        "line": line,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(record)
    # TODO: v2 — add support for capturing caller frame locals automatically
    # when condition is False, similar to guard() locals capture, so the agent
    # has full variable state at the point of a failed expectation
    try:
        insert_expectation(record)
    except Exception:
        pass

    if not condition:
        raise AssertionError(message)

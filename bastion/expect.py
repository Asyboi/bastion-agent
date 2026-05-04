"""Expect — structured assertion for agent-observable invariants."""

from typing import Any, Optional


def expect(condition: bool, message: str, context: Optional[Any] = None) -> None:
    """Assert a condition and emit a structured record if it fails.

    Args:
        condition: Boolean expression to assert.
        message:   Human/agent-readable description of what was expected.
        context:   Optional extra data to surface alongside the failure.

    Raises:
        AssertionError: Always raised when ``condition`` is ``False``.

    Example::

        bastion.expect(len(results) > 0, "search returned results", context={"query": q})
    """
    if not condition:
        record = {
            "message": message,
            "context": context,
        }
        print(record)
        # TODO: capture caller frame locals via inspect.currentframe().f_back and filter
        #       to variables explicitly listed in `context` when context is a list of names
        #       rather than an arbitrary value.
        # TODO: generate a fingerprint (sha256 of message + caller file + line) and add
        #       it to record under a "fingerprint" key.
        # TODO: persist record to the SQLite expectations table opened by core.init().
        raise AssertionError(str(record))

"""Checkpoint — structured progress markers for agent flows."""

from datetime import datetime, timezone
from typing import Any, Optional


def checkpoint(flow: str, step: str, data: Optional[Any] = None) -> None:
    """Record a named step within a named flow.

    Args:
        flow:  Top-level logical flow name (e.g. ``"code-review"``).
        step:  Name of the current step within that flow.
        data:  Optional payload — any JSON-serialisable value.

    Example::

        bastion.checkpoint("refactor", "pre-lint", {"files": ["a.py"]})
    """
    record = {
        "flow": flow,
        "step": step,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(record)
    # TODO: serialize `data` via json.dumps with a fallback for non-serialisable types (repr).
    # TODO: persist record to the SQLite checkpoints table opened by core.init(),
    #       inserting flow, step, data (JSON text), and timestamp columns.

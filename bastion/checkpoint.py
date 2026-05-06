"""Checkpoint — structured progress markers for agent flows."""

from datetime import datetime, timezone
from typing import Optional

from bastion.db import insert_checkpoint


def checkpoint(
    flow: str,
    step: str,
    data: Optional[dict] = None,
    run_id: Optional[str] = None,
) -> None:
    """Record a named step within a named flow.

    Args:
        flow:    Top-level logical flow name (e.g. ``"code-review"``).
        step:    Name of the current step within that flow.
        data:    Optional payload — any JSON-serialisable value.
        run_id:  Optional identifier grouping checkpoints from the same run.

    Example::

        bastion.checkpoint("refactor", "pre-lint", {"files": ["a.py"]})
    """
    record = {
        "flow": flow,                                    # str
        "step": step,                                    # str
        "data": data,                                    # dict | None
        "run_id": run_id,                                # str | None
        "timestamp": datetime.now(timezone.utc).isoformat(),  # str — ISO 8601 UTC
    }
    print(record)
    try:
        insert_checkpoint(record)
    except Exception:
        pass

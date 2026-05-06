"""Breadcrumb — lightweight ordered event markers for agent observability."""

from datetime import datetime, timezone
from typing import List, Optional

from bastion.db import insert_breadcrumb

_VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}


def breadcrumb(
    message: str,
    severity: str = "debug",
    tags: Optional[List[str]] = None,
) -> None:
    """Record an ambient event marker with no frame capture.

    Args:
        message:  Human/agent-readable description of the event.
        severity: One of debug, info, warning, error, critical. Defaults to debug if invalid.
        tags:     Optional list of string labels for filtering.

    Example::

        bastion.breadcrumb("payment validation entered", severity="info", tags=["payment"])
    """
    if severity not in _VALID_SEVERITIES:
        severity = "debug"

    record = {
        "message": message,
        "severity": severity,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(record)
    # TODO: v2 — add max_breadcrumbs config option to bastion.init() so the
    # breadcrumbs table is automatically pruned to the N most recent records,
    # preventing unbounded growth in long running applications
    try:
        insert_breadcrumb(record)
    except Exception:
        pass

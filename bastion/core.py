"""Core initialization for Bastion."""

from typing import Any, Dict, Optional

_config: Dict[str, Any] = {}


def init(config: Optional[Dict[str, Any]] = None) -> None:
    """Set up Bastion with optional configuration.

    Args:
        config: Optional dict with keys like ``db_path``, ``project``.
    """
    global _config
    _config = config or {}
    print("Bastion initialized")
    # TODO: open (or create) a SQLite database at _config.get("db_path", ".bastion.db")
    #       and run the schema migrations to create errors, checkpoints, and expectations tables.
    # TODO: emit an "init" event record to the SQLite store so agents can see when a session started.

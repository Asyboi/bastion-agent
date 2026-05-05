"""Core initialization for Bastion."""

from pathlib import Path
from typing import Optional

from bastion import db


# TODO: v2 — accept mode="team", db_url, db_token and pass through to db.init_db() for Turso team mode
def init(db_path: Optional[str] = None) -> None:
    """Set up Bastion, opening (or creating) the SQLite database.

    Args:
        db_path: Path to the SQLite database file. Defaults to ~/.bastion/bastion.db.
    """
    resolved = Path(db_path) if db_path else Path.home() / ".bastion" / "bastion.db"
    resolved.parent.mkdir(parents=True, exist_ok=True)
    db.init_db(str(resolved))
    print({"status": "initialized", "db_path": str(resolved)})

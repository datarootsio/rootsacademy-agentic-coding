"""Runtime configuration, read from the environment.

The database path is environment-driven so the lab can boot the app on
throwaway state: a reviewer changing data spends nothing real.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Where the SQLite file lives. The lab points this at a temp directory.
DB_PATH_ENV = "SAVING_STREAK_DB"

#: Timezone for every date calculation in the system (spec D5).
TIMEZONE = "Europe/Brussels"


def db_path() -> Path:
    """Resolve the SQLite file path, defaulting to one beside the backend."""
    configured = os.environ.get(DB_PATH_ENV)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "saving-streak.db"

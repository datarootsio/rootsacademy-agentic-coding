"""Run an isolated browser-test API: PYTHONPATH=src python tests/serve_ui_fixture.py."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from saving_streak.banking import register
from saving_streak.db import connection
from saving_streak.migrations import migrate

if __name__ == "__main__":
    with TemporaryDirectory(prefix="saving-streak-ui-") as temp:
        os.environ["SAVING_STREAK_DB"] = str(Path(temp) / "test.db")
        migrate()
        with connection() as conn:
            for suffix in ("", "-empty", "-late"):
                customer = f"ui-smoke{suffix}"
                register(conn, customer, f"savings-{customer}", "Everyday savings")
        uvicorn.run("saving_streak.api:app", host="127.0.0.1", port=8788)

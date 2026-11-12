"""Starts everything in one event loop. Writes heartbeats. Plan B JSON writer."""

import asyncio
from datetime import datetime, timezone

import db
import api as writer
from config import DEFAULTS

DB_PATH = "desk.db"
conn = db.connect(DB_PATH)

# seed settings
for k, v in DEFAULTS.items():
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (k, str(v), datetime.now(timezone.utc).isoformat()),
    )
conn.commit()

# PAPER start balance
START = float(DEFAULTS["desk.paper_start_stack"])
conn.execute(
    "INSERT INTO balance (ts, value) VALUES (?, ?)",
    (datetime.now(timezone.utc).isoformat(), START),
)
conn.commit()


async def heartbeat_loop():
    while True:
        now = datetime.now(timezone.utc).isoformat()
        for agent in ["scanner", "auditor", "analyst", "executor", "risk"]:
            conn.execute(
                "INSERT OR REPLACE INTO heartbeats (agent, ts) VALUES (?, ?)",
                (agent, now),
            )
        conn.commit()
        writer.write_state(START)
        await asyncio.sleep(15)


async def main():
    print("desk started · PAPER · balance", START)
    await heartbeat_loop()


if __name__ == "__main__":
    asyncio.run(main())

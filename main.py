"""Starts everything in one event loop. Wires the 5 agents. Plan B JSON writer."""

import asyncio
import os
from datetime import datetime, timezone

import db
import api as writer
from config import DEFAULTS
from bus import Bus
from agents import scanner, auditor, analyst, executor, risk

DB_PATH = "desk.db"
conn = db.connect(DB_PATH)

# seed settings once
for k, v in DEFAULTS.items():
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (k, str(v), datetime.now(timezone.utc).isoformat()),
    )
conn.commit()

START = float(DEFAULTS["desk.paper_start_stack"])
if not conn.execute("SELECT 1 FROM balance LIMIT 1").fetchone():
    conn.execute(
        "INSERT INTO balance (ts, value) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), START),
    )
    conn.commit()

settings = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM settings")}


async def heartbeat_loop():
    while True:
        now = datetime.now(timezone.utc).isoformat()
        for agent in ["scanner", "auditor", "analyst", "executor", "risk"]:
            conn.execute(
                "INSERT OR REPLACE INTO heartbeats (agent, ts) VALUES (?, ?)",
                (agent, now),
            )
        conn.commit()
        row = conn.execute("SELECT value FROM balance ORDER BY ts DESC LIMIT 1").fetchone()
        bal = float(row["value"]) if row else START
        writer.write_state(bal)
        await asyncio.sleep(15)


async def main():
    bus = Bus()
    print("desk started · PAPER · balance", START)
    await asyncio.gather(
        heartbeat_loop(),
        scanner.run(bus, conn, settings),
        auditor.run(bus, conn, settings),
        analyst.run(bus, conn, settings),
        executor.run(bus, conn, settings),
        risk.run(bus, conn, settings),
    )


if __name__ == "__main__":
    asyncio.run(main())

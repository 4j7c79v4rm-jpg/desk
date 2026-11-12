"""Risk – agent 5. Stops, trails, timeouts. Never places an order."""

import asyncio
from datetime import datetime, timezone

from links import coin_url


async def run(bus, conn, settings: dict):
    print("Risk starting")
    while True:
        msg = await bus.get(bus.executor_to_risk)
        await _open_position(msg, conn, settings)


async def _open_position(msg: dict, conn, settings: dict):
    mint = msg["mint"]
    now = datetime.now(timezone.utc).isoformat()
    stop_pct = float(settings.get("risk.stop_pct", 6))
    entry = float(msg.get("entry_price") or 0.0001)
    stop_price = entry * (1 - stop_pct / 100)

    conn.execute(
        """INSERT INTO positions
           (mint, opened_at, entry_price, size_usd, peak_price, stop_price,
            trail_active, mode)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
        (mint, now, entry, msg["size_usd"], entry, stop_price, msg.get("mode", "PAPER")),
    )
    conn.commit()
    print(f"Risk: OPENED {mint[:8]} size=${msg['size_usd']:.2f} stop={stop_pct}%")

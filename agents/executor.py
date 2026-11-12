"""Executor – agent 4. Sizes and sends the FOMO button. Never places an order."""

import asyncio
from datetime import datetime, timezone

from links import coin_url
import fees
import telegram


async def run(bus, conn, settings: dict):
    print("Executor starting")
    while True:
        msg = await bus.get(bus.analyst_to_executor)
        await _size_and_signal(msg, bus, conn, settings)


async def _size_and_signal(analyst_msg: dict, bus, conn, settings: dict):
    mint = analyst_msg["mint"]
    now = datetime.now(timezone.utc).isoformat()
    mode = settings.get("desk.mode", "PAPER")

    row = conn.execute("SELECT value FROM balance ORDER BY ts DESC LIMIT 1").fetchone()
    stack = float(row["value"]) if row else float(settings.get("desk.paper_start_stack", 200))

    stack_pct = float(settings.get("executor.stack_pct", 8))
    max_pool_pct = float(settings.get("executor.max_pool_pct", 2))
    min_ticket = float(settings.get("executor.min_ticket_usd", 47.50))
    below_min = settings.get("executor.below_min", "bump")

    liq = 100_000
    size = stack * (stack_pct / 100)
    pool_cap = liq * (max_pool_pct / 100)
    size = min(size, pool_cap)

    if size < min_ticket:
        if below_min == "bump":
            size = min_ticket
        else:
            print(f"Executor: SKIP {mint[:8]} size {size:.2f} < min")
            return

    link = coin_url(mint)
    conn.execute(
        """INSERT INTO signals
           (mint, ts, price, size_usd, stack_pct, link, mode, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pushed')""",
        (mint, now, 0.0, round(size, 2), stack_pct, link, mode),
    )
    conn.commit()

    print(f"Executor: SIGNAL {mint[:8]} size=${size:.2f} mode={mode}")
    print(f"  link: {link}")

    text = f"PAPER · Buy {mint[:6]}… · ${size:.2f}"
    await telegram.send(text, button_url=link, button_label="Buy on FOMO")

    await bus.put(
        bus.executor_to_risk,
        {
            "mint": mint,
            "size_usd": size,
            "entry_price": 0.0,
            "mode": mode,
            "link": link,
            "ts": now,
        },
    )

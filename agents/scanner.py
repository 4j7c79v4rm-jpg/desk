"""Scanner – agent 1. Counts and cuts. Talks only through bus and db."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import websockets

from fields import get as fget
import db

WS_URL = "wss://pumpportal.fun/api/data"
DEX_URL = "https://api.dexscreener.com/tokens/v1/solana/"


async def run(bus, conn, settings: dict):
    """Main Scanner loop. One PumpPortal connection for the desk."""
    print("Scanner starting")
    await asyncio.gather(
        _migration_listener(bus, conn, settings),
        _waiting_room_poller(bus, conn, settings),
    )


async def _migration_listener(bus, conn, settings):
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"method": "subscribeMigration"}))
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if "message" in msg and "Subscribed" in str(msg.get("message", "")):
                            continue
                        mint = fget(msg, "mint")
                        if not mint:
                            continue
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            """INSERT OR IGNORE INTO coins
                               (mint, pool, migrated_at, creator)
                               VALUES (?, ?, ?, ?)""",
                            (mint, fget(msg, "pool"), now, fget(msg, "creator")),
                        )
                        conn.commit()
                        print(f"Scanner: new migration {mint[:8]}...")
                    except Exception as e:
                        print("Scanner migration parse error:", e)
        except Exception as e:
            print("Scanner WS error, reconnecting in 5s:", e)
            await asyncio.sleep(5)


async def _waiting_room_poller(bus, conn, settings):
    poll_s = int(settings.get("scanner.poll_s", 60))
    min_liq = float(settings.get("scanner.min_liquidity_usd", 40000))
    max_top10 = float(settings.get("scanner.max_top10_pct", 25))
    max_h1 = float(settings.get("scanner.max_h1_change_pct", 80))
    min_age = int(settings.get("scanner.min_pool_age_min", 10))
    max_age = int(settings.get("scanner.max_wait_min", 60))

    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            await asyncio.sleep(poll_s)
            rows = conn.execute(
                "SELECT mint, migrated_at FROM coins WHERE mint NOT IN (SELECT mint FROM scans WHERE verdict='pass')"
            ).fetchall()
            if not rows:
                continue
            mints = [r["mint"] for r in rows]
            try:
                r = await client.get(DEX_URL + ",".join(mints[:30]))
                if r.status_code != 200:
                    continue
                pairs = r.json()
                if not isinstance(pairs, list):
                    continue
                for p in pairs:
                    mint = p.get("baseToken", {}).get("address")
                    if not mint:
                        continue
                    liq = float(p.get("liquidity", {}).get("usd") or 0)
                    h1 = float(p.get("priceChange", {}).get("h1") or 0)
                    created = p.get("pairCreatedAt")
                    age_min = 999
                    if created:
                        age_min = int((time.time() * 1000 - created) / 60000)
                    reason = None
                    if liq < min_liq:
                        reason = f"liq {liq:.0f} < {min_liq}"
                    elif abs(h1) > max_h1:
                        reason = f"h1 {h1:.1f}% > {max_h1}"
                    elif age_min < min_age:
                        reason = f"age {age_min}m < {min_age}"
                    elif age_min > max_age:
                        reason = f"age {age_min}m > {max_age}"
                    verdict = "cut" if reason else "pass"
                    now = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        """INSERT INTO scans
                           (mint, ts, liquidity_usd, h1_change_pct, age_min, verdict, reason)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (mint, now, liq, h1, age_min, verdict, reason),
                    )
                    conn.commit()
                    if verdict == "pass":
                        await bus.put(
                            bus.scanner_to_auditor,
                            {"mint": mint, "pair": p, "ts": now},
                        )
                        print(f"Scanner: PASS {mint[:8]} liq={liq:.0f}")
                    else:
                        print(f"Scanner: CUT  {mint[:8]} {reason}")
            except Exception as e:
                print("Scanner Dex error:", e)

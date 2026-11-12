"""Analyst – agent 3. Rules mode only (no Jev). Talks only through bus and db."""

import asyncio
from datetime import datetime, timezone

import httpx


async def run(bus, conn, settings: dict):
    print("Analyst starting (rules mode)")
    while True:
        msg = await bus.get(bus.auditor_to_analyst)
        await _score(msg, bus, conn, settings)


async def _score(auditor_msg: dict, bus, conn, settings: dict):
    mint = auditor_msg["mint"]
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.dexscreener.com/tokens/v1/solana/{mint}")
            pairs = r.json() if r.status_code == 200 else []
        except Exception:
            pairs = []

    pair = None
    if isinstance(pairs, list) and pairs:
        pair = next((p for p in pairs if p.get("dexId") == "pumpswap"), pairs[0])

    vol_h1 = float(pair.get("volume", {}).get("h1") or 0) if pair else 0
    buys_h1 = int(pair.get("txns", {}).get("h1", {}).get("buys") or 0) if pair else 0
    h1_pct = float(pair.get("priceChange", {}).get("h1") or 0) if pair else 0
    m5_pct = float(pair.get("priceChange", {}).get("m5") or 0) if pair else 0

    alive_thresh = float(settings.get("analyst.alive_volume_h1", 25000))
    organic_thresh = int(settings.get("analyst.organic_buys_h1", 150))
    chase_thresh = float(settings.get("analyst.chase_h1_pct", 80))
    flush_thresh = float(settings.get("analyst.flush_drop_m5_pct", 5))

    alive_6h = 0.8 if vol_h1 >= alive_thresh else 0.3
    organic = 0.75 if buys_h1 >= organic_thresh else 0.4
    flush = 0.7 if m5_pct <= -flush_thresh else 0.3
    chase = 0.8 if h1_pct >= chase_thresh else 0.2

    score = int((alive_6h * 30 + organic * 30 + (1 - chase) * 25 + flush * 15))

    min_alive = float(settings.get("analyst.min_alive_6h", 0.70))
    min_organic = float(settings.get("analyst.min_organic", 0.65))
    max_chase = float(settings.get("analyst.max_chase", 0.30))
    min_score = int(settings.get("analyst.min_score", 70))

    passed = (
        alive_6h >= min_alive
        and organic >= min_organic
        and chase <= max_chase
        and score >= min_score
    )
    reason = None
    if not passed:
        if alive_6h < min_alive:
            reason = f"alive {alive_6h:.2f}"
        elif organic < min_organic:
            reason = f"organic {organic:.2f}"
        elif chase > max_chase:
            reason = f"chase {chase:.2f}"
        else:
            reason = f"score {score}"

    conn.execute(
        """INSERT INTO verdicts
           (mint, ts, alive_6h, organic, flush, chase, score, pass, reason, input_tokens)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (mint, now, alive_6h, organic, flush, chase, score, 1 if passed else 0, reason),
    )
    conn.commit()

    out = {
        "agent": "analyst",
        "mint": mint,
        "ts": now,
        "alive_6h": alive_6h,
        "organic": organic,
        "flush": flush,
        "chase": chase,
        "score": score,
        "passed": passed,
        "reason": reason,
        "mode": "rules",
    }
    if passed:
        await bus.put(bus.analyst_to_executor, out)
        print(f"Analyst: PASS {mint[:8]} score={score}")
    else:
        print(f"Analyst: REJECT {mint[:8]} {reason}")
        conn.execute(
            """INSERT INTO activity (ts, kind, mint, agent, title, subtitle, value)
               VALUES (?, 'rejected', ?, 'analyst', ?, ?, ?)""",
            (now, mint, f"Rejected {mint[:6]}", reason, f"score {score}"),
        )
        conn.commit()

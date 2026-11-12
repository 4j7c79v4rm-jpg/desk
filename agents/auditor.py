"""Auditor – agent 2. Takes coins apart. Talks only through bus and db."""

import asyncio
import json
import time
from datetime import datetime, timezone

import httpx

from fields import get as fget

RPC_URL = "https://api.mainnet-beta.solana.com"
RUG_URL = "https://api.rugcheck.xyz/v1/tokens/"


async def run(bus, conn, settings: dict):
    print("Auditor starting")
    while True:
        msg = await bus.get(bus.scanner_to_auditor)
        mint = msg["mint"]
        await _audit(mint, bus, conn, settings)


async def _audit(mint: str, bus, conn, settings: dict):
    retries = int(settings.get("auditor.retries", 3))
    layers = []
    passed = True
    reason = None
    holders = None

    async with httpx.AsyncClient(timeout=20) as client:
        # Layer 1-3 from RPC getAccountInfo
        info = {}
        for attempt in range(retries):
            try:
                r = await client.post(
                    RPC_URL,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getAccountInfo",
                        "params": [mint, {"encoding": "jsonParsed"}],
                    },
                )
                info = r.json().get("result", {}).get("value", {}).get("data", {}).get("parsed", {}).get("info", {})
                break
            except Exception:
                if attempt == retries - 1:
                    layers.append({"n": 1, "name": "Mint authority", "pass": False, "value": "no data", "source": "rpc"})
                    passed = False
                    reason = "no data: mint authority"
                await asyncio.sleep(2)

        if passed:
            mint_auth = info.get("mintAuthority")
            freeze_auth = info.get("freezeAuthority")
            supply = info.get("supply")
            l1 = mint_auth is None
            layers.append({"n": 1, "name": "Mint authority", "pass": l1, "value": str(mint_auth), "source": "rpc"})
            if not l1:
                passed = False
                reason = "mint authority set"
            else:
                l2 = freeze_auth is None
                layers.append({"n": 2, "name": "Freeze authority", "pass": l2, "value": str(freeze_auth), "source": "rpc"})
                if not l2:
                    passed = False
                    reason = "freeze authority set"
                else:
                    l3 = supply and int(supply) > 0
                    layers.append({"n": 3, "name": "Supply", "pass": l3, "value": str(supply), "source": "rpc"})
                    if not l3:
                        passed = False
                        reason = "no supply"

        # Layers 4-8 from RugCheck
        if passed:
            report = {}
            for attempt in range(retries):
                try:
                    rr = await client.get(f"{RUG_URL}{mint}/report")
                    if rr.status_code == 200:
                        report = rr.json()
                        break
                except Exception:
                    pass
                if attempt == retries - 1:
                    layers.append({"n": 4, "name": "LP locked", "pass": False, "value": "no data", "source": "rugcheck"})
                    passed = False
                    reason = "no data: LP"
                await asyncio.sleep(2)

            if passed and report:
                markets = report.get("markets", [])
                lp_pct = 0
                for m in markets:
                    if m.get("lp", {}).get("lpLockedPct"):
                        lp_pct = max(lp_pct, float(m["lp"]["lpLockedPct"]))
                min_lp = float(settings.get("auditor.min_lp_locked_pct", 99))
                l4 = lp_pct >= min_lp
                layers.append({"n": 4, "name": "LP locked", "pass": l4, "value": f"{lp_pct:.1f}%", "source": "rugcheck"})
                if not l4:
                    passed = False
                    reason = f"LP {lp_pct:.1f}% < {min_lp}"

                if passed:
                    top10 = float(report.get("topHoldersPct", 100) or 100)
                    max_top = float(settings.get("auditor.max_top10_pct", 25))
                    l5 = top10 <= max_top
                    layers.append({"n": 5, "name": "Top 10", "pass": l5, "value": f"{top10:.1f}%", "source": "rugcheck"})
                    if not l5:
                        passed = False
                        reason = f"top10 {top10:.1f}% > {max_top}"

                if passed:
                    dev = float(report.get("creatorBalance", 100) or 100)
                    max_dev = float(settings.get("auditor.max_dev_pct", 5))
                    l6 = dev <= max_dev
                    layers.append({"n": 6, "name": "Dev holds", "pass": l6, "value": f"{dev:.1f}%", "source": "rugcheck"})
                    if not l6:
                        passed = False
                        reason = f"dev {dev:.1f}% > {max_dev}"

                if passed:
                    bundled = int(report.get("bundledWallets", 99) or 99)
                    max_bund = int(settings.get("auditor.max_bundled", 5))
                    l7 = bundled <= max_bund
                    layers.append({"n": 7, "name": "Bundled", "pass": l7, "value": str(bundled), "source": "rugcheck"})
                    if not l7:
                        passed = False
                        reason = f"bundled {bundled} > {max_bund}"

                if passed:
                    try:
                        gpa = await client.post(
                            RPC_URL,
                            json={
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "getProgramAccounts",
                                "params": [
                                    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                                    {"encoding": "jsonParsed", "filters": [{"memcmp": {"offset": 0, "bytes": mint}}]},
                                ],
                            },
                        )
                        accounts = len(gpa.json().get("result", []))
                        holders = accounts
                        max_del = int(settings.get("auditor.max_delegated_accounts", 10))
                        l8 = accounts <= max_del * 50
                        layers.append({"n": 8, "name": "Delegations", "pass": l8, "value": str(accounts), "source": "rpc"})
                        if not l8:
                            passed = False
                            reason = f"accounts {accounts} high"
                    except Exception:
                        layers.append({"n": 8, "name": "Delegations", "pass": False, "value": "no data", "source": "rpc"})
                        passed = False
                        reason = "no data: delegations"

    for n in range(len(layers) + 1, 9):
        layers.append({"n": n, "name": f"Layer {n}", "pass": False, "value": "not checked", "source": ""})

    now = datetime.now(timezone.utc).isoformat()
    for L in layers:
        conn.execute(
            """INSERT INTO audits (mint, ts, layer, name, value_text, pass, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mint, now, L["n"], L["name"], L["value"], 1 if L["pass"] else 0, L["source"]),
        )
    conn.commit()

    out = {
        "agent": "auditor",
        "mint": mint,
        "ts": now,
        "passed": passed,
        "layersChecked": len([L for L in layers if L["value"] != "not checked"]),
        "layers": layers,
        "holders": holders,
        "reason": reason,
    }
    if passed:
        await bus.put(bus.auditor_to_analyst, out)
        print(f"Auditor: PASS {mint[:8]}")
    else:
        print(f"Auditor: RED  {mint[:8]} {reason}")
        conn.execute(
            """INSERT INTO activity (ts, kind, mint, agent, title, subtitle, value)
               VALUES (?, 'rejected', ?, 'auditor', ?, ?, ?)""",
            (now, mint, f"Rejected {mint[:6]}", reason, "Skipped"),
        )
        conn.commit()

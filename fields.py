"""Raw key mapping from STEP 2 samples. Agents read only through this. Missing key = null."""

FIELDS = {
    # PumpPortal migration
    "mint": "mint",
    "pool": "pool",
    "signature": "signature",
    "creator": None,  # not in migration message; fall back to RugCheck
    # DexScreener pair
    "pairAddress": "pairAddress",
    "priceUsd": "priceUsd",
    "liquidityUsd": "liquidity.usd",
    "marketCap": "marketCap",
    "volumeM5": "volume.m5",
    "priceChangeH1": "priceChange.h1",
    "dexId": "dexId",
    # RPC getAccountInfo (jsonParsed)
    "mintAuthority": "result.value.data.parsed.info.mintAuthority",
    "freezeAuthority": "result.value.data.parsed.info.freezeAuthority",
    "supply": "result.value.data.parsed.info.supply",
    # RugCheck (filled after first real audit)
    "lpLockedPct": None,
    "insidersNodes": None,
    "insidersEdges": None,
}


def get(data: dict, path: str):
    """Dot-path lookup. Returns None if missing. Never guess."""
    if not path or not data:
        return None
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

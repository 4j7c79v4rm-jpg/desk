"""FOMO fee model for PAPER PnL (STEP 11)."""

def paper_fees(size_usd: float, ref_discount: float = 0.10) -> float:
    """Simple round-trip fee estimate. Adjust later from real fills."""
    base_fee_pct = 0.008  # 0.8% round trip estimate
    fee = size_usd * base_fee_pct
    return fee * (1 - ref_discount)


def paper_pnl(entry: float, exit_price: float, size_usd: float, fees: float) -> float:
    if entry <= 0:
        return 0.0
    gross = size_usd * (exit_price - entry) / entry
    return gross - fees

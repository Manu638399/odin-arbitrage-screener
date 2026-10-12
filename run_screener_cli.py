"""
Live CLI Runner for Arbitrage Screener
Prints real-time cross-venue table data between Hyperliquid and MT5.
"""

import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.screener_engine import ScreenerEngine
from pipeline.config import CATEGORIES


def format_currency(val: float) -> str:
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    elif val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    elif val >= 1_000:
        return f"${val / 1_000:.1f}k"
    return f"${val:.0f}"


def print_table(rows, category="All"):
    print("\n" + "=" * 125)
    print(f"  ARBITRAGELAB -- LIVE ARBITRAGE SCREENER (Category: {category})")
    print("=" * 125)
    header = (
        f"{'Fav':<4} "
        f"{'Symbol':<12} "
        f"{'HL Mid':<12} "
        f"{'MT5 Mid':<12} "
        f"{'Spread':<12} "
        f"{'Spread %':<10} "
        f"{'Oracle Spd':<12} "
        f"{'Ann. Funding (L/S)':<22} "
        f"{'Funding Arb':<12} "
        f"{'24h Vol':<10} "
        f"{'OI':<10}"
    )
    print(header)
    print("-" * 125)

    for r in rows:
        fav = "*" if r["is_favorite"] else " "
        sym = r["symbol"]
        hl_mid = f"{r['hl_mid']:.2f}" if r["hl_mid"] is not None else "N/A"
        mt5_mid = f"{r['mt5_mid']:.2f}" if r["mt5_mid"] is not None else "N/A"

        # Format Spread
        spd = f"{r['current_spread']:+.2f}" if r["current_spread"] is not None else "N/A"
        spd_pct = f"{r['current_spread_pct']:+.2f}%" if r["current_spread_pct"] is not None else "N/A"
        orc_spd = f"{r['oracle_spread']:+.2f}" if r["oracle_spread"] is not None else "N/A"

        funding_ls = f"{r['ann_funding_long']:+.2f}% / {r['ann_funding_short']:+.2f}%"
        funding_arb = f"{r['funding_arbitrage']:+.2f}%"

        vol = format_currency(r["volume_24h_usd"])
        oi = format_currency(r["open_interest_usd"])

        row_str = (
            f" {fav}  "
            f"{sym:<12} "
            f"{hl_mid:<12} "
            f"{mt5_mid:<12} "
            f"{spd:<12} "
            f"{spd_pct:<10} "
            f"{orc_spd:<12} "
            f"{funding_ls:<22} "
            f"{funding_arb:<12} "
            f"{vol:<10} "
            f"{oi:<10}"
        )
        print(row_str)

    print("-" * 125)
    print(f"Total pairs monitored: {len(rows)}\n")


def main():
    print("Connecting to Hyperliquid and MetaTrader 5...")
    engine = ScreenerEngine()
    engine.initialize()

    category = sys.argv[1] if len(sys.argv) > 1 else "All"
    print(f"Fetching live market snapshot for category '{category}'...")
    rows = engine.get_screener_table(category=category)
    print_table(rows, category=category)


if __name__ == "__main__":
    main()

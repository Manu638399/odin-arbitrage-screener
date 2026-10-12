"""
Configuration and Symbol Universe for ArbitrageLab
Cross-Venue Screener between Hyperliquid (builder DEXes e.g. xyz:) and MetaTrader 5.
"""

from typing import Dict, List, Optional, Any

# Primary default DEX on Hyperliquid for TradFi / synthetic perps
DEFAULT_HL_DEX = "xyz"

# Base categories matching the Arbitrage Screener UI
CATEGORIES = [
    "All",
    "Favorites",
    "Indices",
    "FX",
    "Metals",
    "Commodities",
    "ETFs",
    "Equities"
]

# Universe definition with preferred symbols and fallback variants across brokers
RAW_PAIRS_UNIVERSE = [
    # Indices
    {
        "symbol": "SP500",
        "hl_symbol": "xyz:SP500",
        "mt5_preferred": "US500",
        "mt5_fallbacks": ["SP500", "SPX500", "USA500", "US500Cash"],
        "category": "Indices",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "JP225",
        "hl_symbol": "xyz:JP225",
        "mt5_preferred": "JP225",
        "mt5_fallbacks": ["JPN225", "NIKKEI", "JP225Cash"],
        "category": "Indices",
        "quote_ccy": "JPY",  # Note: Quoted in points/JPY directly on both
        "is_favorite": True
    },
    {
        "symbol": "XYZ100",
        "hl_symbol": "xyz:XYZ100",
        "mt5_preferred": "USTEC",
        "mt5_fallbacks": ["NAS100", "US100", "NDX", "USTECcash"],
        "category": "Indices",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "DXY",
        "hl_symbol": "xyz:DXY",
        "mt5_preferred": "USDX",
        "mt5_fallbacks": ["DXY", "USD_Index"],
        "category": "Indices",
        "quote_ccy": "USD",
        "is_favorite": False
    },

    # FX
    {
        "symbol": "EUR",
        "hl_symbol": "xyz:EUR",
        "mt5_preferred": "EURUSD",
        "mt5_fallbacks": ["EURUSD.raw", "EURUSD.pro"],
        "category": "FX",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "GBP",
        "hl_symbol": "xyz:GBP",
        "mt5_preferred": "GBPUSD",
        "mt5_fallbacks": ["GBPUSD.raw", "GBPUSD.pro"],
        "category": "FX",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "JPY",
        "hl_symbol": "xyz:JPY",
        "mt5_preferred": "USDJPY",
        "mt5_fallbacks": ["USDJPY.raw", "USDJPY.pro"],
        "category": "FX",
        "quote_ccy": "JPY",
        "is_favorite": True
    },

    # Metals
    {
        "symbol": "GOLD",
        "hl_symbol": "xyz:GOLD",
        "mt5_preferred": "XAUUSD",
        "mt5_fallbacks": ["GOLD", "XAUUSD.raw", "GOLD.NYSE"],
        "category": "Metals",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "SILVER",
        "hl_symbol": "xyz:SILVER",
        "mt5_preferred": "XAGUSD",
        "mt5_fallbacks": ["SILVER", "XAGUSD.raw"],
        "category": "Metals",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "PLATINUM",
        "hl_symbol": "xyz:PLATINUM",
        "mt5_preferred": "XPTUSD",
        "mt5_fallbacks": ["PLATINUM", "XPTUSD.raw"],
        "category": "Metals",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "PALLADIUM",
        "hl_symbol": "xyz:PALLADIUM",
        "mt5_preferred": "XPDUSD",
        "mt5_fallbacks": ["PALLADIUM", "XPDUSD.raw"],
        "category": "Metals",
        "quote_ccy": "USD",
        "is_favorite": False
    },

    # Commodities
    {
        "symbol": "WTIOIL",
        "hl_symbol": "xyz:CL",
        "mt5_preferred": "USOUSD",
        "mt5_fallbacks": ["WTI_X6", "WTI.NYSE", "WTI", "USOIL", "WTI_X6_CFD"],
        "category": "Commodities",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "BRENT",
        "hl_symbol": "xyz:BRENTOIL",
        "mt5_preferred": "UKOUSD",
        "mt5_fallbacks": ["BRENT_Z6", "BRENT_M6", "BRENT", "UKOIL"],
        "category": "Commodities",
        "quote_ccy": "USD",
        "is_favorite": True
    },
    {
        "symbol": "NATGAS",
        "hl_symbol": "xyz:NATGAS",
        "mt5_preferred": "XNGUSD",
        "mt5_fallbacks": ["NATGAS", "GAS"],
        "category": "Commodities",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "COPPER",
        "hl_symbol": "xyz:COPPER",
        "mt5_preferred": "COPPER",
        "mt5_fallbacks": ["XCUUSD", "HG"],
        "category": "Commodities",
        "quote_ccy": "USD",
        "is_favorite": False
    },

    # Equities
    {
        "symbol": "NVDA",
        "hl_symbol": "xyz:NVDA",
        "mt5_preferred": "NVDA.NAS",
        "mt5_fallbacks": ["NVDA", "NVDA.O", "NVDA.NASDAQ", "NVDA-24"],
        "category": "Equities",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "TSLA",
        "hl_symbol": "xyz:TSLA",
        "mt5_preferred": "TSLA.NAS",
        "mt5_fallbacks": ["TSLA", "TSLA.O", "TSLA.NASDAQ", "TSLA-24"],
        "category": "Equities",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "AAPL",
        "hl_symbol": "xyz:AAPL",
        "mt5_preferred": "AAPL.NAS",
        "mt5_fallbacks": ["AAPL", "AAPL.O", "AAPL.NASDAQ"],
        "category": "Equities",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "MSFT",
        "hl_symbol": "xyz:MSFT",
        "mt5_preferred": "MSFT.NAS",
        "mt5_fallbacks": ["MSFT", "MSFT.O", "MSFT.NASDAQ"],
        "category": "Equities",
        "quote_ccy": "USD",
        "is_favorite": False
    },

    # ETFs
    {
        "symbol": "TLT",
        "hl_symbol": "xyz:TLT",
        "mt5_preferred": "TLT",
        "mt5_fallbacks": ["TLT.O", "TLT.NASDAQ"],
        "category": "ETFs",
        "quote_ccy": "USD",
        "is_favorite": False
    },
    {
        "symbol": "SMH",
        "hl_symbol": "xyz:SMH",
        "mt5_preferred": "SMH",
        "mt5_fallbacks": ["SMH.O", "SMH.NASDAQ"],
        "category": "ETFs",
        "quote_ccy": "USD",
        "is_favorite": False
    }
]


def resolve_symbol_pair(
    pair_cfg: Dict[str, Any],
    available_mt5_symbols: Optional[set] = None
) -> Dict[str, Any]:
    """
    Resolves the active MT5 symbol based on the symbols available in the user's broker.
    """
    resolved_mt5 = pair_cfg["mt5_preferred"]
    if available_mt5_symbols:
        candidates = [pair_cfg["mt5_preferred"]] + pair_cfg.get("mt5_fallbacks", [])
        for candidate in candidates:
            if candidate in available_mt5_symbols:
                resolved_mt5 = candidate
                break

    return {
        "symbol": pair_cfg["symbol"],
        "label": f"{pair_cfg['symbol']} ({pair_cfg['hl_symbol']} / {resolved_mt5})",
        "hl_symbol": pair_cfg["hl_symbol"],
        "mt5_symbol": resolved_mt5,
        "category": pair_cfg["category"],
        "quote_ccy": pair_cfg.get("quote_ccy", "USD"),
        "is_favorite": pair_cfg.get("is_favorite", False)
    }

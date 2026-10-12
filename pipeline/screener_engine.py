"""
Arbitrage Screener Engine
Coordinates live ingestion from Hyperliquid and MT5, calculates cross-venue spreads,
annualized funding capture, volume, open interest, and generates table snapshots.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
import pandas as pd

from pipeline.config import RAW_PAIRS_UNIVERSE, resolve_symbol_pair
from pipeline.hyperliquid_feed import HyperliquidFeed
from pipeline.mt5_feed import MT5Feed
from pipeline.synchronizer import DataSynchronizer

logger = logging.getLogger(__name__)


class ScreenerEngine:
    """Core aggregation engine for ArbitrageLab."""

    def __init__(
        self,
        hl_dex: str = "xyz",
        mt5_terminal_path: Optional[str] = None
    ):
        self.hl_feed = HyperliquidFeed(default_dex=hl_dex)
        self.mt5_feed = MT5Feed(terminal_path=mt5_terminal_path)
        self.synchronizer = DataSynchronizer()
        self._initialized = False
        self._resolved_universe: List[Dict[str, Any]] = []
        self._pair_analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec = 30.0
        self._remote_ticks: Dict[str, Dict[str, Any]] = {}

    def update_remote_ticks(self, ticks: Dict[str, Dict[str, Any]]):
        """Stores synced MT5 ticks received from a remote publisher agent."""
        self._remote_ticks.update(ticks)

    def initialize(self) -> bool:
        """Initializes venues and resolves broker symbols."""
        if self._initialized:
            return True

        mt5_ok = self.mt5_feed.initialize()
        if not mt5_ok:
            logger.warning("MT5 initialization failed; live MT5 quotes may be unavailable.")

        # Resolve universe against broker's available symbols
        available_mt5 = self.mt5_feed.get_available_symbols()
        self._resolved_universe = [
            resolve_symbol_pair(p, available_mt5) for p in RAW_PAIRS_UNIVERSE
        ]
        self._initialized = True
        return True

    def get_screener_table(self, category: str = "All") -> List[Dict[str, Any]]:
        """
        Polls live prices across Hyperliquid and MT5 for all universe pairs,
        computing spreads, funding rates, and volume metrics.
        """
        if not self._initialized:
            self.initialize()

        # 1. Fetch live contexts from Hyperliquid
        try:
            hl_contexts = self.hl_feed.get_meta_and_contexts()
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid contexts: {e}")
            hl_contexts = {}

        rows: List[Dict[str, Any]] = []

        for pair in self._resolved_universe:
            # Filter by category if requested
            if category == "Favorites" and not pair.get("is_favorite", False):
                continue
            elif category != "All" and category != "Favorites" and pair["category"] != category:
                continue

            hl_sym = pair["hl_symbol"]
            mt5_sym = pair["mt5_symbol"]

            hl_ctx = hl_contexts.get(hl_sym) or hl_contexts.get(pair["symbol"]) or {}
            hl_mid = hl_ctx.get("mid_px")
            hl_oracle = hl_ctx.get("oracle_px")
            funding_ann = hl_ctx.get("funding_rate_ann_pct", 0.0)
            ann_long = hl_ctx.get("ann_funding_long_pct", 0.0)
            ann_short = hl_ctx.get("ann_funding_short_pct", 0.0)
            volume_24h = hl_ctx.get("day_volume_usd", 0.0)
            open_interest = hl_ctx.get("open_interest_usd", 0.0)

            # 2. Fetch live MT5 tick
            mt5_tick = self.mt5_feed.get_tick(mt5_sym)
            if not mt5_tick:
                mt5_tick = self._remote_ticks.get(pair["symbol"]) or self._remote_ticks.get(mt5_sym)
            mt5_mid = mt5_tick["mid"] if mt5_tick else None

            # 3. Compute Spreads
            if hl_mid is not None and mt5_mid is not None and mt5_mid > 0:
                current_spread = hl_mid - mt5_mid
                current_spread_pct = (current_spread / mt5_mid) * 100.0
            else:
                current_spread = None
                current_spread_pct = None

            if hl_oracle is not None and mt5_mid is not None and mt5_mid > 0:
                oracle_spread = hl_oracle - mt5_mid
            else:
                oracle_spread = None

            # Funding Arbitrage capture yield:
            # If funding is positive (longs pay shorts on HL), short HL and long MT5 -> capture +funding
            # If funding is negative (shorts pay longs on HL), long HL and short MT5 -> capture -funding
            funding_arbitrage = abs(funding_ann) if funding_ann != 0.0 else 0.0

            rows.append({
                "symbol": pair["symbol"],
                "label": pair["label"],
                "hl_symbol": hl_sym,
                "mt5_symbol": mt5_sym,
                "category": pair["category"],
                "is_favorite": pair.get("is_favorite", False),
                "hl_mid": hl_mid,
                "hl_oracle": hl_oracle,
                "mt5_mid": mt5_mid,
                "current_spread": round(current_spread, 4) if current_spread is not None else None,
                "current_spread_pct": round(current_spread_pct, 4) if current_spread_pct is not None else None,
                "oracle_spread": round(oracle_spread, 4) if oracle_spread is not None else None,
                "ann_funding_long": round(ann_long, 2),
                "ann_funding_short": round(ann_short, 2),
                "funding_arbitrage": round(ann_short, 2) if ann_short > 0 else round(ann_long, 2),
                "volume_24h_usd": volume_24h,
                "open_interest_usd": open_interest
            })

        return rows

    def get_pair_analysis(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_hours: int = 48,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Fetches historical candles from both venues concurrently, aligns them on UTC time,
        and computes spread time series and distribution statistics.
        Caches results for high-speed repeated queries (e.g. backtesting).
        """
        if not self._initialized:
            self.initialize()

        cache_key = f"{symbol}_{timeframe}_{lookback_hours}"
        now = time.time()
        if use_cache and cache_key in self._pair_analysis_cache:
            entry = self._pair_analysis_cache[cache_key]
            if now - entry["timestamp"] < self._cache_ttl_sec:
                return entry["data"]

        # Find pair config
        pair_cfg = next((p for p in self._resolved_universe if p["symbol"] == symbol or p["hl_symbol"] == symbol), None)
        if not pair_cfg:
            raise ValueError(f"Unknown symbol '{symbol}'")

        hl_sym = pair_cfg["hl_symbol"]
        mt5_sym = pair_cfg["mt5_symbol"]

        # Concurrently fetch candles & live contexts in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_hl = executor.submit(self.hl_feed.get_candles, hl_sym, timeframe, lookback_hours)
            future_mt5 = executor.submit(self.mt5_feed.get_candles, mt5_sym, timeframe, lookback_hours)
            future_ctx = executor.submit(self.hl_feed.get_meta_and_contexts)
            future_tick = executor.submit(self.mt5_feed.get_tick, mt5_sym)

            try:
                df_hl = future_hl.result()
            except Exception as e:
                logger.error(f"Error fetching HL candles: {e}")
                df_hl = pd.DataFrame()

            try:
                df_mt5 = future_mt5.result()
            except Exception as e:
                logger.error(f"Error fetching MT5 candles: {e}")
                df_mt5 = pd.DataFrame()

            try:
                contexts = future_ctx.result()
            except Exception as e:
                logger.error(f"Error fetching HL contexts: {e}")
                contexts = {}

            try:
                mt5_tick = future_tick.result()
            except Exception as e:
                logger.error(f"Error fetching MT5 tick: {e}")
                mt5_tick = None

            if not mt5_tick:
                mt5_tick = self._remote_ticks.get(pair_cfg["symbol"]) or self._remote_ticks.get(mt5_sym)

        aligned_df = self.synchronizer.align_series(df_hl, df_mt5)
        stats = self.synchronizer.compute_statistics(aligned_df["spread"]) if not aligned_df.empty else {}

        hl_ctx = contexts.get(hl_sym) or contexts.get(pair_cfg["symbol"]) or {}
        hl_mid = hl_ctx.get("mid_px")
        mt5_mid = mt5_tick["mid"] if mt5_tick else None
        curr_spread = (hl_mid - mt5_mid) if (hl_mid and mt5_mid) else None
        curr_spread_pct = ((curr_spread / mt5_mid) * 100.0) if (curr_spread and mt5_mid) else None
        hl_oracle = hl_ctx.get("oracle_px")
        oracle_spread = (hl_oracle - mt5_mid) if (hl_oracle and mt5_mid) else None

        result = {
            "pair": pair_cfg,
            "metrics": {
                "current_spread": round(curr_spread, 4) if curr_spread is not None else None,
                "current_spread_pct": round(curr_spread_pct, 4) if curr_spread_pct is not None else None,
                "oracle_spread": round(oracle_spread, 4) if oracle_spread is not None else None,
                "ann_funding_long": round(hl_ctx.get("ann_funding_long_pct", 0.0), 2),
                "ann_funding_short": round(hl_ctx.get("ann_funding_short_pct", 0.0), 2),
                "funding_arbitrage": round(hl_ctx.get("ann_funding_short_pct", 0.0), 2),
                "volume_24h_usd": hl_ctx.get("day_volume_usd", 0.0),
                "open_interest_usd": hl_ctx.get("open_interest_usd", 0.0),
                "mt5_spread": mt5_tick["spread"] if mt5_tick else 0.0
            },
            "stats": stats,
            "aligned_df": aligned_df
        }

        self._pair_analysis_cache[cache_key] = {
            "timestamp": now,
            "data": result
        }

        return result

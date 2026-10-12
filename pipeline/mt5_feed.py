"""
MetaTrader 5 Feed Client
Connects to the local MT5 terminal, resolves broker timezone offsets,
and streams real-time bid/ask/mid quotes and historical rates.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    MT5_TIMEFRAME_MAP = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
    }
except ImportError:
    mt5 = None
    MT5_TIMEFRAME_MAP = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 16385,
        "4h": 16388,
        "1d": 16408,
    }


class MT5Feed:
    """Interface to the local MetaTrader 5 terminal."""

    def __init__(self, terminal_path: Optional[str] = None):
        self.terminal_path = terminal_path
        self._is_initialized = False
        self._broker_offset_seconds: Optional[int] = None
        self._available_symbols_cache: Optional[Set[str]] = None

    def initialize(self) -> bool:
        """Initializes connection to MT5 terminal."""
        if self._is_initialized:
            return True

        ok = mt5.initialize(self.terminal_path) if self.terminal_path else mt5.initialize()
        if not ok:
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            self._is_initialized = False
            return False

        self._is_initialized = True
        logger.info("Connected to MT5 terminal successfully.")
        return True

    def shutdown(self):
        """Disconnects from MT5 terminal."""
        if self._is_initialized:
            mt5.shutdown()
            self._is_initialized = False

    def get_available_symbols(self, refresh: bool = False) -> Set[str]:
        """Returns the set of all symbols provided by the broker."""
        if not self._is_initialized:
            self.initialize()

        if self._available_symbols_cache is None or refresh:
            symbols = mt5.symbols_get()
            if symbols:
                self._available_symbols_cache = {s.name for s in symbols}
            else:
                self._available_symbols_cache = set()
        return self._available_symbols_cache

    def get_broker_utc_offset_seconds(self) -> int:
        """
        Determines the broker server's UTC offset in seconds.
        E.g., broker server in EET is UTC+2 (7200s) or EEST is UTC+3 (10800s).
        """
        if self._broker_offset_seconds is not None:
            return self._broker_offset_seconds

        if not self._is_initialized:
            self.initialize()

        # Try to sample from a highly liquid pair (EURUSD or similar)
        for probe in ["EURUSD", "GBPUSD", "USDJPY", "US500", "JP225"]:
            tick = mt5.symbol_info_tick(probe)
            if tick and tick.time:
                now_utc_ts = int(datetime.now(timezone.utc).timestamp())
                diff = tick.time - now_utc_ts
                # Round to nearest full hour
                hours = round(diff / 3600.0)
                # Brokers are typically between -12 and +14 hours from UTC
                if -12 <= hours <= 14:
                    self._broker_offset_seconds = int(hours * 3600)
                    logger.info(f"Detected MT5 broker UTC offset: {hours:+d} hours ({self._broker_offset_seconds}s)")
                    return self._broker_offset_seconds

        # Default fallback: 3 hours (IC Markets EET/EEST standard) or 0
        self._broker_offset_seconds = 3 * 3600
        return self._broker_offset_seconds

    def ensure_symbol_selected(self, symbol: str) -> bool:
        """Selects symbol in Market Watch if not already active."""
        if not self._is_initialized:
            self.initialize()
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            return mt5.symbol_select(symbol, True)
        return True

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches current tick (bid, ask, mid, spread) for symbol.
        Falls back to latest M1 candle close if ticks are unavailable (e.g. market closed).
        """
        if not self._is_initialized:
            self.initialize()

        self.ensure_symbol_selected(symbol)
        tick = mt5.symbol_info_tick(symbol)
        
        bid = tick.bid if (tick and tick.bid > 0) else None
        ask = tick.ask if (tick and tick.ask > 0) else None

        sym_info = mt5.symbol_info(symbol)
        point = sym_info.point if sym_info else 0.0001

        if bid and ask:
            mid = (bid + ask) / 2.0
            spread = ask - bid
            server_time = tick.time
        else:
            # Fallback to the latest completed/forming M1 bar
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
            if rates is not None and len(rates) > 0:
                mid = float(rates[0][4])  # close
                bid = mid
                ask = mid
                spread = sym_info.spread * point if sym_info else 0.0
                server_time = int(rates[0][0])
            else:
                return None

        spread_pts = round(spread / point) if point > 0 else 0

        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread": spread,
            "spread_points": spread_pts,
            "point": point,
            "server_time": server_time
        }

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_hours: int = 48,
        start_utc: Optional[datetime] = None,
        end_utc: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetches historical bars and shifts them to UTC.
        Returns a DataFrame indexed by UTC timestamp with OHLCV data.
        """
        if not self._is_initialized:
            self.initialize()

        self.ensure_symbol_selected(symbol)
        tf = MT5_TIMEFRAME_MAP.get(timeframe, mt5.TIMEFRAME_M1)

        offset_s = self.get_broker_utc_offset_seconds()
        now_utc = datetime.now(timezone.utc)

        if end_utc is None:
            end_utc = now_utc
        if start_utc is None:
            start_utc = end_utc - timedelta(hours=lookback_hours)

        # Shift UTC window to Broker Server Time
        broker_start = start_utc + timedelta(seconds=offset_s)
        broker_end = end_utc + timedelta(seconds=offset_s)

        rates = mt5.copy_rates_range(symbol, tf, broker_start, broker_end)
        if rates is None or len(rates) == 0:
            # Fallback to copy_rates_from_pos in case broker range fails
            bars_count = int(lookback_hours * 60) if timeframe == "1m" else 1000
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars_count)

        if rates is None or len(rates) == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rates)
        # Shift broker server timestamp back to UTC
        df["time"] = pd.to_datetime(df["time"] - offset_s, unit="s", utc=True)
        df = df.rename(columns={"tick_volume": "volume"})
        df = df[["time", "open", "high", "low", "close", "volume"]].set_index("time").sort_index()
        # De-duplicate timestamps if any
        df = df[~df.index.duplicated(keep="last")]
        return df
